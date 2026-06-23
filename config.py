import json
import os

CONFIG_FILE = "config.json"
LOCAL_CONFIG_FILE = "config.local.json"
data = None

# TODO turn into class? easy global target_window_title and other settings available?

def load_json(config=LOCAL_CONFIG_FILE):
    global data
    if os.path.exists(config):
        print(f"Loading config from {config}")
        try:
            with open(config, 'r') as f:
                data = json.load(f)
                print(data)

                if config == CONFIG_FILE:
                    print(f"Creating local {LOCAL_CONFIG_FILE} file automatically...")
                    with open(LOCAL_CONFIG_FILE, 'w') as f:
                        json.dump(data, f, indent=4)

                return data
        except Exception:
            pass
    else:
        print(f"CONFIG not found")
        return None

def load_config():
    if load_json(LOCAL_CONFIG_FILE):
        return data
    elif load_json(CONFIG_FILE):
        return data
    else:
        print("ERROR: config not found")
        return None

# turns key into proper json format and style
def cleanup_key(key):
    return str(key).replace(" ", "_").upper()

def update_config(key, value):
    global data
    if not data:
        data = load_json()

    print(f"Updating {key} to {value}")
    data[key] = value
    with open(LOCAL_CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved {key} to {LOCAL_CONFIG_FILE}")