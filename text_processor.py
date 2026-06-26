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

    # manually add ' when it doesn't get scanned correctly
    corrections = {
        "youre": "you're",
        "dont": "don't",
        "cant": "can't",
        "wont": "won't",
        "hes": "he's",
        "shes": "she's",
        "ive": "i've",
        "IIl": "I'll",
    }

    # load corrections from config instead if set
    if "TEXT_CORRECTIONS" in config.json:
        # TODO for character names strip all , . : and whatever else after it to prevent name pronounce alteration setting conflicts from config
        corrections = config["TEXT_CORRECTIONS"]

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