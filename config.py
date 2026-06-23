import json
import os

CONFIG_FILE = "config.json"
LOCAL_CONFIG_FILE = "config.local.json"


class _Config:
    def __init__(self, filename):
        self.json = None
        self.load(filename)
        self.target_window_title = self.json["TARGET_WINDOW_TITLE"]
        self.voice_map = self.json['VOICE_MAP'] # Map character names to the desired Kokoro voice codes

        print(f'Config object init: {self.json}')
        print(f"voice map: {self.voice_map}")

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
            json.dump(self.json[key], f, indent=4)
        print(f"Saved {key} to {LOCAL_CONFIG_FILE}")


    # turns key into proper json format and style
    @staticmethod
    def cleanup_key(key):
        return str(key).replace(" ", "_").upper()


config = _Config(CONFIG_FILE)