# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import atexit
import ctypes
import json
import os
import time
import tkinter as tk
from ctypes import wintypes
import cv2
import easyocr
import keyboard as kb
import mss
import numpy as np
import pythoncom
import win32con
import win32gui
import mouse

from config import load_config, CONFIG_FILE, LOCAL_CONFIG_FILE, update_config, cleanup_key
from snipping_selector import SnippingSelector
from kokoro_tts import send_to_kokoro

# TODO add auto play with something like capslock toggle
# TODO add emergency skip or stop button and or toggle
# TODO move config to its own file

config = load_config()

# Map character names to the desired Kokoro voice codes
VOICE_MAP = config['VOICE_MAP']
print(f"voice map: {VOICE_MAP}")

# The ID for "Window Focus Changed" in Windows API https://learn.microsoft.com/en-us/windows/win32/winauto/event-constants
EVENT_WINDOW_FOCUS_CHANGED = win32con.EVENT_OBJECT_FOCUS
TARGET_WINDOW_TITLE = config["TARGET_WINDOW_TITLE"]

# Verify cuda stuff for ocr debugging
# print(f"CUDA status: {torch.cuda.is_available()}")
# print(f"DEBUG: Torch sees GPU: {torch.cuda.is_available()}")
# print(f"DEBUG: Torch device name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
# print(f"DEBUG: Python executable: {os.sys.executable}")
ocr = easyocr.Reader(['en'], gpu=True)

# Load the Windows DLL for SetWinEventHook
user32 = ctypes.windll.user32
hook = None

# Define the callback types for SetWinEventHook
WinEventProcess = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD
)

is_selecting = False
selected_areas = []
name_selector = None
text_selector = None

json_name_key = f"{cleanup_key(TARGET_WINDOW_TITLE)}_NAME_COORDS"
json_text_key = f"{cleanup_key(TARGET_WINDOW_TITLE)}_TEXT_COORDS"


# checks saved screen selections for targeted window to skip constant manual repeat selections
if json_name_key in config:
    name_selector = config[json_name_key]
    print(f"Loading {json_name_key} from {LOCAL_CONFIG_FILE}. {name_selector}")

if json_text_key in config:
    text_selector = config[json_text_key]
    print(f"Loading {json_text_key} from {LOCAL_CONFIG_FILE}. {text_selector}")

active_hwnd = None
active_window_title = None
last_active_window_title = None
last_text = None

def check_if_targeted_window(hwnd):
    global active_window_title
    window_title = win32gui.GetWindowText(hwnd)
    active_window_title = window_title
    print(f'Active Window: {window_title}')

    if window_title == TARGET_WINDOW_TITLE:
        print(f'Target Window in FOCUS')
        return True
    return False

def start_ocr_process(hwnd):
    global last_text
    screenshot = capture_window(hwnd)

    if screenshot.any():
        name, text = grab_name_and_text_selections(screenshot)
        voice = get_voice_for_name(name)

        # prevent duplicate requests
        if text and text != last_text:
            print(f"TEXT SELECTED: {text}")
            last_text = text
            # sends and plays audio using local kokoro
            print("SENDING ")
            send_to_kokoro(text, voice)
        else:
            print(f"ELSE NO TEXT")

# Gets called when focused window changes
def on_focus_change(win_event_hook, event, hwnd, id_object, id_child, event_thread, event_time):
    global active_hwnd, last_text
    active_hwnd = hwnd

    if check_if_targeted_window(hwnd):
        start_ocr_process(hwnd)

    # if check_if_targeted_window(hwnd): # TODO eventually add specfic and relative active window capture only?

def cleanup():
    user32.UnhookWinEvent(hook)
    print("Hook removed cleanly.")

atexit.register(cleanup)

def get_voice_for_name(name):
    print("Getting voice for", name)
    for character, voice in VOICE_MAP.items():
        print(character)
        print(voice)
        if character.lower() in name.lower():
            print(f"Set {character}'s voice: {voice}")
            return voice
    return "af_heart"

def capture_screen():
    with mss.MSS() as sct:
        # grab whole screen
        screenshot = sct.grab(sct.monitors[1]) # TODO multi monitors?
        screenshot = np.array(screenshot)
        print(f'screenshot shape: {screenshot.shape}')
        return screenshot

