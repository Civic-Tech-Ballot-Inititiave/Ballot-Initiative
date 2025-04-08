import pandas as pd
import numpy as np
import time

# Scanned file should have a combination of Full Name, (full) Street Address

"""
--- Rapidfuzz approach ---
see https://medium.com/@bewin4u/fuzzy-matching-for-million-row-address-dataset-with-rapidfuzz-and-splink-b704eaf1fda9
1. use something other than Pandas to combine columns
2. rapidfuzz.utils.default_process() on both combined columns
3. determine appropriate match score (e.g. scorer = rapidfuzz.fuzz.partial_ratio)
"""

CRITICAL_COLS = ['Last_Name', 'First_Name', 'Street_Number',
       'Street_Name', 'Street_Type', 'Street_Dir_Suffix', 'Unit_Type',
       'Apartment_Number', 'WARD']

def get_matches(scanned_filename: str, registry_filename: str) -> pd.DataFrame:
    FULL_NAME = 'full_name'
    FULL_ADDRESS_NO_APT = 'full_address_no_apt'
    voter_registry = pd.read_csv(registry_filename, usecols=CRITICAL_COLS[:6], keep_default_na=False) #, nrows=100)
    ocr_df = pd.read_csv(scanned_filename) #, usecols=CRITICAL_COLS[:5])
    ocr_df = ocr_df.rename(columns={'Street_Cardinal_Direction': 'Street_Dir_Suffix'})
    
    def combine_names(row):
        return f"{row['First_Name']} {row['Last_Name']}"
    
    def combine_address(row, type_included: bool) -> str:
        corrected_num = "" if np.isnan(row['Street_Number']) else int(row['Street_Number'])
        house_num_list = [f"{corrected_num} {row['Street_Name']}"]
        if not(type_included):
            house_num_list.append(row['Street_Type'])
        house_num = " ".join(house_num_list)
        corrected_suffix = "" if str(row['Street_Dir_Suffix']) == 'nan' else row['Street_Dir_Suffix']
        return f"{house_num} {corrected_suffix}"
        # return re.sub("[^a-zA-Z0-9\s]", "", f"{house_num} {corrected_suffix}".strip())
    
    start = time.time()
    ocr_df[FULL_NAME] = ocr_df.apply(combine_names, axis=1)
    end = time.time()
    print(f"OCR name combination took {end - start} s.")
    
    ocr_df[FULL_NAME] = ocr_df[FULL_NAME].map(lambda s: s.upper()).astype(str)
    
    start = time.time()
    ocr_df[FULL_ADDRESS_NO_APT] = ocr_df.apply(combine_address, axis=1, type_included=True)
    end = time.time()
    print(f"OCR address combination took {end - start} s.")
    
    ocr_df[FULL_ADDRESS_NO_APT] = ocr_df[FULL_ADDRESS_NO_APT].map(lambda s: s.upper()).astype(str)
    
    start = time.time()
    voter_registry[FULL_NAME] = voter_registry.apply(combine_names, axis=1) # voter_registry.apply(lambda row: f"{row.First_Name} {row.Last_Name}".upper(), axis = 1)
    end = time.time()
    print(f"registry name combination took {end - start} s.")
    
    voter_registry[FULL_NAME] = voter_registry[FULL_NAME].astype(str)
    
    start = time.time()
    voter_registry[FULL_ADDRESS_NO_APT] = voter_registry.apply(combine_address, axis=1, type_included=False)
    end = time.time()
    print(f"registry address combination took {end - start} s.")
    
    voter_registry[FULL_ADDRESS_NO_APT] = voter_registry[FULL_ADDRESS_NO_APT].map(lambda s: s.upper()).astype(str)
    
    ocr_df.set_index(FULL_NAME)
    voter_registry.set_index(FULL_NAME)
    
    df_fullname_match = ocr_df.merge(voter_registry, on=FULL_NAME, how='inner')
    df_fullname_match[FULL_NAME].value_counts()
    
    name_counts = df_fullname_match[FULL_NAME].value_counts()
    no_dups = set(name_counts[name_counts == 1].keys())
    df_no_dups = df_fullname_match[df_fullname_match[FULL_NAME].isin(no_dups)]
    
    dups = set(name_counts[name_counts > 1].keys())
    ocr_dups = ocr_df[ocr_df[FULL_NAME].isin(dups)]
    df_dups = ocr_dups.merge(voter_registry, on=[FULL_NAME, FULL_ADDRESS_NO_APT], how='inner')
    
    deduped = []
    return df_fullname_match
#       non_matches = df_fullname_match[df_fullname_match['Last_Name_x'].isna()]

print(get_matches("../Aggregated Data/output.csv",
                  "./voter_registries/raw_feb_23_city_wide.csv"))