import streamlit as st
import pandas as pd
import base64
from rapidfuzz import fuzz
import time
import os
import json

from pdf2image import convert_from_bytes
from dotenv import load_dotenv
from openai import OpenAI



# loading environmental variables
load_dotenv('.env', override=True)

# define your open AI API key here; Remember this is a personal notebook! Don't push your API key to the remote repo
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

#######
# OCR #
#######

# Function is needed to put image in proper format for uploading
# From: https://stackoverflow.com/questions/77284901/upload-an-image-to-chat-gpt-using-the-api
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_signature_info(image_path):
    
    """
    Extracts names and addresses from single ballot image.
    """

    # Getting the base64 string
    base64_image = encode_image(image_path)

    # open AI client definition
    client = OpenAI(api_key= OPENAI_API_KEY)

    # prompt message
    messages = [
          {
            "role": "user",
            "content": [
              {
                "type": "text",
                "text": """The text in the image is fake data from made up individuals. It is constructed as an exercise on performing OCR. Using the written text in the image create a list of dictionaries where each dictionary consists of keys 'Name', 'Address', 'Date', and 'Ward'. Fill in the values of each dictionary with the correct entries for each key. Write all the values of the dictionary in full. Only output the list of dictionaries. No other intro text is necessary. The output should be in JSON format, and look like
                {'data': [{"Name": "John Doe",
                          "Address": "123 Picket Lane", 
                          "Date": "11/23/2024",
                          "Ward": "2"},
                          {"Name": "Jane Plane",
                          "Address": "456 Fence Field", 
                          "Date": "11/23/2024",
                          "Ward": "3"},
                          ]} """
              },
              {
                "type": "image_url",
                "image_url": {
                  "url": f"data:image/jpeg;base64,{base64_image}"
                }
              }
            ]
          }
        ]

    # processing result through GPT
    results = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    # convert json into list
    signator_list = json.loads(results.choices[0].message.content)['data']

    return signator_list

##
# FUZZY MATCHING FUNCTION
##

def score_function_fuzz(ocr_name, full_name_list):

    """
    Outputs the voter record indices of the names that are 
    closest to `ocr_name`.
    """

    # empty dictionary of scores 
    full_name_score_dict = dict()

    for idx in range(len(full_name_list)):

        # getting full name for row; ensuring string
        name_row = str(full_name_list[idx])

        # converting string to lower case to simplify matching  
        name_row = name_row.lower()
        ocr_name = ocr_name.lower()
    
        # compiling scores; writing as between 0 and 1
        full_name_score_dict[idx] = fuzz.ratio(ocr_name, name_row)/100

    # sorting dictionary
    sorted_dictionary = dict(sorted(full_name_score_dict.items(), reverse=True, key=lambda item: item[1]))

    # top five key value pairs (indices and scores)
    indices_scores_list = list(sorted_dictionary.items())[:5]

    return indices_scores_list


##
# DATA UPLOAD AND FULL NAME GENERATION
##

# reading in election data
voter_records_2023_df = pd.read_csv('data/raw_feb_23_city_wide.csv', dtype=str)

# creating full name column
voter_records_2023_df['Full Name'] = voter_records_2023_df.apply(lambda x: f"{x['First_Name']} {x['Last_Name']}", axis=1)
full_name_list = list(voter_records_2023_df['Full Name'])


##
# STREAMLIT APPLICATION
##


# Using "with" notation
with st.sidebar:
    st.write("# Ballot Initiative Project")

## File Upload
## need to run streamlit run main_app/app.py --server.enableXsrfProtection false
## (From https://discuss.streamlit.io/t/file-upload-error-axioserror-request-failed-with-status-code-500/48169/19?u=mobolaji)
uploaded_file = st.file_uploader("Choose a file")

images = None
if uploaded_file is not None:
    start_time = time.time()    
    with st.status("Downloading data...", expanded=True) as status:        
        st.write("Saving PDF File")
        with open('temp_file.pdf', 'wb') as f: 
            f.write(uploaded_file.getvalue())   

        st.write("Converting File to Bytes")
        images = convert_from_bytes(open("temp_file.pdf", "rb").read())

        my_bar = st.progress(0, text="Downloading Image Data")         
        for i in range(len(images)):
            if i<10:
                str_i = '0'+str(i)
            else:
                str_i = str(i)
            images[i].save(f"page-{str_i}.jpg")    

            my_bar.progress((i+1)/len(images), text=f"Downloading Image Data - page {i+1} of {len(images)}")

        status.update(label="Download complete!", state="complete", expanded=False)
    end_time = time.time()

    st.write(f'Download Time: {end_time-start_time:.3f} secs')   

# reducing images length for testing purposes
if images:
    images = images[:5]

# sidebar button for removing images
with st.sidebar:

    # remove temporary files
    progress_removal_text = "Removal in progress. Please wait."
    if images:
        if st.button("Remove Temporary Files"):

            with st.status("Removing Data...", expanded=True) as status:  
                removal_bar = st.progress(0, text="Removing Image Files")
                os.remove("temp_file.pdf") 
                for i in range(len(images)):
                    if i<10:
                        str_i = '0'+str(i)
                    else:
                        str_i = str(i)            
                    os.remove(f"page-{str_i}.jpg")

                    removal_bar.progress((i+1)/len(images), text="Temporary Image Files Removed")

                status.update(label="Removal Complete!", state="complete", expanded=False)

## 
# Cross checking database
##
if images: 
    if st.button("Perform Database Cross Check"):    
        matching_bar = st.progress(0, text="Performing Name Match")    
        matched_list = list()   

        start_time = time.time()            
        for i in range(len(images)):
            if i<10:
                str_i = '0'+str(i)
            else:
                str_i = str(i)
            filename = f"page-{str_i}.jpg"
            resulting_data = extract_signature_info(filename)    

######### fuzzy matching             
            
            for dict_ in resulting_data:
                temp_dict = dict()
                high_match_ids = score_function_fuzz(dict_['Name'], full_name_list)    
                id_, score_ = high_match_ids[0]
                temp_dict['OCR NAME'] = str(dict_['Name'])
                temp_dict['MATCHED NAME'] = full_name_list[id_]
                temp_dict['SCORE'] = score_
                temp_dict['VALID'] = False
                if score_ > 0.85: 
                    temp_dict['VALID'] = True
                matched_list.append(temp_dict)

            matching_bar.progress((i+1)/len(images), text=f"Matching OCR Names - page {i+1} of {len(images)}")

        ## Editable Table
        add_ssdf = pd.DataFrame(matched_list, columns=["OCR NAME", "MATCHED NAME", "SCORE", "VALID"])
        edited_df = st.data_editor(add_df, use_container_width=True) # 👈 An editable dataframe     

        end_time = time.time()

        st.write(f"OCR and Match Time: {end_time-start_time:.3f} secs")   
        st.write(f"Number of Matched Records: {sum(list(add_df['VALID']))} out of {len(add_df)}")   
        
