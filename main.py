# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import atexit
import ctypes
import time
from ctypes import wintypes
import cv2
import mss
import numpy as np
import pythoncom
import win32con

from autoplay import update_interval
from config_handler import config
from kokoro_tts import send
from mkb_handler import mkb
from profiler import profiler
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


@profiler.time_profile
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
            send(text.lower(), voice)
        else:
            print(f"ELSE NO TEXT")
    else:
        print(f"No screenshot")


# Gets called when focused window changes
def on_focus_change(win_event_hook, event, hwnd, id_object, id_child, event_thread, event_time):
    # set active window so its globally available
    config.active_window = Window(hwnd)

    # TODO if autoplay on stop checking as intensely

    if config.active_window.is_target_window():
        config.target_window = config.active_window
        name_key, text_key = config.get_target_window_selection_keys()

        # TODO fix make more reliable
        config.name_selector = config.get(name_key)
        config.text_selector = config.get(text_key)

        start_ocr_process(config.target_window)

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

        #TODO just use VOICE_MAP.get(clean_name, default_voice)?

    return config.default_voice

# TODO remove? keep?
def capture_screen():
    with mss.MSS() as sct:
        # grab whole screen
        screenshot = sct.grab(sct.monitors[1])
        screenshot = np.array(screenshot)
        print(f'screenshot shape: {screenshot.shape}')
        return screenshot

@profiler.time_profile
def grab_name_and_text_selections(screenshot):
    # if these 2 selections have been set manually with keybinds or from the config then only scan and read those portions
    if config.name_selector and config.text_selector:
        print("name and text SELECTED")
        ns = config.name_selector
        name_crop = screenshot[
            ns["top"]: ns["top"] + ns["height"],
            ns["left"]: ns["left"] + ns["width"]
        ]

        raw_name = run_ocr(name_crop, is_raw_array=True)
        # print(f'name selector: {name_selector}')
        # print(f'name_crop: {name_crop}')

        # remove brackets, common artifact characters, and all surrounding whitespace
        name = raw_name.replace('[', '').replace(']', '').strip() if raw_name else ""

        print(f'name: {name}')

        ts = config.text_selector
        text_crop = screenshot[
            ts["top"]: ts["top"] + ts["height"],
            ts["left"]: ts["left"] + ts["width"]
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


# Get text from passed image
@profiler.time_profile
def run_ocr(screenshot, is_raw_array=False):
    img_array = screenshot

    # convert screenshot to easyOCR compatible format
    img_rgb = img_array[:, :, :3][:, :, ::-1]


    # set ocr with larger margin of error to prevent scanned text order being messed up by letters like q or l
    result = ocr.readtext(img_rgb, paragraph=True, x_ths=1000.0,
                           y_ths=0.1 #  prevents it from grouping across different vertical lines
    )
    # result = ocr.readtext(img_rgb)

    config.ocr_counter += 1 # TODO also do a calculation with -duplicate text so it stays accurate with audio_played
    print(f"ocr count: {config.ocr_counter}")

    all_text = ""

    # print text of image
    for (bbox, text) in result:
        all_text += text + " "

 # TODO change vertical reading per program, set that setting per program, others are way more vertical text

    return all_text

def select_portion(p=""):
    # TODO make it so that a window which gets snipped on automatically becomes the target window and gets saved and all other proper actions so its properly dynamic
    # get the selected area from user


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
                # add selected area to array
                selected_areas.append(region) #TODO make relative to window size and or position? dont bother? too much work that a simple reselect would fix anyway
                print(f'selected selection: {selected_areas}')
    else:
        print("select portion ELSE")


# TODO just make all into on_trigger(type)? instead of get name and text?
def on_trigger(p):
    print(f"Keybind pressed: {p}")
    if p == "set_target_window":
        if config.active_window:
            title = config.active_window.title
            path = config.active_window.get_process_path()

            # TODO look at this
            config.target_window_title = title
            config.target_window_path = path
            config.update("TARGET_WINDOW_TITLE", title)
            config.update("TARGET_WINDOW_PATH", path)
    elif p == "left":
        # config.previous() # TODO going back like 5 audios, rewind functionality
        pass
    elif p == "right":
        config.skip()
    elif p == "down":
        config.stop()
    elif p == "up":
        config.start()
    elif p == "name" or p == "text":
        select_portion(p)
    else:
        print("ELSE KEYBIND")

def on_left_click():
    print("Left clickie")

    # if config.running:
    #     config.resume()
    # else:
    #     config.resume()

    if config.active_window == config.target_window:
        time.sleep(0.5) # wait a bit for text to update before scanning # TODO think about this time.sleep here, thread blocking issues and such
        start_ocr_process(config.target_window)




# TODO move to mkb handler
kb.hook(lambda e: on_key_event(e, config.target_window, start_ocr_process))



@profiler.time_profile
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

    # settings = SettingsGUI()
    # settings.mainloop()

    # set mouse and keyboard binds and pass trigger functions
    mkb.set_keybinds(on_trigger)
    mkb.set_mousebinds(on_left_click)

    try:
        # keep script running and listens for Windows events
        pythoncom.PumpMessages()
    except KeyboardInterrupt:
        return

if __name__ == '__main__':
    run()
