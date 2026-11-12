from typing import Any, Literal

from profiler import profiler
from openai import OpenAI
from config_handler import config

ResponseFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]


# TODO streaming chunks vs downloading full audio, maybe a config option for both? Streaming is more responsive but can be choppy if the network is slow, downloading is slower to start but more reliable and can be cached
# TODO hybrid approach: stream first and when queue done and audio already finished playing, normal download to queue buffer in all other cases
# TODO tag queue order if multiple download threads to maintain proper audio order, or single thread enough?
# TODO saving audio for debugging and general config option for it 
# TODO mp3 options and config from the paid api's + the required playback and processing code
class VoiceEngine():
    def __init__(self) -> None:
        self.model: str = "kokoro"
        self.response_format: ResponseFormat = "pcm"
        self.extra_body: dict[str, Any] | None = None
        self.api: str | None = config.active_tts_api

        # PCM has no header so set format metadata for playback, gets adjusted per Voice API
        self.sample_rate: int | None = 44100
        self.channels: int = 1           # expected PCM channels: 1 = mono, 2 = stereo; mono still gets played through both speakers
        self.sample_width: int = 2       # bytes per sample: 1 = 8-bit, 2 = 16-bit

        self.client: OpenAI = self.set_voice_API_client()

    # Set and configure OpenAI compatible client for selected TTS/Voice API(Local or External) 
    def set_voice_API_client(self) -> OpenAI:
        # TODO: add more voice API clients here, maybe a factory pattern or strategy pattern for different APIs
        self.api = config.active_tts_api
        match self.api:
            # TODO handle non options correctly, TODO make it an enum 
            case "KOKORO": # Local self hosted Kokoro
                self.model = "kokoro"
                self.response_format = "wav"
                self.sample_rate = None
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
                url = f"{config.kokoro_host}:{config.kokoro_port}/v1"
                return OpenAI(base_url=url, api_key="local-not-needed", timeout=10, max_retries=0)
            case "FISH_AUDIO": # Drama-3 (Paid API)
                self.model = config.fish_model
                self.response_format = "pcm"
                self.sample_rate = 44100
                self.channels = 1
                self.sample_width = 2
                self.extra_body = {}
                return OpenAI(base_url=config.openrouter_base, api_key=config.openrouter_api_key, timeout=10, max_retries=1,
                              default_headers={"X-OpenRouter-Title": config.project_name, # "HTTP-Referer": "https://github.com/0xNullVOID0/AI-TTS-Injector", # pyright: ignore[reportArgumentType]
                })
            # TODO add default case where none is set?
            case _:
                raise ValueError(f"Unknown ACTIVE_TTS_API: {self.api}")
            # case "ELEVENLABS":
            #     from elevenlabs import ElevenLabs
            #     return ElevenLabs(api_key=config.get("ELEVENLABS_API_KEY"))


    # returns audio bytes for the given text and voice, raises openai.APIConnectionError or openai.APIStatusError on failure
    @profiler.time_profile
    def synthesize(self, text: str, voice: str) -> bytes:
        request_voice = config.fish_voice if self.api == "FISH_AUDIO" else voice
        print(f"[VoiceEngine] synthesizing text: {text} with voice: {request_voice} using API: {self.api}")
        if self.api == "FISH_AUDIO":
            with self.client.audio.speech.with_streaming_response.create(
                model=self.model,
                voice=request_voice,
                input=text,
                response_format=self.response_format,
                extra_body=self.extra_body,
            ) as response:
                return response.read()
        response = self.client.audio.speech.create(
            model=self.model,
            voice=voice,
            input=text,
            response_format=self.response_format,
            extra_body=self.extra_body,
        )
        return response.content


voice_engine = VoiceEngine()