import json
import requests
from requests import status_codes


def has_keys(array, *keys):
    return all(key in array for key in keys)

BASE_URL = "http://127.0.0.1:5000/"
HEADERS = {"Content-Type": "application/json"}

# TODO rename json to payload?
def api(route="/", _json=None, headers=HEADERS):
    url = BASE_URL + route
    response = None
    if _json:
        response = requests.post(url, json=_json, headers=HEADERS, timeout=120)
    else:
        response = requests.post(url, headers=HEADERS, timeout=120)

    if response.status_code != 200:
        print(f"ERROR: request {url} failed")
        return

    return response


def is_json(my_string):
    try:
        json.loads(my_string)
    except ValueError as e:
        return False
    return True


def json_serial(obj):
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    raise TypeError(f"Type {type(obj)} not serializable")



data = '{"name": "Joker", "active": true}'
print(is_json(data))
