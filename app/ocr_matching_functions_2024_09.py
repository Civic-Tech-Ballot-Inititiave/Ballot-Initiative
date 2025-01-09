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
from openai import OpenAI, AsyncOpenAI
import pandas as pd
import io
import numpy as np

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


def collecting_pdf_encoded_images(file_path):
    """Convert PDF pages to encoded images, cropping to target area.
    Returns list of base64 encoded image strings."""
    
    print("Converting PDF file to Image Format")
    # Convert PDF pages to images in memory
    images = convert_from_path(file_path)
    
    print("\nCropping Images and Converting to Bytes Objects")
    encoded_image_list = []
    
    # Process each page
    for image in tqdm(images):
        # Get image dimensions
        width, height = image.size
        
        # Crop directly in memory
        cropped = image.crop((
            0,                  # left
            int(0.385*height),  # top 
            width,             # right
            int(0.725*height)  # bottom
        ))
        
        # Convert to bytes and encode in one step
        with io.BytesIO() as bio:
            cropped.save(bio, format='JPEG')
            encoded = base64.b64encode(bio.getvalue()).decode('utf-8')
            encoded_image_list.append(encoded)

    return encoded_image_list


async def extract_from_encoding(base64_image):
    """
    Extracts names and addresses from single ballot image asynchronously.
    Uses base64_image
    """

    # open AI client definition 
    client = AsyncOpenAI(api_key=OPENAI_API_KEY,
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

    results = await client.beta.chat.completions.parse(
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
    """
    Creates a simplified DataFrame with full names and addresses from voter records.
    
    Args:
        voter_records (pd.DataFrame): DataFrame containing voter information with columns for
            first name, last name, and address components.
            
    Returns:
        pd.DataFrame: DataFrame with 'Full Name' and 'Full Address' columns
    """
    # Create full name by combining first and last names
    name_components = ["First_Name", "Last_Name"] 
    voter_records["Full Name"] = voter_records[name_components].astype(str).agg(" ".join, axis=1)

    # Create full address by combining address components
    address_components = ["Street_Number", "Street_Name", "Street_Type", "Street_Dir_Suffix"]
    voter_records["Full Address"] = voter_records[address_components].astype(str).agg(" ".join, axis=1)

    # Return only the columns we need
    return voter_records[["Full Name", "Full Address"]]


def score_fuzzy_match_slim(ocr_result, comparison_list, scorer_=fuzz.ratio, limit_=10):
    # Pre-process query once instead of for each comparison
    processed_query = utils.default_process(ocr_result)
    
    # Pre-process all choices at once
    processed_choices = [utils.default_process(choice) for choice in comparison_list]
    
    # Calculate scores in bulk using list comprehension
    scores = [(choice, scorer_(processed_query, proc_choice), idx) 
             for idx, (choice, proc_choice) in enumerate(zip(comparison_list, processed_choices))]
    
    # Sort once and take top N
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:limit_]

def get_matched_name_address(ocr_name, ocr_address, select_voter_records):
    """
    Get matched names and addresses using fuzzy matching with optimized performance.
    Returns list of [name, address, score, index] sorted by score descending.
    """
    # Get top 10 name matches efficiently using numpy array
    voter_name_list = select_voter_records["Full Name"].values
    high_score_name_results = score_fuzzy_match_slim(ocr_result=ocr_name,
                                                    comparison_list=voter_name_list,
                                                    limit_=10)

    # Extract indices and get corresponding addresses in one operation
    high_score_name_idxs = np.array([elem[-1] for elem in high_score_name_results])
    full_addresses = select_voter_records.iloc[high_score_name_idxs]["Full Address"].values

    # Get address match scores
    cut_address_results = score_fuzzy_match_slim(ocr_result=ocr_address,
                                                comparison_list=full_addresses)

    # Calculate scores using vectorized operations
    name_scores = np.array([x[1] for x in high_score_name_results])
    addr_scores = np.array([x[1] for x in cut_address_results])
    harmonic_means = 2 * name_scores * addr_scores / (name_scores + addr_scores)

    # Create result list efficiently
    high_score_list = [
        [name_tuple[0], addr_tuple[0], score, name_tuple[2]]
        for name_tuple, addr_tuple, score in zip(
            high_score_name_results, cut_address_results, harmonic_means
        )
    ]

    # Sort in-place by score
    high_score_list.sort(key=lambda x: x[2], reverse=True)

    return high_score_list

def create_ocr_matched_df(ocr_df, select_voter_records, threshold = 92.5):
    # Process all names and addresses at once using pandas apply
    def process_row(row):
        high_score_list = get_matched_name_address(row["OCR Name"], row["OCR Address"], select_voter_records)
        matched_name, matched_address, net_score, _ = high_score_list[0]
        return pd.Series({
            "Matched Name": matched_name,
            "Matched Address": matched_address, 
            "Match Score": net_score
        })

    # Apply processing to all rows at once
    tqdm.pandas()
    match_results = ocr_df.progress_apply(process_row, axis=1)
    
    # Add new columns efficiently
    ocr_df = ocr_df.assign(
        **match_results,
        Valid = lambda x: x["Match Score"] >= threshold
    )

    # Select and reorder columns
    column_order = ["OCR Name", "OCR Address", "Matched Name", "Matched Address", "Date", 
                   "Match Score", "Valid", "Page Number", "Row Number", "Filename"]
    
    return ocr_df[column_order]