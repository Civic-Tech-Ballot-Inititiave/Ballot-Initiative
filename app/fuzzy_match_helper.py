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
import numpy as np
import io
import json
from concurrent.futures import ThreadPoolExecutor
import streamlit as st

# local environment storage
repo_name = 'Ballot-Initiative'
REPODIR = os.getcwd().split(repo_name)[0] + repo_name
load_dotenv(os.path.join(REPODIR, '.env'), override=True)

# load config
with open('config.json', 'r') as f:
    config = json.load(f)

# open ai api key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HELICONE_PERSONAL_API_KEY = os.getenv("HELICONE_PERSONAL_API_KEY")

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
    voter_records[name_components] = voter_records[name_components].fillna('')
    voter_records["Full Name"] = voter_records[name_components].astype(str).agg(" ".join, axis=1)

    # Create full address by combining address components
    address_components = ["Street_Number", "Street_Name", "Street_Type", "Street_Dir_Suffix"]
    voter_records[address_components] = voter_records[address_components].fillna('')
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

def create_ocr_matched_df(ocr_df, select_voter_records, threshold=config['BASE_THRESHOLD'], st_bar=None):
    """Optimized DataFrame matching"""
    # Pre-compute numpy arrays
    names = select_voter_records["Full Name"].values
    addresses = select_voter_records["Full Address"].values
    
    # Process in batches for better memory management
    batch_size = 1000
    results = []

    print(f"Processing {len(ocr_df)} rows in batches of {batch_size}")
    
    for batch_start in tqdm(range(0, len(ocr_df), batch_size)):
        batch = ocr_df.iloc[batch_start:batch_start + batch_size]
        
        # Process batch in parallel
        with ThreadPoolExecutor() as executor:
            batch_results = list(executor.map(
                lambda row: get_matched_name_address(
                    row["OCR Name"],
                    row["OCR Address"],
                    select_voter_records
                ),
                [row for _, row in batch.iterrows()]
            ))
        
        # Extract best matches
        batch_matches = [(res[0][0], res[0][1], res[0][2]) for res in batch_results]
        results.extend(batch_matches)

        if st_bar:
            st_bar.progress(batch_start / len(ocr_df), text=f"Processing batch {batch_start} out of {len(ocr_df)//batch_size+1} batches")
    
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