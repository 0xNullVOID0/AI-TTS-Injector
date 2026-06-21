import io
import threading

import requests
import sounddevice as sd
import soundfile as sf

# Local Kokoro endpoint
KOKORO_URL = "http://localhost:8880/v1/audio/speech"

# makes sure audio finishes playing before starting next
audio_lock = threading.Lock()

def play_audio(response):
    with audio_lock:
        audio_data = io.BytesIO(response.content)

        data, fs = sf.read(audio_data)

        print("playing audio")
        sd.play(data, fs)
        sd.wait()
        print("finished playing audio")

def send_to_kokoro(text, voice="af_heart"):
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

        if response.status_code == 200:
            print(f"playing audio with voice: {voice}")
            # thread for audio so it doesn't stop whole program
            audio_worker = threading.Thread(target=play_audio, args=(response,), daemon=True)
            audio_worker.start()
        else:
            print(f"Kokoro server error: {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")


