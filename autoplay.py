import threading
import time

import keyboard as kb
import win32api
import win32con
import win32gui

from config_handler import config

start_ocr_callback = None

# TODO add counters here

def update_interval(i):
    config.interval = i
    config.save("INTERVAL", i)
    print(f"interval updated to: {i}")

def autoplay_loop(window):
    print("autoplay loop started")
    while config.autoplay_on:
        if window:
            send_background_click(window)

            if start_ocr_callback:
                start_ocr_callback(window)

            time.sleep(config.autoplay_interval) # todo make customizable
            # TODO make autoplay interval dependant on text length for appropiate response time of every function, api whatever
    print("autoplay loop stopped")


# TODO move on key event to seperate keyboard handler file? and just pass function for capslock to this
def on_key_event(event, target_window, ocr_func):
    global start_ocr_callback

    # get ocr function from main file
    start_ocr_callback = ocr_func

    if event.name == 'scroll lock' and event.event_type ==kb.KEY_UP:
        scroll_lock_on = win32api.GetKeyState(0x91) & 1 # scroll lock key code

        if scroll_lock_on and target_window:
            if not config.autoplay_on:
                config.autoplay_on = True
                # spawn the auto clicker loop in a background thread
                autoplay_worker = threading.Thread(target=autoplay_loop, args=[target_window], daemon=True)
                autoplay_worker.start()

        elif not scroll_lock_on:
          config.autoplay_on = False

def send_background_click(window):
    try:
        # get relative window size and calc coords
        width, height = window.get_dimensions()
        center_x = int(width / 2)
        center_y = int(height / 2)
        print(f"calculated center click at: ({center_x}, {center_y})")
        click_coords = win32api.MAKELONG(center_x, center_y)

        # mouse click down and up
        win32gui.PostMessage(window.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, click_coords)
        print("automated background clickie")
        time.sleep(0.05)
        win32gui.PostMessage(window.hwnd, win32con.WM_LBUTTONUP, 0, click_coords)
    except Exception as e:
        print(f"Autoplay failed to calculate window center or click: {e}")