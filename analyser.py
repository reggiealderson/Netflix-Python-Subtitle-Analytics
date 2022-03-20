import textacy 
import pandas as pd
import spacy
import numpy as np
import math
from itertools import groupby
from datetime import datetime

from os import listdir
from os.path import isfile, join, isdir

from directories import get_directory

FMT = '%H:%M:%S,%f' 

def generate_doc(language, show, chosen_dir, show_files, textacy_lang):
    ''' Creates one big text string with all the dialogue combined from each episode in a show'''

    doc_list = []
    for file1 in show_files:
        fff = open(f"{chosen_dir}/{file1}", "r")
        episodetxt = fff.read() 
        doc_list.append(episodetxt)
        fff.close()

    full_doc = ' '.join(doc_list)
    number_of_episodes = len(show_files)

    doc = textacy.make_spacy_doc(full_doc, lang=textacy_lang)

    return doc, number_of_episodes

def generate_ngrams_starter_set(words_per_ngram, ngrams_per_episode, doc, number_of_episodes):
    ''' Creates a sorted list of ngrams based on count. The list is preset to an appropriate length so as to only include the most pertinent ngrams '''

    # User selects number of tokens per ngram
    phrase_token_num = words_per_ngram

    ngrams = list(textacy.extract.basics.ngrams(doc, phrase_token_num, min_freq=1, filter_stops = False, filter_punct = True))
    ngrams_ca = [str(i).lower() for i in ngrams]
    ngrams_ca_sorted = sorted(ngrams_ca)
    ngrams_ca_sorted_set = sorted(list(set(ngrams_ca_sorted)))

    ngrams_per_ep = ngrams_per_episode
    # generating a fixed length list:
    ngrams_starter_set_multiplier = 2.75 # little bit of magic here. I tinkered with this figure to get it to generate a list with an appropriate length to later loop through
    ideal_ngram_starter_set_len = round(number_of_episodes * (math.log((ngrams_per_ep+1), 2) * ngrams_starter_set_multiplier) * ngrams_starter_set_multiplier)

    ngrams_ca_sorted_counts = [len(list(group)) for key, group in groupby(ngrams_ca_sorted)] # returns the count for each ngram (still sorted in alphabetical order)
    ngrams_ca_sorted_dict = dict(zip(ngrams_ca_sorted_set, ngrams_ca_sorted_counts)) #zips the unique ngrams (alphabetical order) with the ngram counts
    
    # sorts the dictionary by count of ngram:
    ngrams_ca_sorted_dict_desc_vals = dict(sorted(ngrams_ca_sorted_dict.items(), key=lambda item: item[1], reverse=True))

    # narrows the list to only a limited number of ngrams because we want repitition (by narrowing) of learning and memorisation
    ngrams_list = list(ngrams_ca_sorted_dict_desc_vals.keys())
    ideal_ngram_starter_set = ngrams_list[0:ideal_ngram_starter_set_len]

    return ideal_ngram_starter_set, ngrams_ca_sorted_dict_desc_vals

