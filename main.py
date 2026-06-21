# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import easyocr
import mss
import win32con
import win32gui
import pythoncom
import ctypes
import atexit
from ctypes import wintypes
import os
import numpy
import torch

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
        screenshot = sct.grab(monitor)
        print(f'screenshot: {screenshot}')
        run_ocr(screenshot)

        return screenshot

def run_ocr(screenshot):
    # convert screenshot to easyocr compatible format
    img_array = numpy.array(screenshot)
    img_rgb = img_array[:, :, :3][:, :, ::-1]
    result = ocr.readtext(img_rgb)

    # print text of image
    for (bbox, text, prob) in result:
        print(f"Detected: {text} (Confidence: {prob:.2f})")

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
        exit

if __name__ == '__main__':
    run()
