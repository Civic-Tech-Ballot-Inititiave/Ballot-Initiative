from typing import List
import re
from rapidfuzz import fuzz

def valid_address(address: str) -> bool:
    """
    e.g. '1344 H St NE Washington, DC 20002'
    """
    address = re.sub(re.compile("\.\s*"), "", address)
    address = re.sub(re.compile("\s{2,}"), " ", address) # remove excess spaces
    number_regex_str = "^\d+"
    street_regex_str = "(\d{1,2}[A-z]{0,2} st)|([A-z]+ [A-z]{2,})"
    street_number_re = re.compile(f"{number_regex_str} ({street_regex_str})", re.I)
    if re.search(street_number_re, address) is None:
        return False
    return address.upper().find("DC") >= 0
    """
    state_zip_regex_str = "[A-z]{2}\s+\d{5}"
    state_zip_search = re.search(re.compile(state_zip_regex_str), address)
    if state_zip_search is not None and state_zip_search.group(0).upper() != 'DC':
        return False
    if state_zip_search is None:
        city_state_re = re.compile("[A-z]{2,},? [A-z]{2}")
    return True
    """

def score_function_fuzz(field: str, full_field_list: List[str], is_address: bool = False) -> float:
    """
    abstraction of score_function_fuzz() in https://github.com/Civic-Tech-Ballot-Inititiave/Ballot-Initiative/blob/main/notebooks/trash_files/full_pipeline.ipynb
    """
    if is_address:
        assert valid_address(field)
    full_field_score_dict = dict()
    for idx in range(len(full_field_list)):

        # getting full field for row
        field_row = str(full_field_list[idx])

        # lowering strings    
        field_row = field_row.lower() 
        guess_full_field = guess_full_field.lower()
    
        # compiling scores
        final_score = fuzz.ratio(guess_full_field, field_row)/100
        full_field_score_dict[idx] = final_score

    # sorting dictionary
    sorted_dictionary = dict(sorted(full_field_score_dict.items(), reverse=True, key=lambda item: item[1]))

    # top five key value pairs (indices and scores)
    indices_scores_list = list(sorted_dictionary.items())[:5]

    return indices_scores_list