def generate_ngrams_list(language, show, ideal_ngram_starter_set, ngrams_per_ep, chosen_dir_csv, show_files_csv):
    ''' This function iterates through a list of csv files (each representing a single episode/film).
    While doing so it iterates through a list of ngrams. Once an ngram is found in a episode it gets added to the ngrams_used list and removed from the available_ngrams_v2 list.
    This essentially bumps found ngrams to the bottom of the pile, only to be used again if a search through the fresh ngrams list (available_ngrams_v2) is exhausted.
    The goal is to find a specified amount of unique ngrams for each episode. ngrams_found_count keeps track of this amount when iterating through each episode. '''

    ngrams_used = []
    all_subtitles = []
    ngrams_found_counter = []
    ngrams_found_list = []
    ep_name_list = []
    all_start_times = []

    for file2 in show_files_csv:
        episode_path = f"{chosen_dir_csv}/{file2}"
        episode = pd.read_csv(episode_path)
        episode_subtitles = []
        subtitles_found = []
        ngrams_found = []
        ngrams_found_count = 0
        episode_start_times = []
        available_ngrams_v2 = [x for x in ideal_ngram_starter_set if x not in ngrams_used]

        for ngram_x in available_ngrams_v2:
            ngram_subtitles = []
            df_check = episode[episode['Dialogue_lower'].str.contains(ngram_x)]
            df_check = df_check[~df_check.Dialogue.isin(subtitles_found)]

            if len(df_check) == 1:
                ngrams_used.append(ngram_x)
                ngrams_found.append(ngram_x)
                subtitle_found = df_check['Dialogue'].values[0]
                subtitles_found.append(subtitle_found)
                ngram_subtitles.append(subtitle_found)
                ngrams_found_count += 1
                episode_subtitles.append(ngram_subtitles)

                start_time_found = df_check['Start'].values[0]
                start_time_found = datetime.strptime(start_time_found, FMT)
                start_time_found = str(start_time_found.time())[0:8]
                episode_start_times.append(start_time_found)
                
            if len(df_check) > 1:
                ngrams_used.append(ngram_x)
                ngrams_found.append(ngram_x)
                df_check2 = df_check.sample(n=2,replace=False)
                subtitle_found = df_check2['Dialogue'].values[0]
                subtitles_found.append(subtitle_found)
                ngram_subtitles.append(subtitle_found)

                ngrams_found_count += 1
                episode_subtitles.append(ngram_subtitles)

                start_time_found = df_check['Start'].values[0]
                start_time_found = datetime.strptime(start_time_found, FMT)
                start_time_found = str(start_time_found.time())[0:8]
                episode_start_times.append(start_time_found)
                
            if ngrams_found_count == ngrams_per_ep:
                break

        if ngrams_found_count < ngrams_per_ep:   # if we cannot find any original ngrams, we look at ones already found
            for repeat_ngram in ngrams_used:
                ngram_subtitles = []
                df_check = episode[episode['Dialogue_lower'].str.contains(repeat_ngram)]
                df_check = df_check[~df_check.Dialogue.isin(subtitles_found)]

                if len(df_check) == 1:
                    ngrams_found.append(repeat_ngram)
                    subtitle_found = df_check['Dialogue'].values[0]
                    subtitles_found.append(subtitle_found)
                    ngram_subtitles.append(subtitle_found)
                    ngrams_found_count += 1
                    episode_subtitles.append(ngram_subtitles)

                    start_time_found = df_check['Start'].values[0]
                    start_time_found = datetime.strptime(start_time_found, FMT)
                    start_time_found = str(start_time_found.time())[0:8]
                    episode_start_times.append(start_time_found)
                
                if len(df_check) > 1:
                    ngrams_found.append(repeat_ngram)
                    df_check2 = df_check.sample(n=2,replace=False)
                    subtitle_found = df_check2['Dialogue'].values[0]
                    subtitles_found.append(subtitle_found)
                    ngram_subtitles.append(subtitle_found)
                    ngrams_found_count += 1
                    episode_subtitles.append(ngram_subtitles)

                    start_time_found = df_check['Start'].values[0]
                    start_time_found = datetime.strptime(start_time_found, FMT)
                    start_time_found = str(start_time_found.time())[0:8]
                    episode_start_times.append(start_time_found)

                if ngrams_found_count == ngrams_per_ep:
                    break

        all_subtitles.append(episode_subtitles)
        all_start_times.append(episode_start_times)
        ngrams_found_counter.append(ngrams_found_count)
        ngrams_found_list.append(ngrams_found)

        for xyz in range(ngrams_found_count):
            ep_name_list.append(file2)

    episode_names_flat = [(x.replace("_", " ")).replace(".csv", "") for x in ep_name_list]
    ngrams_found_list_flat = [item for sublist in ngrams_found_list for item in sublist]
    all_subtitles_found_list_flat = [item[0] for sublist in all_subtitles for item in sublist]
    all_start_times_found_list_flat = [item for sublist in all_start_times for item in sublist]

    return episode_names_flat, ngrams_found_list, ngrams_found_list_flat, ngrams_used, all_subtitles, all_subtitles_found_list_flat, all_start_times_found_list_flat


