import json
import os

CONFIG_FILE = "config.json"
LOCAL_CONFIG_FILE = "config.local.json"

# TODO change self.json[key] to use key function

class _Config:
    def __init__(self, filename):
        self.filename = filename
        self.json = None
        self.load(filename)
        self.target_window_title = self.json["TARGET_WINDOW_TITLE"]
        self.target_window_path = None
        self.default_voice = self.json["DEFAULT_VOICE"]
        self.voice_map = self.json['VOICE_MAP'] # Map character names to the desired Kokoro voice codes
        self.last_text = None
        self.interval = self.get("INTERVAL") # autoplay interval

        print(f'Config object init: {self.json}')
        print(f"voice map: {self.voice_map}")
        print(f'default_voice: {self.default_voice}')

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
        with open(LOCAL_CONFIG_FILE, 'w') as f: # TODO make local config file variable dynamic here
            json.dump(self.json, f, indent=4)
        print(f"Saved {key} to {LOCAL_CONFIG_FILE}")

    @staticmethod
    def get_window_key(window_title, affix=""):
        return f"{window_title}{affix}"

    def get_window_selection_keys(self, window_title):
        window_key = self.cleanup_key(f"{window_title}")

        name_key = self.get_window_key(window_key, "_NAME_COORDS")
        text_key = self.get_window_key(window_key, "_TEXT_COORDS")
        print(f"name_key: {name_key}")
        print(f"text_key: {text_key}")

        return name_key, text_key

    # checks saved screen selections for window to skip constant manual repeat selections
    def get_window_selections(self, window_title):
        name_key = self.cleanup_key(f"{window_title}_NAME_COORDS")
        text_key = self.cleanup_key(f"{window_title}_TEXT_COORDS")

        if self.has_keys(name_key, text_key):
            name_selector = self.json[name_key]
            text_selector = self.json[name_key]

            print(f"Loading {name_key} from {LOCAL_CONFIG_FILE}. {name_selector}")
            print(f"Loading {text_key} from {LOCAL_CONFIG_FILE}. {name_selector}")
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
# config.get_window_selection_keys(config.target_window_title)