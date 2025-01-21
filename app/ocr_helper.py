# needed libraries
### structured outputs; replacements
from typing import List
from pydantic import BaseModel
import base64
import os
import json
from tqdm.notebook import tqdm
from dotenv import load_dotenv
from openai import AsyncOpenAI
import pandas as pd
import asyncio
import fitz  # Add this import at the top with other imports
import streamlit as st
import logging
from datetime import datetime

# Set up logging
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Create a logger
logger = logging.getLogger('ocr_processing')
logger.setLevel(logging.INFO)

# Create handlers
log_filename = f"ocr_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(os.path.join(log_directory, log_filename))
console_handler = logging.StreamHandler()

# Create formatters and add it to handlers
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

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

# load config
with open('config.json', 'r') as f:
    config = json.load(f)

def collecting_pdf_encoded_images(file_path : str) -> List[str]:
    """Convert PDF pages to encoded images, cropping to target area.
    Returns list of base64 encoded image strings."""
    
    logger.info(f"Starting PDF conversion for file: {file_path}")
    encoded_image_list = []
    
    # Open PDF document
    pdf_document = fitz.open(file_path)
    logger.info(f"PDF opened successfully. Total pages: {len(pdf_document)}")
    
    print("\nCropping Images and Converting to Bytes Objects")
    # Process each page
    for page in tqdm(pdf_document):
        # Get page dimensions
        rect = page.rect
        width = rect.width
        height = rect.height
        
        # Calculate crop rectangle
        crop_rect = fitz.Rect(
            0,                                  # left
            height * config['TOP_CROP'],        # top
            width,                              # right
            height * config['BOTTOM_CROP']      # bottom
        )
        
        # Get pixmap with cropped area and grayscale
        pix = page.get_pixmap(
            matrix=fitz.Matrix(1, 1),  # zoom factors of 1 = 72 dpi
            colorspace="gray",         # convert to grayscale
            clip=crop_rect            # crop to our target area
        )
        
        # Convert to bytes and encode
        img_bytes = pix.tobytes(output="jpeg")
        encoded = base64.b64encode(img_bytes).decode('utf-8')
        encoded_image_list.append(encoded)
    
    pdf_document.close()
    logger.info(f"Completed PDF conversion. Generated {len(encoded_image_list)} encoded images")
    return encoded_image_list

async def extract_from_encoding_async(base64_image: str) -> List[dict]:
    """
    Extracts names and addresses from single ballot image asynchronously.
    Uses base64_image

    Args:
        base64_image: The base64 encoded image to extract data from.

    Returns:
        list: A list of dictionaries with the OCR data.
    """
    logger.debug("Starting OCR extraction for image")

    try:
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
        logger.debug(f"Successfully extracted {len(parsed_list)} entries from image")
        return parsed_list
        
    except Exception as e:
        logger.error(f"Error in OCR extraction: {str(e)}")
        raise

# function for adding data
def add_metadata(initial_data : List[dict], 
                  page_no : int, 
                  filename : str) -> List[dict]:
    """
    Adds page number, row number, and filename metadata to the recognized signatures

    Args:
        initial_data (List[dict]): The initial data to add metadata to.
        page_no (int): The page number of the current page.
        filename (str): The name of the file.

    Returns:
        List[dict]: The final data with metadata.
    """

    final_data = list()
    for row, data in enumerate(initial_data):
        temp_dict = dict(data)
        temp_dict["Page Number"] = page_no+1
        temp_dict["Row Number"] = row+1
        temp_dict["Filename"] = filename
        final_data.append(temp_dict)

    return final_data

async def process_batch_async(encodings : List[str]) -> List[List[dict]]:
    """
    Process a batch of images concurrently
    """
    tasks = []
    for encoding in encodings:
        tasks.append(extract_from_encoding_async(encoding))
    results = await asyncio.gather(*tasks)
    return results


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def collect_ocr_data(filedir : str, 
                     filename : str, 
                     max_page_num : int = None, 
                     batch_size : int = 10, 
                     st_bar = None) -> List[dict]:
    
    """
    Collects OCR data from a PDF file.

    Args:
        filedir (str): The directory of the PDF file.
        filename (str): The name of the PDF file.
        max_page_num (int): The maximum number of pages to process.
        batch_size (int): The number of pages to process in each batch.
        st_bar (st.progress): A progress bar to display the progress of the OCR process.

    Returns:
        list: A list of dictionaries with the OCR data.
    """
    logger.info(f"Starting OCR collection for {filename}")
    logger.info(f"Parameters - max_page_num: {max_page_num}, batch_size: {batch_size}")

    # collecting images
    encoded_images = collecting_pdf_encoded_images(os.path.join(filedir, filename))

    # selecting pages
    if max_page_num: 
        encoded_images = encoded_images[:max_page_num]
        logger.info(f"Limited processing to {max_page_num} pages")

    print()
    print("Files Successfully Converted to Bytes")
    print("Performing OCR to read Names and Addresses")

    full_data = []
    total_pages = len(encoded_images)

    # getting event loop
    loop = get_or_create_event_loop()
    
    # Process in batches
    logger.info(f"Processing {total_pages} pages in batches of {batch_size}")
    for i in tqdm(range(0, total_pages, batch_size)):
        batch = encoded_images[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} of {(total_pages + batch_size - 1)//batch_size}")

        if st_bar:
            st_bar.progress(i/total_pages, text="Processing pages {} to {} (of {})".format(i+1, i+batch_size, total_pages))        
        
        # Run async batch processing using the event loop
        batch_results = loop.run_until_complete(process_batch_async(batch))   
        
        # Add metadata for each result in the batch
        for page_idx, result in enumerate(batch_results):
            current_page = i + page_idx
            ocr_data = add_metadata(result, current_page, filename)
            full_data.extend(ocr_data)

        logger.info(f"Batch {i//batch_size + 1} complete. Processed {len(batch_results)} pages")
    
    logger.info(f"OCR collection complete. Total entries: {len(full_data)}")
    return full_data


def create_ocr_df(filedir : str, 
                   filename : str, 
                   max_page_num : int = None, 
                   batch_size : int = 10, 
                   st_bar = None) -> pd.DataFrame: 
    
    """
    Creates a dataframe from OCR data.

    Args:
        filedir (str): The directory of the PDF file.
        filename (str): The name of the PDF file.
        max_page_num (int): The maximum number of pages to process.
        batch_size (int): The number of pages to process in each batch.
        st_bar (st.progress): A progress bar to display the progress of the OCR process.

    Returns:
        pd.DataFrame: A dataframe with the OCR data.
    """
    logger.info("Starting OCR DataFrame creation")

    # gathering ocr_data
    ocr_data = collect_ocr_data(filedir, 
                                filename, 
                                max_page_num = max_page_num, 
                                batch_size=batch_size, 
                                st_bar=st_bar)

    # convert dataframe
    ocr_df = pd.DataFrame(data = ocr_data)
    logger.info(f"Created DataFrame with shape: {ocr_df.shape}")

    # renaming columns
    ocr_df.rename(columns = {"Name": "OCR Name", 
                            "Address":"OCR Address", 
                            "Ward": "OCR Ward"}, 
                            inplace=True)

    # converting all caps names to title format
    ocr_df["OCR Name"] = ocr_df["OCR Name"].apply(lambda row: row.title())

    logger.info("OCR DataFrame creation complete")
    return ocr_df    