def generate_ngram_counts(language, show, ngrams_found_list, ngrams_used, ngrams_ca_sorted_dict_desc_vals, chosen_dir_csv, show_files_csv):

    # Part 1 of this step - Goes through each episode and searches for each ngram, returning the count
    ngram_episode_dicts = {}
    ngrams_used_reference = ngrams_used
    for file2 in show_files_csv:
        episode_path = f"{chosen_dir_csv}/{file2}"
        episode = pd.read_csv(episode_path)
        file2_name = file2.replace(".csv", "")
        file2_name = file2_name.replace("__", " - ")
        file2_name = file2_name.replace("_", " ")
        fil2_dict = {}
        for ngram in ngrams_used:
            csv_check = episode[episode['Dialogue_lower'].str.contains(ngram.lower())]
            ngram_count_in_ep = len(csv_check)
            fil2_dict[ngram] = ngram_count_in_ep
        ngram_episode_dicts[file2_name] = fil2_dict

    # Part 2 of this step - Reorders the above so that the ngram is the focus instead of the episode (for each search)
    ngrams_used_episode_check = {}
    for ngram in ngrams_used:
        episodes_found_for_ngram = []
        for episodexx in list(ngram_episode_dicts.items()):
            if episodexx[1][ngram] > 0:
                ngram_in_ep_counter_str = f"{episodexx[0]} (count: {episodexx[1][ngram]})"
                episodes_found_for_ngram.append(ngram_in_ep_counter_str)
        ngrams_used_episode_check[ngram] = episodes_found_for_ngram

    # Part 3 - Retrieve episode count per ngram
    eps_per_ngrams_master = []
    for ep in ngrams_found_list:
        eps_per_ngrams_episodes = []
        for ngram in ep:
            eps_per_ngram = len(ngrams_used_episode_check[ngram])
            eps_per_ngrams_episodes.append(eps_per_ngram)
        eps_per_ngrams_master.append(eps_per_ngrams_episodes)
    
    eps_per_ngrams_master_flat = [item for sublist in eps_per_ngrams_master for item in sublist]


    # Part 4 - Retrieve total count per ngram
    ngram_counts_master = []
    for ep in ngrams_found_list:
        ngram_counts_episodes = []
        for ngram in ep:
            ngram_count = ngrams_ca_sorted_dict_desc_vals[ngram]
            ngram_counts_episodes.append(ngram_count)
        ngram_counts_master.append(ngram_counts_episodes)

    ngram_counts_master_flat = [item for sublist in ngram_counts_master for item in sublist]

    # Part 5 - Retrieve ngram ranks
    ngrams_count_dict = {}
    for ngram in ngrams_used:
        ngram_count = ngrams_ca_sorted_dict_desc_vals[ngram]
        ngrams_count_dict[ngram] = ngram_count
    ngrams_sorted_by_count = sorted(ngrams_count_dict.items(), reverse=True, key=lambda item: item[1])

    a_ngram_rank, a_ngram_count, a_ngram_previous, a_ngram_result = 0, 0, None, {}
    for key, num in ngrams_sorted_by_count:
        a_ngram_count += 1
        if num != a_ngram_previous:
            a_ngram_rank += a_ngram_count
            a_ngram_previous = num
            a_ngram_count = 0
        a_ngram_result[key] = a_ngram_rank

    ngram_ranks_master = []
    for ep in ngrams_found_list:
        ngram_ranks_episodes = []
        for ngram in ep:
            ngram_rank = a_ngram_result[ngram]
            ngram_ranks_episodes.append(ngram_rank)
        ngram_ranks_master.append(ngram_ranks_episodes)
    
    ngram_ranks_master_flat = [item for sublist in ngram_ranks_master for item in sublist]

    return eps_per_ngrams_master_flat, ngram_counts_master_flat, ngram_ranks_master_flat


def generate_pre_dialogue(language, show, ngrams_found_list, chosen_dir_csv, show_files_csv):
    ''' Extracts the appropriate dialogue that exists prior to an ngram occuring, based on timestamps'''

    # FMT = '%H:%M:%S,%f'
    master_full_dialogue_context_pre = []
    for file2, ngram_collection in zip(show_files_csv, ngrams_found_list):
        episode_dialogue_context_pre = []
        episode_path = f"{chosen_dir_csv}/{file2}"
        episode = pd.read_csv(episode_path)
        for ng in ngram_collection:
            ngram_context_pre = []
            ngram_found_row = episode[episode['Dialogue_lower'].str.contains(ng.lower())]
            ngram_start = ngram_found_row['Start'].values[0]
            ngram_index = ngram_found_row['Line_Index'].values[0]
            for x in range(1,4):
                ngram_index_pre = ngram_index - x
                ngram_index_pre_check = episode.loc[episode['Line_Index'] == ngram_index_pre]
                if len(ngram_index_pre_check) > 0:
                    ngram_index_pre_start = ngram_index_pre_check['Start'].values[0]
                    tdelta = datetime.strptime(ngram_start, FMT) - datetime.strptime(ngram_index_pre_start, FMT)
                    tdelta_sec = tdelta.total_seconds()
                    if tdelta_sec < 12:
                        ngram_index_pre_dialogue = ngram_index_pre_check['Dialogue'].values[0]
                        ngram_context_pre.append(ngram_index_pre_dialogue)
                    else: break
                else: break
            ngram_context_pre_rev = list(reversed(ngram_context_pre))
            episode_dialogue_context_pre.append(ngram_context_pre_rev)
        master_full_dialogue_context_pre.append(episode_dialogue_context_pre)

    return master_full_dialogue_context_pre


