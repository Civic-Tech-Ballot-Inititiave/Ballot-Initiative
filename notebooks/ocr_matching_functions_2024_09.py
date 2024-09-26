# needed libraries
### structured outputs; replacements
from typing import List
from pydantic import BaseModel
import base64
import os
import json
import time
from tqdm.notebook import tqdm
from PIL import Image
from rapidfuzz import fuzz, process, utils
from pdf2image import convert_from_path
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd

# local environment storage
repo_name = 'Ballot-Initiative'
REPODIR = os.getcwd().split(repo_name)[0] + repo_name
load_dotenv(os.path.join(REPODIR, '.env'), override=True)

# open ai api key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HELICONE_PERSONAL_API_KEY = os.getenv("HELICONE_PERSONAL_API_KEY")

class OCREntry(BaseModel):
    Name: str
    Address: str
    Date: str
    Ward: int


class OCRData(BaseModel):
    Data: List[OCREntry]


###
## OCR FUNCTIONS
###

# Function is needed to put image in proper format for uploading
# From: https://stackoverflow.com/questions/77284901/upload-an-image-to-chat-gpt-using-the-api
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def image_cropper(file_path):

    # Opens a image in RGB mode
    im = Image.open(file_path)

    # Size of the image in pixels (size of original image)
    # (This is not mandatory)
    width, height = im.size

    # Setting the points for cropped image
    left = 0
    top = int(0.385*height)
    right = width
    bottom = int(0.725* height)
    
    # Cropped image of above dimension
    # (It will not change original image)
    im1 = im.crop((left, top, right, bottom))

    im1.save(file_path)
    
    # Shows the image in image viewer
    return im1

def collecting_pdf_encoded_images(file_path):

    print("Converting PDF file to Image Format")
    # getting collection of images
    images = convert_from_path(file_path)
    print()
    print("Cropping Images and Converting to Bytes Objects")
    # list of images
    encoded_image_list = list()
    for k in tqdm(range(len(images))):

        # selecting image
        image = images[k]

        # saving image name
        image_name = f"temp_image_{k}.jpg"
        image.save(image_name)
        
        # crop image; saves under same name
        image_cropper(image_name)

        # encoding result as an image
        encoded_result = encode_image(image_name)
        encoded_image_list.append(encoded_result)

        # cleaning up saved image
        os.remove(image_name)   

    return encoded_image_list


