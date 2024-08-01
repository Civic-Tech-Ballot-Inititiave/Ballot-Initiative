from rapidfuzz import fuzz, process, utils

def score_fuzzy_match_slim(query_name, names_list):
    # the default scorer produces a Levenshtein distance number, so we can use fuzz.ratio as a scorer to obtain the same format we've been getting for data so far
    # there is no processor used by default but it does mostly what we've been using in the project so far, removes whitespace, lowers all letters, removes any non-alphanumeric characters
    # by limiting to 5 we can save a little bit of space and time and code, since we were looping through all of the items before and only taking the top 5 of the sorted list.
    list_of_match_tuples = process.extract(query=query_name, choices=names_list, scorer=fuzz.ratio, processor=utils.default_process, limit=5)
    # this will produce a list of tuples whose values are as follows:
    # (matched record: the record which the query matched*,
    # score: the result of fuzz.ratio between the query and the matched record,
    # index: when checked against an iterable i.e standard python list, this will be an index, when checked against panda dataframes, it will return a key)
    # my recommendation is to keep this format and refactor the functions which accept this list as an argument to simply access the correct index of the new tuple format.
    # however, it is no problem to reformat them to the original format with a simple loop:
    # indices_scores_list = list((match[2], match[1]) for match in list_of_match_tuples)
    return list_of_match_tuples

test_name = "James Hatch"
test_name_list = ["James Hatch", "James Hatcher", "Jamees Heath", "James Patch", "James Bach"]

results = score_fuzzy_match_slim(test_name, test_name_list)

for result in results:
    print(result)
