from rapidfuzz import fuzz

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