from typing import List
from rapidfuzz import fuzz
from address_util import valid_address

def score_function_fuzz(ocr_name: str, full_name_list: List[str], is_address: bool = False) -> List[int, float]:

    """
    Outputs the voter record indices of the names that are 
    closest to `ocr_name`.
    """
    if is_address:
        assert valid_address(is_address)

    # empty dictionary of scores 
    full_name_score_dict = dict()

    for idx in range(len(full_name_list)):

        # getting full name for row; ensuring string
        name_row = str(full_name_list[idx])

        # converting string to lower case to simplify matching  
        name_row = name_row.lower()
        ocr_name = ocr_name.lower()
    
        # compiling scores; writing as between 0 and 1
        full_name_score_dict[idx] = fuzz.ratio(ocr_name, name_row)/100

    # sorting dictionary
    sorted_dictionary = dict(sorted(full_name_score_dict.items(), reverse=True, key=lambda item: item[1]))

    # top five key value pairs (indices and scores)
    indices_scores_list = list(sorted_dictionary.items())[:5]

    return indices_scores_list  