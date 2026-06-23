# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import atexit
import ctypes
import re
import time
from ctypes import wintypes
import cv2
import easyocr
import keyboard as kb
import mouse
import mss
import numpy as np
import pythoncom
import win32con

from config_handler import config
from autoplay import on_key_event, update_interval
from kokoro_tts import send_to_kokoro
from snipping_selector import SnippingSelector
from window_handler import Window

# TODO add auto play with something like capslock toggle
# TODO add emergency skip or stop button and or toggle
# TODO move config to its own file
# TODO add GUI for settings, config, customization like voice selection, target window selection
# TODO live translation?
# TODO pipeline CI/CD stuff
# TODO add check for kokoro api available/running, show in gui too
# TODO better ocr post processing and other cleaning
# TODO OCR post processing, correct size? downscaling, anti aliasing? different settings
# TODO add some sort of dictionary check and others checking for warning signs of incorrect text then send to another AI model for verification, validation/fixing
# TODO offer suno's bark compatibility / option, test it out first
# TODO orpheus-tts for default emotional layer?
# TODO hook into renpy functionality? other engine options and easy not too heavy stuff but later not prio, generalist first approach
# TODO other ocr options, and just general ocr settings for the ocr itself to adapt to the window's needs, its own text size and whatever
# TODO can still take window capture of different than intended window, fix
# TODO performance and delay testing, find bottleknecks

# The ID for "Window Focus Changed" in Windows API https://learn.microsoft.com/en-us/windows/win32/winauto/event-constants
EVENT_WINDOW_FOCUS_CHANGED = win32con.EVENT_OBJECT_FOCUS


# Verify cuda stuff for ocr debugging
# print(f"CUDA status: {torch.cuda.is_available()}")
# print(f"DEBUG: Torch sees GPU: {torch.cuda.is_available()}")
# print(f"DEBUG: Torch device name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
# print(f"DEBUG: Python executable: {os.sys.executable}")
ocr = easyocr.Reader(['en'], gpu=True)
ocr_counter = 0

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

# TODO move to config?
active_window = None
target_window = None


def start_ocr_process(window):
    image = None
    voice = config.default_voice

    # only capture window if targeted window
    if window and window.is_target_window():
        image = window.capture()
    else:
        print("Not the target window")

    if image is not None and image.size > 0:
        # TODO check if window has had name and or text selections set

        name, text = grab_name_and_text_selections(image)

        # full window capture if name and text selections not set
        if (name, text) == (0, 0):
            print(f"Full window capture")
            text = run_ocr(image)
            print(f'text: {text}')
        else:
            voice = get_voice_for_name(name)

        # prevent duplicate requests
        if text and text != config.last_text:
            print(f"TEXT SELECTED: {text}")
            config.last_text = text
            # sends and plays audio using local kokoro
            print("SENDING ")
            send_to_kokoro(text.lower(), voice)
        else:
            print(f"ELSE NO TEXT")
    else:
        print(f"No screenshot")


# Gets called when focused window changes
def on_focus_change(win_event_hook, event, hwnd, id_object, id_child, event_thread, event_time):
    global active_window, target_window, name_selector, text_selector
    active_window = Window(hwnd)

    # TODO if autoplay on stop checking as intensely 

    if active_window.is_target_window():
        target_window = active_window
        name_key, text_key = config.get_window_selection_keys(config.target_window_title)
        name_selector = config.get(name_key)
        text_selector = config.get(text_key)

        start_ocr_process(target_window)

def cleanup():
    user32.UnhookWinEvent(hook)
    print("Hook removed cleanly.")

atexit.register(cleanup)

def get_voice_for_name(name):
    clean_name = name.strip().lower()
    print("Getting voice for:", clean_name)

    for character, voice in config.voice_map.items():
        if character.lower() == clean_name:
            print(f"Set {character}'s voice: {voice}")
            return voice
    return "af_heart"

    return config.default_voice

# TODO remove? keep?
def capture_screen():
    with mss.MSS() as sct:
        # grab whole screen
        screenshot = sct.grab(sct.monitors[1])
        screenshot = np.array(screenshot)
        print(f'screenshot shape: {screenshot.shape}')
        return screenshot

def grab_name_and_text_selections(screenshot):
    # if these 2 selections have been set manually with keybinds or from the config then only scan and read those portions
    if name_selector and text_selector:
        print("name and text SELECTED")
        name_crop = screenshot[
            name_selector["top"]: name_selector["top"] + name_selector["height"],
            name_selector["left"]: name_selector["left"] + name_selector["width"]
        ]

        raw_name = run_ocr(name_crop, is_raw_array=True)
        # print(f'name selector: {name_selector}')
        # print(f'name_crop: {name_crop}')

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
    else:
        print("NO name and text selected")
        return 0, 0 # return 0 if name and text selectors not set instead of None in case they are set but still return no value/text

