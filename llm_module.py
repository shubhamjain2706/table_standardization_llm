from string import Template
from langchain.document_loaders.csv_loader import CSVLoader
import pandas as pd
import openai
import json
from langchain.llms import OpenAI
from classes import Candidate


# Globals
OPENAI_API_KEY = ""  # ADD YOUR OPENAI API KEY HERE
COLS_MAPPING_ASK_TEXT_TEMPLATE = Template(f"Find only the closest mapping of all column names in '$to_cols' and "
                                          f"'$from_cols' and not the code. In case of ambiguous mappings, "
                                          f"keep them all. Return valid JSON dict and nothing else, with key as "
                                          f"column name from $to_cols and value as list of mappings to $from_cols. "
                                          f"Use double quotes in JSON.")
DATA_CONVERSION_ASK_TEXT_TEMPLATE = Template(f"Return code for converting data from '$from_data' to '$to_data'. Write "
                                             f"single function to convert pandas df to another. Conversion function "
                                             f"should take single dataframe and return the converted dataframe. The "
                                             f"function should be self sufficient. Include imports inside the "
                                             f"function. Do not hard code, for columns with no conversion required "
                                             f"return the value. Function name should be called $function_name."
                                             f"Assume column are of simple data types. Perform conversion to complex type like datetime as requied."
                                             f"Do not invoke the function, the text should only contain required function.")


# Step 1 : Extract information about the columns of the Template table and tables A and B in the format of a text
# description.
def extract_cols_info(template_file_path: str, input_candidate_file_paths: list[str]) -> (list[Candidate]):
    template_loader = CSVLoader(file_path=template_file_path)
    template_data = template_loader.load()
    sample_template_data = template_data[0].dict()['page_content']
    template_cols_string = ",".join([x.split(":")[0] for x in sample_template_data.split("\n")])
    print(f"template_cols :: {template_cols_string}")
    print(f"template_sample_data:: {sample_template_data}")
    print()

    input_candidates = []
    for i in range(len(input_candidate_file_paths)):
        candidate = Candidate(input_candidate_file_paths[i])
        print("candidate.input_path: ", candidate.input_path)
        loader = CSVLoader(file_path=candidate.input_path)
        data = loader.load()
        sample_row = data[0].dict()['page_content']
        candidate.input_cols_string = ",".join([x.split(":")[0] for x in sample_row.split("\n")])
        input_candidates.append(candidate)
        print(f"candidate {i} cols :: {candidate.input_cols_string}")
        print(f"candidate {i} sample_row :: {sample_row}")
        print()
    return (template_cols_string, input_candidates)


# Step 2 : For each of the candidate tables (A and B), ask the LLM to find similar columns in the Template.
def find_similar_cols_mapping(template_cols_string: str, input_candidates: list[Candidate]) -> list[Candidate]:
    openai.api_key = OPENAI_API_KEY
    llm = OpenAI(openai_api_key=openai.api_key, temperature=0.1)
    for i in range(len(input_candidates)):
        text = COLS_MAPPING_ASK_TEXT_TEMPLATE.substitute(
            to_cols=template_cols_string,
            from_cols=input_candidates[i].input_cols_string
        )
        mapping = llm(text)
        json_mapping = json.loads(mapping)
        print(f"json_mapping: {json_mapping}")
        print()
        input_candidates[i].cols_mapping = json_mapping
    return input_candidates


# Step 3 : In case of ambiguous mapping, ask the user to choose the most suitable column from the candidates.
# This method is only needed for CLI and not the web interface.
def resolve_ambiguity(input_candidates: list[Candidate]) -> list[Candidate]:
    for i in range(len(input_candidates)):
        cols_mapping = input_candidates[i].cols_mapping
        final_mapping = {}
        for mapping_to, mapping_from in cols_mapping.items():
            final_mapping_from = mapping_from[0] if type(mapping_from) == list else mapping_from  # default case
            if type(mapping_from) == list and len(mapping_from) > 1:
                print(f"Ambiguous mapping for column '{mapping_to}': {mapping_from}")
                user_choice = input("Please choose the most suitable column: ")
                if user_choice in mapping_from:
                    final_mapping_from = user_choice
                else:
                    print(f"Invalid choice. Assigning default mapping for column '{mapping_to}'.")
            final_mapping[mapping_to] = final_mapping_from
        print(f"final_mapping for candidate {i} : {final_mapping}")
        print()
        input_candidates[i].cols_mapping = final_mapping
    return input_candidates


