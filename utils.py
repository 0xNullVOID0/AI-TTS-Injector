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

# TODO move to own file?
# Global APIClient class for cleaner, more readable and reusable code
class APIClient:
    def __init__(self, BASE_URL, HEADERS, client=None):  # TODO set user name fix hardcode
        self.BASE_URL = BASE_URL
        self.HEADERS = HEADERS
        self.client = client


    def api(self, route="/", payload=None, req_type=None):
        url = f"{self.BASE_URL}{route}"  # TODO improve
        print(f"Calling: {url}")

        response = None

        if payload:
            if is_json(payload):
                response = requests.post(url, json=payload, headers=self.HEADERS, timeout=120)
            else:
                # response = requests.post(url, headers=self.HEADERS, timeout=120)
                print(f"ERROR: payload {payload} failed, NOT (proper?) JSON") # TODO redundant?
                response = Exception("ERROR: payload {payload} failed, NOT (proper?) JSON")
            # except Exception as e:
            #     print(f"ERROR: request {url} failed")

            # if is_json(payload):
            #     response = requests.post(url, json=payload, headers=self.HEADERS, timeout=120)
            # else:
            #     response = requests.post(url, payload=payload, headers=self.HEADERS, timeout=120)
        elif req_type == "GET":
            response = requests.get(url, headers=self.HEADERS, timeout=120)
        else:
            response = requests.post(url, headers=self.HEADERS, timeout=120)

        if response.status_code == 200:
            print(response)
        else:
            print(f"ERROR: request {url} failed")
            # Exception("ERROR: payload {payload} failed, NOT (proper?) JSON")

        return response