def capture_window(window):
    global last_text
    rect = window.get_bounds()
    capture_region = window.get_capture_region()

    print(f'window rect: {rect}')
    print(f'window capture region: {capture_region}')
    with mss.MSS() as sct:
        try:
            window_capture = sct.grab(capture_region)
            print(f"window capture: {window_capture}")
            screenshot = np.array(window_capture)

            # save screenshots for debugging
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            cv2.imwrite(f"screenshots/window_{window.title}_{timestamp}.png", screenshot)

            return screenshot
        except Exception as e:
            print(f"Failed to grab window boundaries: {e}. Falling back.")

# Get text from passed image
def run_ocr(screenshot, is_raw_array=False):
    global ocr_counter

    img_array = screenshot

    # convert screenshot to easyOCR compatible format
    img_rgb = img_array[:, :, :3][:, :, ::-1]


    # set ocr with larger margin of error to prevent scanned text order being messed up by letters like q or l
    result = ocr.readtext(img_rgb, paragraph=True, x_ths=1000.0,
                           y_ths=0.1 #  prevents it from grouping across different vertical lines
    )
    # result = ocr.readtext(img_rgb)

    ocr_counter += 1 # TODO also do a calculation with -duplicate text so it stays accurate with audio_played
    print(f"ocr count: {ocr_counter}")

    all_text = ""

    # print text of image
    for (bbox, text) in result:
        all_text += text + " "

    print(all_text)
    return all_text

def select_portion(p=""):
    # TODO make it so that a window which gets snipped on automatically becomes the target window and gets saved and all other proper actions so its properly dynamic
    global target_window, name_selector, text_selector
    # get the selected area from user


    # TODO what if no target window? also make snipping a window the new target_window?
    if target_window:
        print("select portion IF target window")
        r = target_window.get_capture_region()
        selector = SnippingSelector(**r) # unpack dictionary into class initializer with ** operator
        region = selector.get_selection() # returns (left, top, width, height)

        if region:
            name_key, text_key = config.get_window_selection_keys(config.target_window_title)

            # save selected areas to config to prevent constant repetition
            if p == "name":
                print(f"Selected name: {region}")
                name_selector = region
                config.update(name_key, name_selector)
            elif p == "text":
                text_selector = region
                config.update(text_key, text_selector)
            else:
                # add selected area to array
                selected_areas.append(region) #TODO make relative to window size and or position? dont bother? too much work that a simple reselect would fix anyway
                print(f'selected selection: {selected_areas}')
    else:
        print("select portion ELSE")


# TODO just make all into on_trigger(type)? instead of get name and text?
def on_trigger(p):
    print(f"Keybind pressed: {p}")
    if p == "set_target_window":
        if active_window:
            title = active_window.title
            path = active_window.get_process_path()
            config.target_window_title = title
            config.target_window_path = path
            config.update("TARGET_WINDOW_TITLE", title)
            config.update("TARGET_WINDOW_PATH", path)
    else:
        select_portion(p)

def on_left_click():
    global target_window, target_window # TODO even neccesary?
    print("Left clickie")
    if active_window == target_window:
        time.sleep(0.5) # wait a bit for text to update before scanning
        start_ocr_process(target_window)

mouse.on_click(on_left_click)
# check for keybind and start screen selection on trigger
#kb.add_hotkey('ctrl+.', on_trigger) #TODO make keybind customizable
kb.add_hotkey('ctrl+[', on_trigger, args=['name'])
kb.add_hotkey('ctrl+]', on_trigger, args=['text'])
kb.add_hotkey('ctrl+.', on_trigger, args=['set_target_window'])


kb.hook(lambda e: on_key_event(e, target_window, start_ocr_process))

def run():
    global hook
    process = WinEventProcess(on_focus_change)

    # use the window event hook from user32.dll
    hook = user32.SetWinEventHook(
        EVENT_WINDOW_FOCUS_CHANGED, EVENT_WINDOW_FOCUS_CHANGED, 0,
        process, 0, 0,
        win32con.WINEVENT_OUTOFCONTEXT
    )

    if not hook:
        print("Failed to set hook")
        return

    try:
        # keep script running and listens for Windows events
        pythoncom.PumpMessages()
    except KeyboardInterrupt:
        return

if __name__ == '__main__':
    run()
