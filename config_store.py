import json
import os
import threading

CONFIG_FILE = "config.json"
LOCAL_CONFIG_FILE = "config.local.json"
_WRITE_LOCK = threading.RLock()


class ConfigStore:
    def __init__(self, filename=CONFIG_FILE):
        self.filename = filename
        self.json = {}
        self.load(filename, prefer_local=filename == CONFIG_FILE)

    def load_json(self, filename):
        if not os.path.exists(filename):
            print("CONFIG not found")
            return None

        print(f"Loading config from {filename}")
        try:
            with open(filename, "r") as file:
                self.json = json.load(file)

            if filename == CONFIG_FILE:
                print(f"Creating local {LOCAL_CONFIG_FILE} file automatically...")
                with open(LOCAL_CONFIG_FILE, "w") as file:
                    json.dump(self.json, file, indent=4)
            return True
        except Exception as error:
            print(f"Failed to load config from {filename}, error: {error}")
            return False

    def load(self, filename, prefer_local=True):
        if prefer_local and os.path.exists(LOCAL_CONFIG_FILE) and self.load_json(LOCAL_CONFIG_FILE):
            return True
        return self.load_json(filename)

    def get(self, key):
        if key in self.json:
            return self.json[key]
        print(f"ERROR: Could not find {key} in config")
        return None

    def has_keys(self, *keys):
        return all(key in self.json for key in keys)

    def update(self, key, value, filename=None):
        self.update_many({key: value}, filename)

    def update_many(self, values, filename=None):
        filename = filename or self.filename
        with _WRITE_LOCK:
            self.json.update(values)
            temp_filename = f"{filename}.tmp"
            with open(temp_filename, "w") as file:
                json.dump(self.json, file, indent=4)
            os.replace(temp_filename, filename)
        print(f"Saved {', '.join(values)} to {filename}")
