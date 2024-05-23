# -*- coding: utf-8 -*-
"""
Created on Wed Apr 17 19:36:34 2024

@author: kevin.shu
"""
from rapidfuzz import fuzz, utils
print(fuzz.ratio('this is a test', 'this is a test!'))
print(f"full vs. abbreviation: {fuzz.ratio('Georgia Avenue', 'Georgia Ave.')}")
print(f"full vs. abbreviation: {fuzz.ratio('4828 Georgia Avenue', '4828 Georgia Ave.')}")
# utils.default