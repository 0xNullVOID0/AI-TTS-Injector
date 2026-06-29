# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import atexit
import ctypes
import threading
import time
from ctypes import wintypes

import keyboard
import mss
import numpy as np
import pythoncom
import win32con

import ocr
from config_handler import config
from kokoro_api import boot_backend_api
from mkb_handler import mkb
from profiler import profiler
from queue_handler import q
from snipping_selector import SnippingSelector
from window_handler import Window, user32, WinEventProcess, EVENT_WINDOW_FOCUS_CHANGED, EVENT_SYSTEM_FOREGROUND
import popup_gui

# TODO add GUI for settings, config, customization like voice selection, target window selection
# TODO live translation?
# TODO pipeline CI/CD stuff
# TODO better ocr post processing and other cleaning
# TODO OCR post processing, correct size? downscaling, anti aliasing? different settings
# TODO add some sort of dictionary check and others checking for warning signs of incorrect text then send to another AI model for verification, validation/fixing
# TODO offer suno's bark compatibility / option, test it out first
# TODO orpheus-tts for default emotional layer?
# TODO hook into renpy functionality? other engine options and easy not too heavy stuff but later not prio, generalist first approach
# TODO other ocr options, and just general ocr settings for the ocr itself to adapt to the window's needs, its own text size and whatever
# TODO can still take window capture of different than intended window, fix
# TODO performance and delay testing, find bottleknecks


@profiler.time_profile
def cleanup():
    user32.UnhookWinEvent(hook)
    print("Hook removed cleanly.")

# TODO are they being unset cleanly?
atexit.register(cleanup)


# TODO remove? keep?
@profiler.time_profile
def capture_screen():
    with mss.MSS() as sct:
        # grab whole screen
        screenshot = sct.grab(sct.monitors[1])
        screenshot = np.array(screenshot)
        print(f'screenshot shape: {screenshot.shape}')
        return screenshot

# get the selected area from user
@profiler.time_profile
def select_portion(p=""):
    # TODO what if no target window? also make snipping a window the new config.target_window?
    if config.target_window:
        print("select portion IF target window")
        r = config.target_window.get_capture_region()
        selector = SnippingSelector(**r) # unpack dictionary into class initializer with ** operator
        region = selector.get_selection() # returns (left, top, width, height)

        if region:
            name_key, text_key = config.get_window_selection_keys(config.target_window_title)

            # save selected areas to config to prevent constant repetition
            if p == "name":
                print(f"Selected name: {region}")
                config.name_selector = region
                config.update(name_key, region)
            elif p == "text":
                config.text_selector = region
                config.update(text_key, region)
            else:
                print("ELSE KEYBIND")
    else:
        print("Target window not set")


# TODO refactor and move to mkb handler?
@profiler.time_profile
def on_trigger(p):
    print(f"Keybind pressed: {p}")
    if p == "set_target_window":
        if config.active_window:
            title = config.active_window.title
            path = config.active_window.get_process_path()

            # stop if on blacklist
            if config.active_window.is_blacklisted():
                return

            # TODO look at this
            config.target_window_title = title
            config.target_window_path = path
            config.update("TARGET_WINDOW_TITLE", title)
            config.update("TARGET_WINDOW_PATH", path)

            # force focus change event so proper steps for a focused target window get taken
            Window.on_focus_change(None, EVENT_SYSTEM_FOREGROUND, config.active_window.hwnd, 0, 0, 0, 0)

            # # TODO fix update right away,
            # on_left_click()
    elif p == "left":
        # config.previous() # TODO going back like 5 audios, rewind functionality
        pass
    elif p == "right":
        q.skip()
    elif p == "down":
        q.stop()
    elif p == "up":
        q.start()
    elif p == "start_ocr":
        config.ocr = True
        q.start()
    elif p == "disable_ocr":
        q.stop_ocr()
    elif p == "name" or p == "text":
        select_portion(p)
    else:
        print(f"ELSE KEYBIND")

@profiler.time_profile
def on_left_click():
    print("Left clickie")

    if config.running and config.ocr:
        # if active window is the target window and currently not snipping(to prevent screen selection clicks triggering unwanted scans)
        if config.active_window and config.active_window == config.target_window and not config.snipping:
                time.sleep(0.5) # wait a bit for text to update before scanning # TODO think about this time.sleep here, thread blocking issues and such
                ocr.start_processing(config.target_window)


@profiler.time_profile
def run():
    global hook
    process = WinEventProcess(Window.on_focus_change)

    # use the window event hook from user32.dll
    hook = user32.SetWinEventHook(
        EVENT_WINDOW_FOCUS_CHANGED, EVENT_WINDOW_FOCUS_CHANGED, 0,
        process, 0, 0,
        win32con.WINEVENT_OUTOFCONTEXT
    )

    if not hook:
        print("Failed to set hook")
        return

    # settings = SettingsGUI()
    # settings.mainloop()

    # set mouse and keyboard binds and pass trigger functions, and make sure they're set before popup is initialized otherwise it has no access to em
    mkb.set_keybinds(on_trigger)
    mkb.set_mousebinds(on_left_click)

    print(f"DEBUG mode: {config.debug}")

    api_process = boot_backend_api()

    # bind start/stop functions from queue handler to config
    config.on_start = q.start
    config.on_stop = q.stop

    if api_process:
        # True: Leaves Kokoro running when main.py stops
        # False: Kills Kokoro automatically when main.py closes
        if config.debug:
            print("[Debug Mode] Active: Kokoro API will persist in the background after exit")
        else:
            print("[Production Mode] Active: Tying Kokoro API to main script stop signals for auto termination")
            # only register the kill command in production mode
            atexit.register(api_process.terminate)

    try:
        # keep script
        while True:
            # pump/listen to Windows messages manually without locking the thread
            pythoncom.PumpWaitingMessages()
            time.sleep(0.05)
    except KeyboardInterrupt:
        return

if __name__ == '__main__':
    run()
