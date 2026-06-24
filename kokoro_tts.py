from queue_handler import q
from config_handler import config
from profiler import profiler


KOKORO_URL = config.kokoro_url


@profiler.time_profile
def send(text, voice):
    # prevent empty requests
    if not text or not text.strip():
        print("EMPTY text")
        return


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