def generate_post_dialogue(language, show, ngrams_found_list, chosen_dir_csv, show_files_csv):
    ''' Extracts the appropriate dialogue that exists after an ngram occurs, based on timestamps'''

    # FMT = '%H:%M:%S,%f'
    master_full_dialogue_context_post = []
    for file2, ngram_collection in zip(show_files_csv, ngrams_found_list):
        episode_dialogue_context_post = []
        episode_path = f"{chosen_dir_csv}/{file2}"
        episode = pd.read_csv(episode_path)
        for ng in ngram_collection:
            ngram_context_post = []
            ngram_found_row = episode[episode['Dialogue_lower'].str.contains(ng.lower())]
            ngram_start = ngram_found_row['Start'].values[0]
            ngram_index = ngram_found_row['Line_Index'].values[0]
            for x in range(1,4):
                ngram_index_post = ngram_index + x
                ngram_index_post_check = episode.loc[episode['Line_Index'] == ngram_index_post]
                if len(ngram_index_post_check) > 0:
                    ngram_index_post_start = ngram_index_post_check['Start'].values[0]
                    tdelta = datetime.strptime(ngram_index_post_start, FMT) - datetime.strptime(ngram_start, FMT)
                    tdelta_sec = tdelta.total_seconds()
                    if tdelta_sec < 12:
                        ngram_index_post_dialogue = ngram_index_post_check['Dialogue'].values[0]
                        ngram_context_post.append(ngram_index_post_dialogue)
                    else: break
                else: break
            episode_dialogue_context_post.append(ngram_context_post)
        master_full_dialogue_context_post.append(episode_dialogue_context_post)

    return master_full_dialogue_context_post


def generate_full_dialogue(language, show, master_full_dialogue_context_pre, all_subtitles, master_full_dialogue_context_post):
    ''' Glues the appropriate dialogue including and surrounding the ngram together '''

    curated_all_dialogues = []
    for pre, actual, post in zip(master_full_dialogue_context_pre,all_subtitles,master_full_dialogue_context_post):
        curated_episode_dialogues = []
        for pre_a, actual_a, post_a in zip(pre, actual, post):
            joined_pre = ' '.join(pre_a)
            joined_post = ' '.join(post_a)
            full_dialogue = f"...{joined_pre} {actual_a[0]} {joined_post}..."
            curated_episode_dialogues.append(full_dialogue)
        curated_all_dialogues.append(curated_episode_dialogues)

    curated_all_dialogues_flat = [item for sublist in curated_all_dialogues for item in sublist]

    return curated_all_dialogues_flat



def analyser(language, show, words_per_ngram, ngrams_per_episode):
    ''' Main function that brings all the other functions together and generates a final dataframe '''

    ## The following needs to become dynamic when there are multiple languages available to select from
    if language == 'German':
        nlp = spacy.load("de_core_news_sm")
        de = textacy.load_spacy_lang("de_core_news_sm", disable=("parser",))
        textacy_lang = de

    chosen_dir = get_directory(language, show, filetype="Docs")
    show_files = [fl for fl in listdir(chosen_dir) if isfile(join(chosen_dir, fl))]
    chosen_dir_csv = get_directory(language, show, filetype="CSV")
    show_files_csv = [fl for fl in listdir(chosen_dir_csv) if isfile(join(chosen_dir_csv, fl))]

    doc, number_of_episodes = generate_doc(language, show, chosen_dir, show_files, textacy_lang)

    ideal_ngram_starter_set, ngrams_ca_sorted_dict_desc_vals = generate_ngrams_starter_set(words_per_ngram, ngrams_per_episode, doc, number_of_episodes)

    episode_names_flat, ngrams_found_list, ngrams_found_list_flat, ngrams_used, all_subtitles, all_subtitles_found_list_flat, all_start_times_found_list_flat = generate_ngrams_list(language, show, ideal_ngram_starter_set, ngrams_per_episode, chosen_dir_csv, show_files_csv)

    eps_per_ngrams_master_flat, ngram_counts_master_flat, ngram_ranks_master_flat = generate_ngram_counts(language, show, ngrams_found_list, ngrams_used, ngrams_ca_sorted_dict_desc_vals, chosen_dir_csv, show_files_csv)

    master_full_dialogue_context_pre = generate_pre_dialogue(language, show, ngrams_found_list, chosen_dir_csv, show_files_csv)
    master_full_dialogue_context_post = generate_post_dialogue(language, show, ngrams_found_list, chosen_dir_csv, show_files_csv)
    curated_all_dialogues_flat = generate_full_dialogue(language, show, master_full_dialogue_context_pre, all_subtitles, master_full_dialogue_context_post)

    final_dataframe = pd.DataFrame(
        {'Episode': episode_names_flat,
        'Phrase': ngrams_found_list_flat,
        'Featured dialogue': curated_all_dialogues_flat,
        'Phrase rank': ngram_ranks_master_flat,
        '# of occurences': ngram_counts_master_flat,
        '# of episodes': eps_per_ngrams_master_flat,
        'Subtitle shortened': all_subtitles_found_list_flat,
        'Subtitle start time': all_start_times_found_list_flat
        })

    return final_dataframe

