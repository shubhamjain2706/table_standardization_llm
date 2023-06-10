from flask import Flask, request, jsonify, render_template, session, flash, send_from_directory
from llm_module import extract_cols_info, find_similar_cols_mapping, generate_data_conversion_code, transform_verify_save_data
from classes import Candidate
import os
import shutil

app = Flask(__name__)
app.secret_key = 'BAD_SECRET_KEY'

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'

@app.route('/')
def index():
    return render_template('index.html')  


@app.route('/process', methods=['POST'])
def process_files():
    template_file = request.files['templateFile']
    candidate_files = request.files.getlist('candidateFiles')

    # Create a unique folder to store the uploaded files
    upload_path = UPLOAD_FOLDER
    if os.path.exists(upload_path) and os.path.isdir(upload_path):
        shutil.rmtree(upload_path)
    os.makedirs(upload_path)

    # Save the template file
    template_filename = template_file.filename
    template_path = os.path.join(upload_path, template_filename)
    template_file.save(template_path)

    # Save the candidate files
    candidate_filenames = []
    candidate_paths = []
    for i, candidate_file in enumerate(candidate_files):
        candidate_filename = candidate_file.filename
        candidate_path = os.path.join(upload_path, candidate_filename)
        candidate_file.save(candidate_path)
        candidate_paths.append(candidate_path)
        candidate_filenames.append(candidate_filename)

    # Process the files
    template_cols_string, input_candidates = extract_cols_info(template_path, candidate_paths)
    input_candidates = find_similar_cols_mapping(template_cols_string, input_candidates)
    response = {}
    for candidate in input_candidates:
        response[candidate.input_path.split("/")[-1]] = candidate.cols_mapping
        print("mapping: ", candidate.cols_mapping)
        print("input_file: ", candidate.input_path.split("/")[-1])
    print("response: ", response)

    final_response = {}
    final_response["mappings"] = response
    final_response["template_file_name"] = template_filename

    return jsonify(final_response)


@app.route('/process_form', methods=['POST'])
def process_form():
    candidates = []
    # Iterate over the form data to process the selected aliases for each column
    print("request.form: ", request.form)

    column_aliases = {}
    template_file_name = ""
    for column, alias in request.form.items():
        template_file_name = column.split("::")[0]
        actual_col = column.split("::")[2]
        file_name = column.split("::")[1]
        col_alias = alias
        if file_name not in column_aliases.keys():
            column_aliases[file_name] = {}
        column_aliases[file_name][actual_col] = col_alias

    session["column_aliases"] = column_aliases

    for k, v in column_aliases.items():
        cand = Candidate(os.path.join(UPLOAD_FOLDER, k))
        cand.cols_mapping = v
        candidates.append(cand)
        
    print(f"All selected aliases: {column_aliases}")
    print("template_file_name: ", template_file_name)

    if os.path.exists(OUTPUT_FOLDER) and os.path.isdir(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)
    os.makedirs(OUTPUT_FOLDER)
    template_path = os.path.join(UPLOAD_FOLDER, template_file_name)
    candidates = generate_data_conversion_code(template_path, candidates)
    code_conversion_filenames = [x.output_path.replace("_converted.csv", "_code_for_conversion.py").replace("outputs/", "") for x in candidates]

    # Generate download URLs for the output files
    output_filenames = []
    download_urls = []
    for output_filename in code_conversion_filenames:
        download_url = f'/download/{output_filename}'
        download_urls.append(download_url)
        output_filenames.append(output_filename)

    response = {
        'outputFiles': [
            {'filename': output_filename, 'downloadUrl': download_url}
            for output_filename, download_url in zip(output_filenames, download_urls)
        ]
    }

    return jsonify(response)


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename.replace("outputs/", ""), as_attachment=True)


@app.route('/upload_and_convert', methods=['POST'])
def upload_and_convert():
    conversion_files = request.files.getlist('codeConversionFiles')

    if os.path.exists(OUTPUT_FOLDER) and os.path.isdir(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)
    os.makedirs(OUTPUT_FOLDER)

    # Save the conversion files with names
    for i, file_ in enumerate(conversion_files):
        path_ = os.path.join(OUTPUT_FOLDER, file_.filename)
        file_.save(path_)

    candidates = []
    column_aliases = session.get("column_aliases", {})
    print("column_aliases: ", column_aliases)
    for file_ in conversion_files:
        file_name = file_.filename.replace("_code_for_conversion.py", ".csv")
        cand = Candidate(os.path.join(UPLOAD_FOLDER, file_name))
        cand.cols_mapping = column_aliases[file_name]
        path_ = os.path.join(OUTPUT_FOLDER, file_.filename)
        with open(path_, 'r') as file:
            file_contents = file.read()
        cand.data_conversion_code = file_contents
        candidates.append(cand)

    # Process the files
    input_candidates = transform_verify_save_data(candidates)
    if input_candidates is None:
        return jsonify({'error': "Some error occurred while converting the data. Please try again with right mappings. Please refresh the page and try again."}), 400
        
    response = {}
    for candidate in input_candidates:
        response[candidate.input_path.split("/")[-1].replace(".csv", "_converted.csv")] = "/download/" + candidate.output_path.replace("outputs/", "")
    print("response: ", response)

    response = {
        'outputFiles': [
            {'filename': output_filename, 'downloadUrl': download_url}
            for output_filename, download_url in response.items()
        ]
    }

    return jsonify(response)


if __name__ == '__main__':
    app.run()
