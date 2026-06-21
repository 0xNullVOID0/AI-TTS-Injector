import json
import os

CONFIG_FILE = "config.json"
LOCAL_CONFIG_FILE = "config.local.json"

def load_config():
    if os.path.exists(LOCAL_CONFIG_FILE):
        print(f"Loading testing config from {LOCAL_CONFIG_FILE}...")
        with open(LOCAL_CONFIG_FILE, 'r') as f:
            j = json.load(f)
            print(j)
            return j
    elif os.path.exists(LOCAL_CONFIG_FILE):
        base_config = None
        print(f"Loading base defaults from {CONFIG_FILE}...")
        with open(CONFIG_FILE, 'r') as f:
            base_config = json.load(f)

        print(f"Creating local {LOCAL_CONFIG_FILE} file automatically...")
        with open(LOCAL_CONFIG_FILE, 'w') as f:
            json.dump(base_config, f, indent=4)

        return base_config