import difflib
import re
import string

import enchant

from config_handler import config
from profiler import profiler

lookup_cache = config.lookup_cache



@profiler.time_profile
def clean_text(text):
    # replace curly/smart apostrophes with standard ones
    text = text.replace("’", "'").replace("‘", "'")

    # remove all symbols except [.,!?-] # TODO add : ?
    text = re.sub(r'[^\w\s.,!?-]', '', text)

    return text.strip()


@profiler.time_profile
def fix_ocr(text):
    # ocr often mistakes . for : and , for ; messing up speed of talking and pauses
    text = text.replace(":", ".").replace(";", ",").replace("_", "...")

    # manually add ' and other adjustments when it doesn't get scanned correctly
    corrections = {
        "youre": "you're",
        "dont": "don't",
        "cant": "can't",
        "wont": "won't",
        "hes": "he's",
        "shes": "she's",
        "ive": "i've",
        "ill": "I'll",
        "II": "I'll",
        "mel": "me!", # e and ! conflicts
        "upl": "up!",
        "rulesl": "rules!",
        "we'l": "we'll",
        "cantl": "can't",
        "showyou": "show you",
    } # TODO stop checking for skip or stop/play keybinds if window not focused or just if in blacklisted program


    # TODO lookup cache as first step for everything? or only after this one or something
    # TODO words with weird l's add end, replace with ! through dict check? from the ones outside this corrections list and then added to lookup cache?
    # TODO add check for I being combined with words like Iunderstand, if starts with I and isnt i'll, i'd or other correct uses for it then add space between that and word, split it

    # load corrections from config instead if set
    if config.text_corrections:
        # TODO for character names strip all , . : and whatever else after it to prevent name pronounce alteration setting conflicts from config
        corrections = config.text_corrections

    # print("text corrections")
    # print(corrections)

    # split the text into words and check if they exist in the dictionary and replaces them
    words = text.split()
    corrected_words = [corrections.get(word.lower(), word) for word in words]
    return " ".join(corrected_words)


@profiler.time_profile
def process_ocr(text):
    # TODO combine all text processing and only perform appropiate text for tts models which require it, dont do it for tts models which can actually properly pronounce such "speech"
    text = fix_ocr(text)
    print(f"cleaned text: {text}")

    return text