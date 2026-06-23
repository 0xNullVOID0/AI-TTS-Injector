import io
import threading

import requests
import sounddevice as sd
import soundfile as sf

# Local Kokoro endpoint
KOKORO_URL = "http://localhost:8880/v1/audio/speech"

# makes sure audio finishes playing before starting next
audio_lock = threading.Lock()
audio_played_counter = 0
request_counter = 0
succ_request_counter = 0

# TODO make stuff into classes and objects
config = None
def set_config(c):
    global config
    config = c

def play_audio(response):
    global audio_played_counter
    with audio_lock:
        audio_data = io.BytesIO(response.content)

        data, fs = sf.read(audio_data)

        print("playing audio")
        sd.play(data, fs)
        audio_played_counter += 1
        print(f"audio count: {audio_played_counter}")
        sd.wait()
        print("finished playing audio")

def send_to_kokoro(text, voice="af_heart"):
    global request_counter, succ_request_counter
    payload = {
        "model": "kokoro",
        "input": text,
        "voice": voice,
        "response_format": "wav",
        "stream": False,
        "normalization_options": {
            "normalize": True,
            "url_normalization": True,
            "email_normalization": True,
            "phone_normalization": True
        }
    }

    # prevent empty requests
    if not text or not text.strip():
        print("empty text")
        return

    try:
        response = requests.post(KOKORO_URL, json=payload, timeout=10)
        print(f"response: {response}")
        print(f"response status: {response.status_code}")

        request_counter += 1
        print(f"request counter: {request_counter}")

        if response.status_code == 200:
            succ_request_counter += 1
            print(f"successfull request counter: {succ_request_counter}")
            print(f"playing audio with voice: {voice}")
            # thread for audio so it doesn't stop whole program
            audio_worker = threading.Thread(target=play_audio, args=(response,), daemon=True)
            audio_worker.start()
        else:
            print(f"Kokoro server error: {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")


