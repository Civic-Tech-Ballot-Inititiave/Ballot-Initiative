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
import asyncio
from concurrent.futures import ThreadPoolExecutor
from itertools import islice

# local environment storage
repo_name = 'Ballot-Initiative'
REPODIR = os.getcwd().split(repo_name)[0] + repo_name
load_dotenv(os.path.join(REPODIR, '.env'), override=True)

# open ai api key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HELICONE_PERSONAL_API_KEY = os.getenv("HELICONE_PERSONAL_API_KEY")

###
## OCR FUNCTIONS
###

class OCREntry(BaseModel):
    Name: str
    Address: str
    Date: str
    Ward: int


class OCRData(BaseModel):
    Data: List[OCREntry]



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

def extract_from_encoding(base64_image):
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

async def extract_from_encoding_async(base64_image):
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

async def process_batch_async(encodings, batch_size=5):
    """
    Process a batch of images concurrently
    """
    tasks = []
    for encoding in encodings:
        tasks.append(extract_from_encoding_async(encoding))
    results = await asyncio.gather(*tasks)
    return results

def get_or_create_event_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

def collect_ocr_data(filedir, filename, max_page_num = None, batch_size=10):

    # collecting images
    encoded_images = collecting_pdf_encoded_images(os.path.join(filedir, filename))

    # selecting pages
    if max_page_num: 
        encoded_images = encoded_images[:max_page_num]

    print()
    print("Files Successfully Converted to Bytes")
    print("Performing OCR to read Names and Addresses")

    full_data = []
    total_pages = len(encoded_images)

    # getting event loop
    loop = get_or_create_event_loop()
    
    # Process in batches
    print("Processing Batches in {} per batch".format(batch_size))
    for i in tqdm(range(0, total_pages, batch_size)):
        batch = encoded_images[i:i + batch_size]
        print(f"\nProcessing batch {i//batch_size + 1} of {(total_pages + batch_size - 1)//batch_size}")
        
        # Run async batch processing using the event loop
        batch_results = loop.run_until_complete(process_batch_async(batch))   
        
        # Add metadata for each result in the batch
        for page_idx, result in enumerate(batch_results):
            current_page = i + page_idx
            ocr_data = add_metadata(result, current_page, filename)
            full_data.extend(ocr_data)
            # print(f"Completed Page {current_page + 1} of {total_pages}")

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
    """Optimized fuzzy matching"""
    # Convert to numpy array for faster operations
    comparison_array = np.array(comparison_list)
    
    # Vectorize the scorer function
    vectorized_scorer = np.vectorize(lambda x: scorer_(ocr_result, x))
    
    # Calculate all scores at once
    scores = vectorized_scorer(comparison_array)
    
    # Get top N indices
    top_indices = np.argpartition(scores, -limit_)[-limit_:]
    top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
    
    # Return results in required format
    return [(comparison_array[i], scores[i], i) for i in top_indices]

def get_matched_name_address(ocr_name, ocr_address, select_voter_records):
    """Optimized name and address matching"""
    # Convert to numpy arrays once
    voter_names = select_voter_records["Full Name"].values
    voter_addresses = select_voter_records["Full Address"].values
    
    # Get name matches
    name_matches = score_fuzzy_match_slim(ocr_name, voter_names)
    
    # Get corresponding addresses for top name matches
    matched_indices = [x[2] for x in name_matches]
    relevant_addresses = voter_addresses[matched_indices]
    
    # Get address matches only for relevant addresses
    address_matches = score_fuzzy_match_slim(ocr_address, relevant_addresses)
    
    # Calculate harmonic means using numpy
    name_scores = np.array([x[1] for x in name_matches])
    addr_scores = np.array([x[1] for x in address_matches])
    harmonic_means = 2 * name_scores * addr_scores / (name_scores + addr_scores)
    
    # Create and sort results
    results = list(zip(
        [x[0] for x in name_matches],
        [x[0] for x in address_matches],
        harmonic_means,
        matched_indices
    ))
    return sorted(results, key=lambda x: x[2], reverse=True)

def create_ocr_matched_df(ocr_df, select_voter_records, threshold=92.5):
    """Optimized DataFrame matching"""
    # Pre-compute numpy arrays
    names = select_voter_records["Full Name"].values
    addresses = select_voter_records["Full Address"].values
    
    # Process in chunks for better memory management
    chunk_size = 1000
    results = []
    
    for chunk_start in tqdm(range(0, len(ocr_df), chunk_size)):
        chunk = ocr_df.iloc[chunk_start:chunk_start + chunk_size]
        
        # Process chunk in parallel
        with ThreadPoolExecutor() as executor:
            chunk_results = list(executor.map(
                lambda row: get_matched_name_address(
                    row["OCR Name"],
                    row["OCR Address"],
                    select_voter_records
                ),
                [row for _, row in chunk.iterrows()]
            ))
        
        # Extract best matches
        chunk_matches = [(res[0][0], res[0][1], res[0][2]) for res in chunk_results]
        results.extend(chunk_matches)
    
    # Create result DataFrame efficiently
    match_df = pd.DataFrame(
        results,
        columns=["Matched Name", "Matched Address", "Match Score"]
    )
    
    # Combine results with original DataFrame
    result_df = pd.concat([
        ocr_df,
        match_df
    ], axis=1)
    
    # Add Valid column
    result_df["Valid"] = result_df["Match Score"] >= threshold
    
    # Reorder columns
    column_order = [
        "OCR Name", "OCR Address", "Matched Name", "Matched Address",
        "Date", "Match Score", "Valid", "Page Number", "Row Number", "Filename"
    ]
    
    return result_df[column_order]