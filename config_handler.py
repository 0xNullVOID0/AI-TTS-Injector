import json
import os
import threading

CONFIG_FILE = "config.json"
LOCAL_CONFIG_FILE = "config.local.json"

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
        self.json = None
        self.load(filename)

        self.target_window_title = self.get("TARGET_WINDOW_TITLE")
        self.target_window_path = self.get("TARGET_WINDOW_PATH")
        self.target_window = None
        self.active_window = None
        self.default_voice = self.get("DEFAULT_VOICE")
        self.voice_map = self.get('VOICE_MAP') # map character names to the desired Kokoro voice codes
        self.last_text = None
        self.interval = float(self.get("INTERVAL")) # autoplay interval
        self._running = True
        self.next = False
        self.kokoro_url = self.get("KOKORO_URL")
        self.debug = str(self.get("DEBUG")).lower() == "true" # convert json true/false string to actual python bool
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
        if os.path.exists(filename):
            print(f"Loading config from {filename}")
            try:
                with open(filename, 'r') as f:
                    self.json = json.load(f)

                    if filename == CONFIG_FILE:
                        print(f"Creating local {LOCAL_CONFIG_FILE} file automatically...")
                        with open(LOCAL_CONFIG_FILE, 'w') as f:
                            json.dump(self.json, f, indent=4)

                    return True
            except Exception as e:
                print(f"Failed to load config from {filename}, error: {e}")
                pass
        else:
            print(f"CONFIG not found")
            return None


    def get(self, key):
        if key in self.json:
            return self.json[key]
        print(f"ERROR: Could not find {key} in config")
        return None

    def load(self, filename):
        loaded = False
        if os.path.exists(LOCAL_CONFIG_FILE):
            loaded = self.load_json(LOCAL_CONFIG_FILE)
        if not loaded:
            loaded = self.load_json(CONFIG_FILE)
        return loaded

    def update(self, key, value):
        print(f"Updating {key} to {value}")
        self.json[key] = value

        prop = getattr(type(self), key, None)

        # only use setattr() if there's no specific setter for it, otherwise use its specific setters
        if isinstance(prop, property) and prop.fset is not None:
            prop.fset(self, value)
        else:
            setattr(self, key, value)

        with open(LOCAL_CONFIG_FILE, 'w') as f: # TODO make local config file variable dynamic here
            json.dump(self.json, f, indent=4)
        print(f"Saved {key} to {LOCAL_CONFIG_FILE}")

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
        return all(key in self.json for key in keys)

    # turns key into proper json format and style
    @staticmethod
    def cleanup_key(key):
        return str(key).replace(" ", "_").upper()


config = _Config(CONFIG_FILE)