# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import atexit
import ctypes
import tkinter as tk
from ctypes import wintypes
import easyocr
import keyboard as kb
import mss
import numpy as np
import pythoncom
import win32con
import win32gui

from snipping_selector import SnippingSelector
from kokoro_tts import send_to_kokoro

# The ID for "Window Focus Changed" in Windows API
EVENT_WINDOW_FOCUS_CHANGED = win32con.EVENT_OBJECT_FOCUS
TARGET_WINDOW_TITLE = "Settings" # TODO make generic, customizable, configurable, with keybinds and manual entry in a config file

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

# Gets called when focused window changes
def on_focus_change(win_event_hook, event, hwnd, id_object, id_child, event_thread, event_time):
    window_title = win32gui.GetWindowText(hwnd)
    print(f'Active Window: {window_title}')

    if window_title == TARGET_WINDOW_TITLE:
        print(f'Target Window in FOCUS')
        capture_window(hwnd)

def cleanup():
    user32.UnhookWinEvent(hook)
    print("Hook removed cleanly.")

atexit.register(cleanup)

def capture_window(hwnd):
    rect = win32gui.GetWindowRect(hwnd)

    # convert rect to appropiate dictionary for mss
    monitor = {
        "top": rect[1],
        "left": rect[0],
        "width": rect[2] - rect[0],
        "height": rect[3] - rect[1]
    }

    # hardcoded coordinates for text we want to grab
    name_box = {"top": 1094, "left": 327, "width": 728, "height": 50}
    dial_box = {"top": 1193, "left": 332, "width": 1793, "height": 154}

    print(f'rect: {rect}')
    print(f'monitor: {monitor}')

    with mss.MSS() as sct:
        # if user has selected areas on screen then those will be scanned and read, otherwise default is the full window
        if selected_areas:
            for s in selected_areas:
                screenshot = sct.grab(s)
                print(f'screenshot: {screenshot}')
                run_ocr(screenshot)
        else:
            screenshot = sct.grab(monitor)
            print(f'screenshot: {screenshot}')
            run_ocr(screenshot)

        return screenshot # not relevant anymore?

# Get text from passed image
def run_ocr(screenshot):
    # convert screenshot to easyOCR compatible format
    img_array = np.array(screenshot)
    img_rgb = img_array[:, :, :3][:, :, ::-1]
    result = ocr.readtext(img_rgb)

    all_text = ""

    # print text of image
    for (bbox, text, prob) in result:
        print(f"Detected: {text} (Confidence: {prob:.2f})")
        all_text += text + " "

    print(all_text)

    # sends and plays audio using local kokoro
    send_to_kokoro(all_text)

def select_portion():
    # Get the selected area from user
    selector = SnippingSelector()
    region = selector.get_selection() # Returns (left, top, width, height)

    if region:
        # add selected area to array
        selected_areas.append(region) #TODO make relative to window size and or position? dont bother? too much work that a simple reselect would fix anyway
        print(f'selected selection: {selected_areas}')

        # TODO remove below?
        # Capture only selected region
        # with mss.mss() as sct:
            # img = np.array(sct.grab(region))
        # results = ocr.ocr(img)


def on_trigger():
    print("Keybind pressed")
    select_portion()

# check for keybind and start screen selection on trigger
kb.add_hotkey('ctrl+]', on_trigger) #TODO make keybind customizable

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
