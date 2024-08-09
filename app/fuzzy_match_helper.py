from rapidfuzz import fuzz, process, utils

def score_function_fuzz(guess_full_name, full_name_list):

    full_name_score_dict = dict()
    for idx in range(len(full_name_list)):

        # getting full name for row
        name_row = str(full_name_list[idx])

        # lowering strings
        name_row = name_row.lower()
        guess_full_name = guess_full_name.lower()

        # compiling scores
        final_score = fuzz.ratio(guess_full_name, name_row)/100
        full_name_score_dict[idx] = final_score

    # sorting dictionary
    sorted_dictionary = dict(sorted(full_name_score_dict.items(), reverse=True, key=lambda item: item[1]))

    # top five key value pairs (indices and scores)
    indices_scores_list = list(sorted_dictionary.items())[:5]

    return indices_scores_list

# fuzzy match redux

def score_fuzzy_match_slim(query_name, names_list):
    # the default scorer produces a Levenshtein distance number, so we can use fuzz.ratio as a scorer to obtain the same format we've been getting for data so far
    # default_process is a process that removes whitespace, lowers all letters, removes any non-alphanumeric characters
    # by limiting to 5 we can save a little bit of space and time and code, since we were looping through all of the items before and only taking the top 5 of the sorted list.
    list_of_match_tuples = process.extract(query=query_name, choices=names_list, scorer=fuzz.ratio, processor=utils.default_process, limit=5)
    # this will produce a list of tuples whose values are as follows:
    # (matched record: the record which the query matched*,
    # score: the result of fuzz.ratio between the query and the matched record,
    # index: when checked against an iterable i.e standard python list, this will be an index, when checked against panda dataframes, it will return a key)
    return list_of_match_tuples
