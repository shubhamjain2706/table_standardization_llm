# Task_zero_llm_project

To access the project hosted on the server, go to: http://shubhamjain2706.pythonanywhere.com/

## File structure

1. flask_app.py: main server file.
2. llm_module.py: module containing the logical code including all methods required to perform the tasks likw communicating with llm etc.
3. classes.py: contains the Candidate class.
4. templates/index.html: contains the front end interface code to display all prompts for the user to interact with.
5. sample_files/{file}.csv: All csv files that can be used to test the code functionality.
6. assignment_desc: contains the original assignment description.
7. REAMDE.md: contains the description of the project

## The workflow

To run the app server on your local, follow these steps:

1. Install packages using 'pip install langchain openai flask pandas'
2. Clone the repository on your local in a project folder named 'task_zero_llm'
3. Then paste your OPENAI API KEY in the llm_module.py
4. Finally open a terminal and cd to the above project and run 'python flask_app.py' to start the server. You can now access the app on yoru machine on http://127.0.0.1:5000/

To access the project hosted on the hosted server, just go to: http://shubhamjain2706.pythonanywhere.com/

Once you uplaod the files, the interface will take few seconds to show you all the options for yor mappings for each candidate file and once submitted yo can download the code conversion files.
You can then review and reupload the files to start the conversion process. Understand that the code conversion produced by LLM will highly depend on the mappings you choose since wrong mappings
will misinform the LLM and it will try to write wrong code to convert the candidate data to template data structure.

## Possible improvements and edge cases handling

1. Improved prompts: As more variety of datasets might come in, our prompts might not give best results always. So it would always be better to have some kind of monitoring or a user-based feedback loop present to monitor the performance of our prompts and make sure they stay relevant according to our needs.
2. Improved mappings: Apart from the above scenario, the prompts to the LLM in general also can be quite non-deterministic thus ending up affecting our columns mapping at times. The solution to tackle this would be to add more data when asking the LLM for mappings to allow it to understand the structure in a better manner to make it less error prone to wrong mappings.
3. Sanity checks in the conversion code produced by LLM: We can improve our prompts when asking the LLM to add some sanity checks in the data conversion code so as to make it more robust.
4. Pre/post-process data checks: Improving LLM prompts to allow for better handling of missing, incorrect values both in pre and post data in the conversion code.
5. More automated checks: once the data is converted, even though it can be inspected by the humans, more automated checks can be added to make sure no errors are there.

## Owner

- Name: Shubham Kumar Jain
- Email: shubham.jain2706@gmail.com
