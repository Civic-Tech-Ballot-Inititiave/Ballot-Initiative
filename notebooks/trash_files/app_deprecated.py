import streamlit as st
import pandas as pd
import time
import os

from pdf2image import convert_from_bytes
from dotenv import load_dotenv
from openai import OpenAI

from fuzzy_match_helper import score_function_fuzz
from ocr_helper import extract_signature_info


# starting Open AI client
load_dotenv() 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# reading in election data
election_data = pd.read_csv('../raw_feb_23_city_wide.csv', dtype = str)

# generating list of names
full_name_list = [str(char1) + ' ' + str(char2) for char1, char2 in zip(list(election_data['First_Name']), list(election_data['Last_Name']))]

# full function
def produce_match_df(filename, verbose = False, threshold = 0.90):

    resulting_data = extract_signature_info(filename, verbose = verbose)    

    matched_list = list()
    for dict_ in resulting_data:
        temp_dict = dict()
        high_match_ids = score_function_fuzz(dict_['Name'], full_name_list)    
        id_, score_ = high_match_ids[0]
        temp_dict['OCR NAME'] = dict_['Name']
        temp_dict['MATCHED NAME'] = election_data.iloc[id_]['First_Name'] + ' ' + election_data.iloc[id_]['Last_Name']
        temp_dict['SCORE'] = score_
        temp_dict['VALID'] = False
        if score_ > threshold: 
            temp_dict['VALID'] = True
        matched_list.append(temp_dict)

    df = pd.DataFrame(matched_list)

    return df



## Streamlit sidebar

# Using object notation
# add_selectbox = st.sidebar.selectbox(
#     "How would you like to be contacted?",
#     ("Email", "Home phone", "Mobile phone")
# )


# Using "with" notation
with st.sidebar:
    st.write("# Ballot Initiative Project")
    # add_radio = st.radio(
    #     "Choose a shipping method",
    #     ("Standard (5-15 days)", "Express (2-5 days)")
    # )

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

if images:
    images = images[:5]


# Using "with" notation
with st.sidebar:

    # remove temporary files
    progress_removal_text = "Removal in progress. Please wait."
    if images:
        if st.button("Remove Temporary Files"):

            with st.status("Removing Data...", expanded=True) as status:               
                removal_bar = st.progress(0, text="Removing Image Files")
                # os.remove("temp_file.pdf")
                for i in range(len(images)):
                    if i<10:
                        str_i = '0'+str(i)
                    else:
                        str_i = str(i)            
                    os.remove(f"page-{str_i}.jpg")

                    removal_bar.progress((i+1)/len(images), text="Temporary Image Files Removed")

                status.update(label="Removal Complete!", state="complete", expanded=False)


if images: 
    if st.button("Perform Database Cross Check"):    
        matching_bar = st.progress(0, text="Performing Name Match")  

        ## Editable Table
        # df0 = pd.DataFrame(columns=["OCR NAME", "MATCHED NAME", "SCORE", "VALID"])
        # edited_df = st.dataframe(df0, use_container_width=True) # 👈 An editable dataframe    
        matched_list = list()   

        start_time = time.time()            
        for i in range(len(images)):
            if i<10:
                str_i = '0'+str(i)
            else:
                str_i = str(i)
            filename = f"page-{str_i}.jpg"
            resulting_data = extract_signature_info(filename, verbose = False)    
            
            
            for dict_ in resulting_data:
                temp_dict = dict()
                high_match_ids = score_function_fuzz(dict_['Name'], full_name_list)    
                id_, score_ = high_match_ids[0]
                temp_dict['OCR NAME'] = str(dict_['Name'])
                temp_dict['MATCHED NAME'] = str(election_data.iloc[id_]['First_Name'] + ' ' + election_data.iloc[id_]['Last_Name'])
                temp_dict['SCORE'] = score_
                temp_dict['VALID'] = False
                if score_ > 0.85: 
                    temp_dict['VALID'] = True
                matched_list.append(temp_dict)

            matching_bar.progress((i+1)/len(images), text=f"Matching OCR Names - page {i+1} of {len(images)}")

        ## Editable Table
        add_df = pd.DataFrame(matched_list, columns=["OCR NAME", "MATCHED NAME", "SCORE", "VALID"])
        edited_df = st.data_editor(add_df, use_container_width=True) # 👈 An editable dataframe     

            # edited_df.add_rows(add_df)                   

        # df = pd.DataFrame(matched_list)

        ## Editable Table
        # edited_df = st.data_editor(df) # 👈 An editable dataframe

        end_time = time.time()

        st.write(f'OCR and Match Time: {end_time-start_time:.3f} secs')   
        st.write(f'Number of Matched Records: {sum(list(add_df['VALID']))} out of {len(add_df)}')   
        




## progress bar; https://docs.streamlit.io/develop/api-reference/status/st.progress
# progress_text = "Operation in progress. Please wait."
# my_bar = st.progress(0, text=progress_text)

# for percent_complete in range(100):
#     time.sleep(0.01)
#     my_bar.progress(percent_complete + 1, text=progress_text)
# time.sleep(1)
# my_bar.empty()

# st.button("Rerun")

## spinner; https://docs.streamlit.io/develop/api-reference/status/st.spinner
# with st.spinner('Wait for it...'):
#     time.sleep(5)
# st.success('Done!')


## status; https://docs.streamlit.io/develop/api-reference/status/st.status
# with st.status("Downloading data...", expanded=True) as status:
#     st.write("Searching for data...")
#     time.sleep(2)
#     st.write("Found URL.")
#     time.sleep(1)
#     st.write("Downloading data...")
#     time.sleep(1)
#     status.update(label="Download complete!", state="complete", expanded=False)

# st.button("Rerun Again")


# favorite_command = edited_df.loc[edited_df["rating"].idxmax()]["command"]
# st.markdown(f"Your favorite command is **{favorite_command}** 🎈")