# Step 4 : Automatically generate data mapping code for each column display in the final Template format. For
# example, for date columns, they may be in different formats, and it is necessary to change the order from
# dd.mm.yyyy to mm.dd.yyyy. The person can check the code (or pseudocode) that will perform the mapping.
def generate_data_conversion_code(template_file_path: str, input_candidates: list[Candidate]) -> list[Candidate]:
    for i in range(len(input_candidates)):
        candidate_select_cols = input_candidates[i].cols_mapping.values()
        candidate_data = pd.read_csv(input_candidates[i].input_path)[candidate_select_cols]
        template_select_cols = input_candidates[i].cols_mapping.keys()
        sample_template_data = pd.read_csv(template_file_path)[template_select_cols].head(2)
        candidate_data = candidate_data.rename(
            columns={v: k for k, v in input_candidates[i].cols_mapping.items()}
        )
        sample_candidate_data = candidate_data.head(2)
        print(f"sample_candidate_data: \n{sample_candidate_data}")
        print()
        print(f"sample_template_data: \n{sample_template_data}")
        text = DATA_CONVERSION_ASK_TEXT_TEMPLATE.substitute(
            to_data=sample_template_data,
            from_data=sample_candidate_data,
            function_name="convert_df"
        )
        openai.api_key = OPENAI_API_KEY
        llm = OpenAI(openai_api_key=openai.api_key, temperature=0.1)
        data_conversion_code = llm(text)
        input_candidates[i].data_conversion_code = data_conversion_code
        print(f"Code generated by LLM to convert data from candidate {i} to template data:: \n")
        print(data_conversion_code)
        print()

        ## code for CLI and not web interface
        # user_choice = input("Does this look good to you? Please type Y (to proceed) or N (to abort): ")
        # if user_choice in ['Y', 'N']:
        #     if user_choice == 'N':
        #         input_candidates[i].data_conversion_code = None
        # else:
        #     print(f"Invalid choice. Assigning Y by default.")

        with open(f"{input_candidates[i].output_path.replace('_converted.csv', '_code_for_conversion.py')}", "w") as py_file:
            py_file.write(input_candidates[i].data_conversion_code)
    return input_candidates


# Step 5 : Check that all data has been transferred correctly; if any errors occur, issue an alert to the person.
def transform_verify_save_data(input_candidates: list[Candidate]) -> list[Candidate]:
    for i in range(len(input_candidates)):
        print(f"input_candidates[{i}].input_path: ", input_candidates[i].input_path)
        print(f"input_candidates[{i}].output_path: ", input_candidates[i].output_path)
        print(f"input_candidates[{i}].cols_mapping: ", input_candidates[i].cols_mapping)
        print(f"input_candidates[{i}].data_conversion_code: ", input_candidates[i].data_conversion_code)
        print()
        
    flag = 0
    for i in range(len(input_candidates)):
        candidate_select_cols = input_candidates[i].cols_mapping.values()
        candidate_data = pd.read_csv(input_candidates[i].input_path)[candidate_select_cols]
        candidate_data = candidate_data.rename(columns={v:k for k,v in input_candidates[i].cols_mapping.items()})
        try:
            if input_candidates[i].data_conversion_code:
                function_string = input_candidates[i].data_conversion_code.strip()
                compiled_code = compile(function_string, "<string>", "exec")
                scope = {}
                exec(compiled_code, scope)
                function_name = function_string.split('(')[0].replace("def ", "").strip()
                converted_candidate_data = scope[function_name](candidate_data)
                print(converted_candidate_data.head())
                converted_candidate_data.to_csv(input_candidates[i].output_path, index=False)
                flag = 1
            else:
                raise Exception(f"ALERT: No conversion code present for candidate {i}.")
        except Exception as e:
            print(f"ERROR: Some error occurred while converting the candidate {i} data format.")
            print(e)
    if flag:
        return input_candidates
    else:
        return None

# This function is only required for CLI and not web interface
def main_processor(template_file_path: str, input_candidate_file_paths: list[str]) -> list[str]:
    print(f"template_file_path: {template_file_path}")
    print(f"input_candidate_file_paths: {input_candidate_file_paths}")
    template_cols_string, input_candidates = extract_cols_info(template_file_path, input_candidate_file_paths)
    input_candidates = find_similar_cols_mapping(template_cols_string, input_candidates)
    input_candidates = resolve_ambiguity(input_candidates)
    input_candidates = generate_data_conversion_code(template_file_path, input_candidates)
    input_candidates = transform_verify_save_data(input_candidates)
    output_filenames = [x.output_path for x in input_candidates]
    return output_filenames
