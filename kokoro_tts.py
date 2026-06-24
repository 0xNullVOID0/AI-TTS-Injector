from queue_handler import q
from config_handler import config
from profiler import profiler


KOKORO_URL = config.kokoro_url

# makes sure audio finishes playing before starting next


audio_played_counter = 0
request_counter = 0
succ_request_counter = 0

# TODO turn off screenshots, turn off hard debug mode as in screenshots, turn off logging mode


        data, fs = sf.read(audio_data)

        print("playing audio")
        sd.play(data, fs)
        audio_played_counter += 1
        print(f"audio count: {audio_played_counter}")
        sd.wait()
        print("finished playing audio")

def send_to_kokoro(text, voice="af_heart"):

def fix_ocr_text(text):
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

    # split the text into words and check if they exist in the dictionary
    words = text.split()
    corrected_words = [corrections.get(word.lower(), word) for word in words]
    return " ".join(corrected_words)


def fix_text():
# TODO add both and others here
# TODO dont do it for tts models which can actually properly pronounce such "speech"
    return


@profiler.time_profile
def send(text, voice):
    # prevent empty requests
    if not text or not text.strip():
        print("EMPTY text")
        return

    text = fix_ocr_text(text)
    print("cleaned text: " + text)

# TODO add custom speech speed, increasing/decrasing it dynamically with keybinds or whatever
    payload = {
        "model": "kokoro",
        "input": text,
        "voice": voice,
        "lang_code": "a",
        "cleaner": "american_english",
        "response_format": "wav",
        "stream": False,
        "normalization_options": {
            "normalize": True,
            "url_normalization": True,
            "email_normalization": True,
            "phone_normalization": True
        }
    }

    download_request = {
        "url": KOKORO_URL,
        "payload": payload,
    }

    q.add(download_request, "download")


    # create and start threads if they weren't already
    q.setDownloader()
    q.setAudioPlayer()

