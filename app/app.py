import streamlit as st
import pandas as pd
import numpy as np
import base64
from rapidfuzz import fuzz, process, utils
import time
import os
import json
import glob
from loguru import logger

from pdf2image import convert_from_bytes
from dotenv import load_dotenv
from openai import OpenAI

# setting up logger for benchmarking, comment in to write logs to data/logs/benchmark_logs.log
logger.remove()
# logger.add("data/logs/benchmark_logs.log", rotation="10 MB", level="INFO")

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
                "text": """Using the written text in the image create a list of dictionaries where each dictionary consists of keys 'Name', 'Address', 'Date', and 'Ward'. Ignore all values in the box labeled "CIRCULATOR'S AFFIDAVIT OF CERTIFCATION". Ignore all values in the box labeled "SIGNATURE". Addresses belong to the name printed in the box to the immediate right of the box labeled "ADDRESS". Fill in the values of each dictionary with the correct entries for each key. Write all the values of the dictionary in full, except in the case of 'Address', which should be truncated to exclude APT and the following Apartment Number. Only output the list of dictionaries. No other intro text is necessary. The output should be in JSON format, and look like
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
        model="gpt-4o-mini",
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

def score_fuzzy_match_slim(ocr_name, full_name_list, scorer_=fuzz.token_ratio, limit_=1):
    list_of_match_tuples = process.extract(query=ocr_name, choices=full_name_list, scorer=scorer_, processor=utils.default_process, limit=limit_)
    return list_of_match_tuples


##
# TIERED SEARCH
##

def tiered_search(name, address):

    name_address_combo = f"{name} {address}"

    # Searches for a match within the Ward returned by OCR
    name_address_matches1 = score_fuzzy_match_slim(name_address_combo, voter_records_2023_df[voter_records_2023_df['WARD'] == f"{dict_['Ward']}.0"]["Full Name and Full Address"])
    if len(name_address_matches1) == 0:
        return '', 0.0, 0

    name_address__name1, name_address__score1, name_address__id1 = name_address_matches1[0]

    # if score is more than 85, return the tuple
    if name_address__score1 >= 85.0:
        return (name_address__name1, name_address__score1, name_address__id1)

    # if score is below 85, do additional processing
    else:

        # computing matches based on name and address; only considers all other wards
        name_address_matches2 = score_fuzzy_match_slim(name_address_combo, voter_records_2023_df[voter_records_2023_df['WARD'] != f"{dict_['Ward']}.0"]["Full Name and Full Address"])
        name_address__name2, name_address__score2, name_address__id2 = name_address_matches2[0]

        # if the new voter records score is greater than 85, return tuple
        if name_address__score2 >= 85.0:
            return (name_address__name2, name_address__score2, name_address__id2)

        # if score is less than 85, perform full records search based on name
        # and return results with highest score
        else:
            # computing matches based on name alone; considers full voter records
            full_name_matches = score_fuzzy_match_slim(name, voter_records_2023_df["Full Name"], scorer_=fuzz.ratio)
            full_name__name, full_name__score, full_name__id = full_name_matches[0]

            # find max from three scores
            max_indx = np.argmax([name_address__score1, name_address__score2, full_name__score])

            # return records associated with that max
            if max_indx== 0:
                return (name_address__name1, name_address__score1, name_address__id1)
            elif max_indx == 1:
                return (name_address__name2, name_address__score2, name_address__id2)
            else:
                address = voter_records_2023_df.loc[full_name__id, 'Full Address']
                full_name_address = f"{full_name__name} {address}"
                return (full_name_address, full_name__score, full_name__id)

##
# DELETE TEMPORARY FILES
##

def wipe_temp_dir(remove_status_bar=None):
    status = 0
    temp_files = [file.path for file in os.scandir('./temp_ocr_images') if file.is_file() and file.name !='.gitkeep']
    for file in temp_files:
        os.remove(file)
        if remove_status_bar:
            remove_status_bar.progress((status+1)/len(temp_files), text="Temporary Image Files Removed")
            status += 1
##
# DATA UPLOAD AND FULL NAME GENERATION
##

# reading in election data

voter_records_2023_df = pd.read_csv('data/raw_feb_23_city_wide.csv', dtype=str)

# creating full name, full address, and OCR columns
voter_records_2023_df['Full Name'] = voter_records_2023_df["First_Name"] + ' ' + voter_records_2023_df['Last_Name']
voter_records_2023_df['Full Address'] =  voter_records_2023_df["Street_Number"] + " " + voter_records_2023_df["Street_Name"] + " " + voter_records_2023_df["Street_Type"] + " " + voter_records_2023_df["Street_Dir_Suffix"]
voter_records_2023_df['Full Name and Full Address'] = voter_records_2023_df["Full Name"] + ' ' + voter_records_2023_df["Full Address"]
##
# STREAMLIT APPLICATION
##


# Using "with" notation
with st.sidebar:
    st.write("# Ballot Initiative Project")

## File Upload
## need to run streamlit run main_app/app.py --server.enableXsrfProtection false
## (From https://discuss.streamlit.io/t/file-upload-error-axioserror-request-failed-with-status-code-500/48169/19?u=mobolaji)
uploaded_ballots = st.file_uploader("Choose a file")

images = None
if uploaded_ballots is not None:
    start_time = time.time()
    with st.status("Downloading data...", expanded=True) as status:
        st.write("Saving PDF File")
        with open('temp_ocr_images/temp_file.pdf', 'wb') as f:
            f.write(uploaded_ballots.getvalue())

        st.write("Converting File to Bytes")
        images = convert_from_bytes(open("temp_ocr_images/temp_file.pdf", "rb").read())
        my_bar = st.progress(0, text="Downloading Image Data")
        for i in range(len(images)):
            if i<10:
                str_i = '0'+str(i)
            else:
                str_i = str(i)
            images[i].save(f"temp_ocr_images/page-{str_i}.jpg")

            my_bar.progress((i+1)/len(images), text=f"Downloading Image Data - page {i+1} of {len(images)}")

        status.update(label="Download complete!", state="complete", expanded=False)
    end_time = time.time()

    st.write(f'Download Time: {end_time-start_time:.3f} secs')
    logger.info(f"PDF Download & Parse Time: {end_time-start_time:3f}")

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
                wipe_temp_dir(remove_status_bar=removal_bar)
                status.update(label="Removal Complete!", state="complete", expanded=False)

##
# Cross checking database
##
# With Chat GPT API
add_df = pd.DataFrame()

if images:
    if st.button("Perform Database Cross Check"):
        matching_bar = st.progress(0, text="Performing Name Match")
        matched_list = list()
        start_time = time.time()
        pattern = os.path.join('.', 'temp_ocr_images', "*jpg")
        jpg_files = glob.glob(pattern)
        i = 0
        for jpg in jpg_files:
            resulting_data = extract_signature_info(jpg)
            for dict_ in resulting_data:
                temp_dict = dict()
                name_, score_, id_ = tiered_search(dict_['Name'], dict_['Address'])
                if name_ == '':
                    continue
                temp_dict['OCR RECORD'] = f"{dict_['Name']} {dict_['Address']}"
                temp_dict['MATCHED RECORD'] = name_
                temp_dict['SCORE'] = "{:.2f}".format(score_)
                temp_dict['VALID'] = False
                if score_ > 85.0:
                    temp_dict['VALID'] = True
                matched_list.append(temp_dict)

            matching_bar.progress((i+1)/len(jpg_files), text=f"Matching OCR Names - page {i+1} of {len(jpg_files)}")
            i+=1

        ## Editable Table
        add_df = pd.DataFrame(matched_list, columns=["OCR RECORD", "MATCHED RECORD", "SCORE", "VALID"])
        edited_df = st.data_editor(add_df, use_container_width=True) # 👈 An editable dataframe

        end_time = time.time()
        total_records = len(add_df)
        valid_matches = add_df["VALID"].sum()
        st.write(f"OCR and Match Time: {end_time-start_time:.3f} secs")
        st.write(f"Number of Matched Records: {valid_matches} out of {total_records}")
        logger.info(f"OCR and Match Time {end_time-start_time:.3f} secs | Matched Records: {valid_matches} of {total_records} - {(valid_matches/total_records * 100):2f}%")
##
# With Preprocessed Data
##

# if pre-processed data exists, we get a button that allows for testing the cross check
if os.path.exists('data/processed_ocr_data.json'):
    if st.button("Test Cross Check with Preprocessed OCR Data"):
            matching_bar = st.progress(0, text="Performing Name Match")
            matched_list = list()
            start_time = time.time()
            i = 0

            with open('data/processed_ocr_data.json', 'r') as file:
                resulting_data = json.load(file)

            for dict_ in resulting_data:
                temp_dict = dict()
                name_, score_, id_ = tiered_search(dict_['Name'], dict_['Address'])
                if name_ == '':
                    continue                
                temp_dict['OCR RECORD'] = f"{dict_['Name']} {dict_['Address']}"
                temp_dict['MATCHED RECORD'] = name_
                temp_dict['SCORE'] = "{:.2f}".format(score_)
                temp_dict['VALID'] = False
                if score_ > 85.0:
                    temp_dict['VALID'] = True
                matched_list.append(temp_dict)
                matching_bar.progress((i+1)/len(resulting_data), text=f"Matching OCR Names - page {i+1} of {len(resulting_data)}")
                i+=1

            ## Editable Table
            test_df = pd.DataFrame(matched_list, columns=["OCR RECORD", "MATCHED RECORD", "SCORE", "VALID"])
            edited_test_df = st.data_editor(test_df, use_container_width=True) # 👈 An editable dataframe

            end_time = time.time()
            total_test_records = len(test_df)
            valid_test_matches = test_df["VALID"].sum()
            st.write(f"Match Time: {end_time-start_time:.3f} secs")
            st.write(f"Number of Matched Records: {valid_test_matches} out of {total_test_records}")
            logger.info(f"Preprocessed Records Match Time {end_time-start_time:.3f} secs | Matched Records: {valid_test_matches} of {total_test_records} - {(valid_test_matches/total_test_records * 100):.2f}%")


# comment in to auto-wipe temporary files
# wipe_temp_dir()
