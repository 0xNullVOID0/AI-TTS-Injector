import io
import requests
import sounddevice as sd
import soundfile as sf

# Local Kokoro endpoint
KOKORO_URL = "http://localhost:8880/v1/audio/speech"

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

    try:
        response = requests.post(KOKORO_URL, json=payload, timeout=10)
        print(f"response: {response}")
        print(f"response status: {response.status_code}")

        if response.status_code == 200:
            # TODO make play audio its own function
            audio_data = io.BytesIO(response.content)

            data, fs = sf.read(audio_data)

            print("playing audio")
            sd.play(data, fs)
            sd.wait()
            print("finished playing audio")
        else:
            print(f"Kokoro server error: {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")


