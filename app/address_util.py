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