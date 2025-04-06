# needed libraries
### structured outputs; replacements
import os
import json
from typing import List, Tuple
from tqdm.notebook import tqdm
from rapidfuzz import fuzz
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import logging
from datetime import datetime

# local environment storage
repo_name = 'Ballot-Initiative'
REPODIR = os.getcwd()
load_dotenv(os.path.join(REPODIR, '.env'), override=True)

# load config
with open('config.json', 'r') as f:
    config = json.load(f)

# Set up logging after imports
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Create a logger
logger = logging.getLogger('fuzzy_matching')
logger.setLevel(logging.INFO)

# Create handlers
log_filename = f"fuzzy_matching_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(os.path.join(log_directory, log_filename))
console_handler = logging.StreamHandler()

# Create formatters and add it to handlers
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

###
## MATCHING FUNCTIONS
###

def create_select_voter_records(voter_records : pd.DataFrame) -> pd.DataFrame:
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


def score_fuzzy_match_slim(ocr_result : str, 
                           comparison_list : List[str], 
                           scorer_=fuzz.ratio, 
                           limit_=10) -> List[Tuple[str, int, int]]:
    """
    Scores the fuzzy match between the OCR result and the comparison list.

    Args:
        ocr_result (str): The OCR result to match.
        comparison_list (List[str]): The list of strings to compare against.
        scorer_ (function): The scorer function to use.
        limit_ (int): The number of top matches to return.
        
    Returns:
        List[Tuple[str, int, int]]: The list of top matches with their scores and indices.
    """
    logger.debug(f"Starting fuzzy matching for: {ocr_result[:30]}...")
    
    # Convert to numpy array for faster operations
    comparison_array = np.array(comparison_list)
    
    # Vectorize the scorer function
    vectorized_scorer = np.vectorize(lambda x: scorer_(ocr_result, x))
    
    # Calculate all scores at once
    scores = vectorized_scorer(comparison_array)
    
    # Get top N indices
    top_indices = np.argpartition(scores, -limit_)[-limit_:]
    top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
    
    results = [(comparison_array[i], scores[i], i) for i in top_indices]
    logger.debug(f"Top match score: {results[0][1]}, Match: {results[0][0][:30]}...")
    return results

def get_matched_name_address(ocr_name : str, 
                              ocr_address : str, 
                              select_voter_records : pd.DataFrame) -> List[Tuple[str, str, float, int]]:
    """
    Optimized name and address matching

    Args:
        ocr_name (str): The OCR result for the name.
        ocr_address (str): The OCR result for the address.
        select_voter_records (pd.DataFrame): The DataFrame containing voter records.
        
    Returns:
        List[Tuple[str, str, float, int]]: The list of top matches with their scores and indices.
    """
    logger.debug(f"Matching - Name: {ocr_name[:30]}... Address: {ocr_address[:30]}...")
    
    # Get name matches
    name_matches = score_fuzzy_match_slim(ocr_name, select_voter_records["Full Name"].values)
    logger.debug(f"Best name match score: {name_matches[0][1]}")
    
    # Get address matches
    matched_indices = [x[2] for x in name_matches]
    relevant_addresses = select_voter_records["Full Address"].values[matched_indices]
    address_matches = score_fuzzy_match_slim(ocr_address, relevant_addresses)
    logger.debug(f"Best address match score: {address_matches[0][1]}")
    
    # Calculate harmonic means
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
    results = sorted(results, key=lambda x: x[2], reverse=True)
    
    logger.debug(f"Best combined match score: {results[0][2]}")
    return results

def create_ocr_matched_df(ocr_df : pd.DataFrame, 
                           select_voter_records : pd.DataFrame, 
                           threshold : float = config['BASE_THRESHOLD'], 
                           st_bar = None) -> pd.DataFrame:
    """
    Creates a DataFrame with matched name and address.

    Args:
        ocr_df (pd.DataFrame): The DataFrame containing OCR results.
        select_voter_records (pd.DataFrame): The DataFrame containing voter records.
        threshold (float): The threshold for matching.
        st_bar (st.progress): The progress bar to display.
        
    Returns:
        pd.DataFrame: The DataFrame with matched name and address.
    """
    logger.info(f"Starting matching process for {len(ocr_df)} records with threshold {threshold}")
    
    # Process in batches for better memory management
    batch_size = 1000
    results = []
    
    for batch_start in tqdm(range(0, len(ocr_df), batch_size)):
        batch = ocr_df.iloc[batch_start:batch_start + batch_size]
        logger.info(f"Processing batch {batch_start//batch_size + 1}, rows {batch_start} to {min(batch_start + batch_size, len(ocr_df))}")
        
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
        
        # Log batch statistics
        batch_scores = [match[2] for match in batch_matches]
        logger.info(f"Batch statistics - Avg score: {np.mean(batch_scores):.2f}, "
                   f"Min score: {min(batch_scores):.2f}, "
                   f"Max score: {max(batch_scores):.2f}, "
                   f"Valid matches: {sum(score >= threshold for score in batch_scores)}")

        if st_bar:
            st_bar.progress(batch_start / len(ocr_df), text=f"Processing batch {batch_start} out of {len(ocr_df)//batch_size+1} batches")
    
    logger.info("Creating final DataFrame")
    match_df = pd.DataFrame(results, columns=["Matched Name", "Matched Address", "Match Score"])
    result_df = pd.concat([ocr_df, match_df], axis=1)
    result_df["Valid"] = result_df["Match Score"] >= threshold
    
    # Reorder columns
    column_order = [
        "OCR Name", "OCR Address", "Matched Name", "Matched Address",
        "Date", "Match Score", "Valid", "Page Number", "Row Number", "Filename"
    ]
    
    # Log final statistics
    total_valid = result_df["Valid"].sum()
    logger.info(f"Matching complete - Total records: {len(result_df)}, "
                f"Valid matches: {total_valid} ({total_valid/len(result_df)*100:.1f}%)")
        
    return result_df[column_order]