def grab_name_and_text_selections(screenshot):
    global last_text

    # if these 2 selections have been set manually with keybinds or from the config then only scan and read those portions
    if name_selector and text_selector:
        print("NAME AND TEXT SELECTED")
        name_crop = screenshot[
            name_selector["top"]: name_selector["top"] + name_selector["height"],
            name_selector["left"]: name_selector["left"] + name_selector["width"]
        ]

        raw_name = run_ocr(name_crop, is_raw_array=True)
        print(f'name selector: {name_selector}')
        print(f'name_crop: {name_crop}')

        # remove brackets, common artifact characters, and all surrounding whitespace
        name = raw_name.replace('[', '').replace(']', '').strip() if raw_name else ""

        print(f'name: {name}')

        text_crop = screenshot[
            text_selector["top"]: text_selector["top"] + text_selector["height"],
            text_selector["left"]: text_selector["left"] + text_selector["width"]
        ]
        text = run_ocr(text_crop, is_raw_array=True)
        print(f'text: {text}')

        # save screenshots for debugging
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        cv2.imwrite(f"screenshots/debug_name_crop_{timestamp}.png", name_crop)
        cv2.imwrite(f"screenshots/debug_text_crop_{timestamp}.png", text_crop)

        return name, text

def capture_window(hwnd):
    global last_text
    rect = win32gui.GetWindowRect(hwnd)
    # convert rect to appropiate dictionary for mss
    monitor = {
        "top": rect[1],
        "left": rect[0],
        "width": rect[2] - rect[0],
        "height": rect[3] - rect[1]
    }
    with mss.MSS() as sct:
        try:
            window_capture = sct.grab(monitor)
            return np.array(window_capture)
        except Exception as e:
            print(f"Failed to grab window boundaries: {e}. Falling back.")

# Get text from passed image
def run_ocr(screenshot, is_raw_array=False):
    global last_text

    # redundant?
    if is_raw_array:
        img_array = screenshot
    else:
        img_array = np.array(screenshot)
    # convert screenshot to easyOCR compatible format
    img_rgb = img_array[:, :, :3][:, :, ::-1]
    result = ocr.readtext(img_rgb)

    all_text = ""

    # print text of image
    for (bbox, text, prob) in result:
        print(f"Detected: {text} (Confidence: {prob:.2f})")
        all_text += text + " "

    print(all_text)
    return all_text

def select_portion(p=""):
    global name_selector, text_selector
    # Get the selected area from user
    selector = SnippingSelector()
    region = selector.get_selection() # Returns (left, top, width, height)

    if region:
        if p == "name":
            print(f"Selected name: {region}")
            name_selector = region
            update_config(f"{cleanup_key(TARGET_WINDOW_TITLE)}_NAME_COORDS", name_selector) # save selected area to config to prevent constant repetition
        elif p == "text":
            text_selector = region
            update_config(f"{cleanup_key(TARGET_WINDOW_TITLE)}_TEXT_COORDS", text_selector)
        else:
            # add selected area to array
            selected_areas.append(region) #TODO make relative to window size and or position? dont bother? too much work that a simple reselect would fix anyway
            print(f'selected selection: {selected_areas}')


# TODO just make all into on_trigger(type)? instead of get name and text?
def on_trigger(p):
    print("Keybind pressed")
    select_portion(p)

def on_left_click():
    print("Left clickie")
    global active_hwnd
    if check_if_targeted_window(active_hwnd):
        time.sleep(0.5) # wait a bit for text to update before scanning
        start_ocr_process(active_hwnd)

mouse.on_click(on_left_click)
# check for keybind and start screen selection on trigger
kb.add_hotkey('ctrl+.', on_trigger) #TODO make keybind customizable
kb.add_hotkey('ctrl+[', on_trigger, args=['name'])
kb.add_hotkey('ctrl+]', on_trigger, args=['text'])

def run():
    global hook
    process = WinEventProcess(on_focus_change)

    # Use the window event hook from user32.dll
    hook = user32.SetWinEventHook(
        EVENT_WINDOW_FOCUS_CHANGED, EVENT_WINDOW_FOCUS_CHANGED, 0,
        process, 0, 0,
        win32con.WINEVENT_OUTOFCONTEXT
    )

    if not hook:
        print("Failed to set hook")
        return

    try:
        # Keep script running and listens for Windows events
        pythoncom.PumpMessages()
    except KeyboardInterrupt:
        return

if __name__ == '__main__':
    run()
