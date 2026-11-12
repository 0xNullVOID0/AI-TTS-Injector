import threading

from config_store import CONFIG_FILE, LOCAL_CONFIG_FILE, ConfigStore

# TODO if statements for relevant places in code
# TODO save and keep or delete screenshots and audio depending on level
# TODO performance tiers, queue sizes, saving or skipping debug screenshots, audio whatever
# TODO turn off screenshots, turn off hard debug mode as in screenshots, turn off logging mode
debug_levels = {
    1: "ALL",
    2: "INFO",
    3: "WARNING",
    4: "ERROR",
    5: "CRITICAL",
}

_BOOL_ATTRS = {"debug", "testing", "media_cleanup"}
_FLOAT_ATTRS = {"interval", "autoplay_interval", "speech_speed", "media_max_age_hours", "media_max_folder_mb"}
_INT_ATTRS = {"kokoro_port", "media_max_files"}

def as_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _coerce_live(attr, value):
    if attr in _BOOL_ATTRS:
        return as_bool(value)
    if attr in _FLOAT_ATTRS:
        return float(value)
    if attr in _INT_ATTRS:
        return int(value)
    return value


# TODO make into actual proper singleton
# TODO variable event hooks

# TODO for everything that can just be stored and retrieved easily from json just use config.get() for them instead of object properties?

class _Config:
    _instance = None
    _initialized = False
    _lock = threading.Lock()


    def __new__(cls, *args, **kwargs):
        # ensure class can only be initialized once as a proper Singleton
        if not cls._instance:
            with cls._lock:
                # double check to prevent race condition instancing
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, filename=CONFIG_FILE):
        # ensure init can only be run once
        if _Config._initialized:
            return

        self.filename = filename
        self.store = ConfigStore(filename)

        self.project_name = self.get("PROJECT_NAME")
        self.window_captures_folder = self.get("WINDOW_CAPTURES_FOLDER") or "window_captures"
        self.audio_folder = self.get("AUDIO_FOLDER")
        self.target_window_title = self.get("TARGET_WINDOW_TITLE")
        self.target_window_path = self.get("TARGET_WINDOW_PATH")
        self.target_window = None
        self.active_window = None
        self.active_tts_api = self.get("ACTIVE_TTS_API") or "KOKORO"
        stored = self.store.json or {}
        self.default_voice = stored.get("DEFAULT_VOICE") or stored.get("DEFAULT_KOKORO_VOICE") or "af_bella"
        self.voice_map = self.get('VOICE_MAP') # map character names to the desired Kokoro voice codes
        self.last_text = None
        self.interval = float(self.get("INTERVAL")) # autoplay interval
        self._running = True
        self.next = False
        self.debug = as_bool(self.get("DEBUG"))
        self.ocr_counter = 0 # TOOD move
        self.characters = self.get("CHARACTERS")
        self.lookup_cache = self.get("LOOKUP_CACHE")
        self.snipping = False
        self.blacklist = self.get("BLACKLIST")
        self.target_list = self.get("TARGET_LIST")
        self.duplicate = False
        self._autoplay = False
        self.autoplay_interval = float(self.get("AUTOPLAY_INTERVAL"))
        self.text_corrections = self.get("TEXT_CORRECTIONS")
        self.listeners = []
        self.on_start = None
        self.on_stop = None
        self.ocr = None
        self.testing = as_bool(self.get("TESTING"))
        self.tested = False
        self.testing_lock = threading.Lock()
        # Voice APIs
        self.openrouter_base = "https://openrouter.ai/api/v1"
        self.openrouter_api_key = self.get("OPENROUTER_API_KEY") or ""

        self.fish_model = self.get("FISH_MODEL") or "fish-audio/drama-3"
        self.fish_voice = self.get("FISH_VOICE") or "f3a2b90078d54a65af4b95f63bc7798e"
        self.fish_format = "pcm"

        self.kokoro_host = self.get("KOKORO_HOST") or "http://localhost"
        self.kokoro_port = self.get("KOKORO_PORT") or "8880"

        # finalize and lock initialization
        _Config._initialized = True

        # TODO move name and text selector to here

        print(f'Config object init: {self.json}')
        print(f"voice map: {self.voice_map}")
        print(f'default_voice: {self.default_voice}')

    @property
    def running(self) -> bool:
        return self._running

    @running.setter
    def running(self, value: bool):
        print("Running: " + str(value))
        if self._running != value:
            self._running = value

            if self._running and self.on_start:
                self.on_start()
            elif not self._running and self.on_stop:
                self.on_stop()


    @property
    def autoplay(self) -> bool:
        return self._autoplay

    @autoplay.setter
    def autoplay(self, value: bool):
        print("Autoplay: " + str(value))
        self._autoplay = value


    def load_json(self, filename):
        return self.store.load_json(filename)


    def get(self, key):
        return self.store.get(key)

    def load(self, filename):
        return self.store.load(filename, prefer_local=filename == CONFIG_FILE)

    def update(self, key, value):
        self.update_many({key: value})

    def update_many(self, values):
            prepared = {}
            for key, value in values.items():
                value = _coerce_live(key, value)
                prepared[key] = value

            self.store.update_many(prepared, LOCAL_CONFIG_FILE)

            for key, value in prepared.items():
                prop = getattr(type(self), key, None)
                if isinstance(prop, property) and prop.fset is not None:
                    prop.fset(self, value)
                else:
                    setattr(self, key, value)

    @staticmethod
    def get_window_key(window_title, affix=""):
        return f"{window_title}{affix}"

    def get_target_window_selection_keys(self):
        return self.get_window_selection_keys(self.target_window_title)

    def get_window_selection_keys(self, window_title):
        window_key = self.cleanup_key(f"{window_title}")

        name_key = self.get_window_key(window_key, "_NAME_COORDS")
        text_key = self.get_window_key(window_key, "_TEXT_COORDS")
        print(f"name_key: {name_key}")
        print(f"text_key: {text_key}")

        return name_key, text_key

    # checks saved screen selections for window to skip constant manual repeat selections
    def get_window_selections(self, window_title):
        name_key, text_key = self.get_window_selection_keys(window_title)

        if self.has_keys(name_key, text_key):
            name_selector = self.get(name_key)
            text_selector = self.get(text_key)

            print(f"Loading {name_key} from {LOCAL_CONFIG_FILE}. {name_selector}")
            print(f"Loading {text_key} from {LOCAL_CONFIG_FILE}. {text_key}")
            return name_selector, text_selector
        else:
            print(f"ERROR: Could not find {name_key} and {text_key}")
            return None, None

    def get_target_window_selections(self):
        return self.get_window_selections(self.target_window_title)

    def has_keys(self, *keys):
        return self.store.has_keys(*keys)

    @property
    def json(self):
        return self.store.json

    # turns key into proper json format and style
    @staticmethod
    def cleanup_key(key):
        return str(key).replace(" ", "_").upper()


config = _Config(CONFIG_FILE)
