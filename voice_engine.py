from profiler import profiler
from openai import OpenAI
from config_handler import config


# TODO streaming chunks vs downloading full audio, maybe a config option for both? Streaming is more responsive but can be choppy if the network is slow, downloading is slower to start but more reliable and can be cached
# TODO hybrid approach: stream first and when queue done and audio already finished playing, normal download to queue buffer in all other cases
# TODO tag queue order if multiple download threads to maintain proper audio order, or single thread enough?
# TODO saving audio for debugging and general config option for it 
class VoiceEngine():
    def __init__(self):
        self.model = "kokoro"
        self.response_format = "pcm"
        self.extra_body = None
        self.client = self.set_voice_API_client()

    def set_voice_API_client(self):
        # TODO: add more voice API clients here, maybe a factory pattern or strategy pattern for different APIs
        api = config.active_tts_api

        match api:
            case "KOKORO":
                # Kokoro-FastAPI serves an OpenAI-compatible speech endpoint
                self.model = "kokoro"
                self.response_format = "wav"
                self.extra_body = {
                    "lang_code": "a",
                    "cleaner": "american_english",
                    "stream": False,
                    "normalization_options": {
                        "normalize": True,
                        "url_normalization": True,
                        "email_normalization": True,
                        "phone_normalization": True,
                    },
                }
                return OpenAI(
                    base_url=f"{config.kokoro_host}:{config.kokoro_port}/v1",
                    api_key="local-not-needed", timeout=10, max_retries=0)
            case _:
                raise ValueError(f"Unknown ACTIVE_TTS_API: {api}")
            # case "ELEVENLABS":
            #     from elevenlabs import ElevenLabs
            #     return ElevenLabs(api_key=config.get("ELEVENLABS_API_KEY"))


    # returns audio bytes for the given text and voice, raises openai.APIConnectionError or openai.APIStatusError on failure
    @profiler.time_profile
    def synthesize(self, text, voice):
        print(f"[VoiceEngine] synthesizing text: {text} with voice: {voice} using API: {config.active_tts_api}")
        response = self.client.audio.speech.create(
            model=self.model,
            voice=voice,
            input=text,
            response_format=self.response_format,
            extra_body=self.extra_body,
        )
        return response.content


voice_engine = VoiceEngine()