def extract_from_encoding(base64_image):

    """
    Extracts names and addresses from single ballot image.
    Uses base64_image
    """

    # open AI client definition
    client = OpenAI(api_key=OPENAI_API_KEY,
                    base_url="https://oai.helicone.ai/v1",  # Set the API endpoint
                    default_headers= {  # Optionally set default headers or set per request (see below)
                          "Helicone-Auth": f"Bearer {HELICONE_PERSONAL_API_KEY}", }
                          )                    

    # prompt message
    messages = [
          {
            "role": "user",
            "content": [
              {
                "type": "text",
                "text": """Using the written text in the image create a list of dictionaries where each dictionary consists of keys 'Name', 'Address', 'Date', and 'Ward'. Fill in the values of each dictionary with the correct entries for each key. Write all the values of the dictionary in full. Only output the list of dictionaries. No other intro text is necessary."""
              },
              {
                "type": "text",
                "text": """Remove the city name 'Washington, DC' and any zip codes from the 'Address' values."""
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

    results = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0,
            response_format= OCRData
            )     

    # parsing results
    parsed_results = results.choices[0].message.parsed    

    # dictionary results
    parsed_list = json.loads(parsed_results.json())['Data']
    
    return parsed_list

# function for adding data
def add_metadata(initial_data, page_no : int, filename : str):

    final_data = list()
    for row in range(len(initial_data)):
        dict_ = initial_data[row]
        temp_dict = dict(dict_)
        temp_dict["Page Number"] = page_no+1
        temp_dict["Row Number"] = row+1
        temp_dict["Filename"] = filename
        final_data.append(temp_dict)

    return final_data

def collect_ocr_data(filedir, filename, max_page_num = None):

    # collecting images
    encoded_images = collecting_pdf_encoded_images(f"{filedir}/{filename}")

    # selecting pages 
    encoded_images = encoded_images[:max_page_num]

    print()
    print("Files Successfully Converted to Bytes")      

    print()
    print("Performing OCR to read Names and Addresses")       

    full_data = list()
    for page_no in tqdm(range(len(encoded_images))):
        encoding = encoded_images[page_no]
        print(f"Processing Page {page_no+1} of {filename}")
        ocr_data = extract_from_encoding(encoding)
        ocr_data = add_metadata(ocr_data, page_no, filename)
        full_data +=ocr_data

    return full_data


def create_ocr_df(filedir, filename, max_page_num = None): 

    # gathering ocr_data
    ocr_data = collect_ocr_data(filedir, filename, max_page_num = max_page_num)

    # convert dataframe
    ocr_df = pd.DataFrame(data = ocr_data)

    # renaming columns
    ocr_df.rename(columns = {"Name": "OCR Name", 
                            "Address":"OCR Address", 
                            "Ward": "OCR Ward"}, 
                            inplace=True)

    # converting all caps names to title format
    ocr_df["OCR Name"] = ocr_df["OCR Name"].apply(lambda row: row.title())

    return ocr_df    


###
## MATCHING FUNCTIONS
###

def create_select_voter_records(voter_records):

    # creating full name
    cols = ["First_Name", "Last_Name"]
    voter_records["Full Name"] = voter_records[cols].apply(lambda row: " ".join(row.values.astype(str)), axis=1)

    # creating full address
    cols = ["Street_Number", "Street_Name", "Street_Type", "Street_Dir_Suffix"]
    voter_records["Full Address"] = voter_records[cols].apply(lambda row: " ".join(row.values.astype(str)), axis=1)

    # only getting the full list of names
    limited_voter_records = voter_records[["Full Name", "Full Address"]]

    return limited_voter_records


def score_fuzzy_match_slim(ocr_result, comparison_list, scorer_=fuzz.ratio, limit_=10):
    list_of_match_tuples = process.extract(query=ocr_result, choices=comparison_list, scorer=scorer_, processor=utils.default_process, limit=limit_)
    return list_of_match_tuples

def get_matched_name_address(ocr_name, ocr_address, select_voter_records): 

    # list of voter names
    voter_name_list = select_voter_records["Full Name"]

    # getting 10 highest match results
    high_score_name_results = score_fuzzy_match_slim(ocr_result = ocr_name, 
                                                     comparison_list = voter_name_list, 
                                                     limit_ = 10)    

    # getting indices for highest match results
    high_score_name_idxs = [elem[-1] for elem in high_score_name_results]

    # getting the addresses for the highest match results
    full_addresses_for_high_scores =  list(select_voter_records.iloc[high_score_name_idxs]["Full Address"])

    # getting the scores between ocr address and full address list
    cut_address_results = score_fuzzy_match_slim(ocr_result = ocr_address, 
                                                 comparison_list = full_addresses_for_high_scores)

    # getting list of high scores
    high_score_list = list()
    for name_tuple, address_tuple in zip(high_score_name_results, cut_address_results):
        
        # getting name and addresses
        name, name_score, idx = name_tuple
        address, address_score, _ = address_tuple

        # getting harmonic means
        harmonic_mean_score = 2*name_score*address_score/(name_score+address_score)

        # appending to list
        high_score_list.append([name, address, harmonic_mean_score, idx])

    # sorting by score
    high_score_list.sort(key=lambda x: x[2], reverse= True)    

    return high_score_list

def create_ocr_matched_df(ocr_df, select_voter_records, threshold = 92.5):

    # getting OCR name and address
    ocr_names = list(ocr_df["OCR Name"])
    ocr_addresses = list(ocr_df["OCR Address"])    

    # creating new columns for matched names, addresses and scores
    matched_name_list = list()
    matched_address_list = list()
    net_score_list = list()

    for ocr_name, ocr_address in tqdm(zip(ocr_names, ocr_addresses)):

        # getting list of high scorers
        high_score_list = get_matched_name_address(ocr_name, ocr_address, select_voter_records)

        # getting the highest scores for name
        matched_name, matched_address, net_score, _  = high_score_list[0]

        # appending results
        matched_name_list.append(matched_name)
        matched_address_list.append(matched_address)
        net_score_list.append(net_score)

    # adding new columns to df
    ocr_df["Matched Name"] = matched_name_list
    ocr_df["Matched Address"] = matched_address_list
    ocr_df["Match Score"] = net_score_list    
    ocr_df["Valid"] = ocr_df["Match Score"].apply(lambda row: row>=threshold)

    # reordering columns; keeping only the relevant ones
    column_order = ["OCR Name", "OCR Address", "Matched Name", "Matched Address", "Date", "Match Score", "Valid", "Page Number", "Row Number", "Filename"]
    ocr_df_simple = ocr_df[column_order]

    return ocr_df_simple   