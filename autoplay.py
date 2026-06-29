import threading
import time

import keyboard
import keyboard as kb
import win32api
import win32con
import win32gui

from config_handler import config
from window_handler import Window

start_ocr_callback = None

# TODO add counters here

def update_interval(i):
    config.interval = i
    config.save("INTERVAL", i)
    print(f"interval updated to: {i}")

def autoplay_loop(window):
    print("autoplay loop started")
    while config.autoplay:
        if window:
            if config.ocr:
                window.send_background_click()

                # TODO fix
                if start_ocr_callback:
                    start_ocr_callback(window)

            time.sleep(config.autoplay_interval) # todo make customizable
                time.sleep(config.autoplay_interval) # todo make customizable



            # TODO make autoplay interval dependant on text length for appropiate response time of every function, api whatever
    print("autoplay loop stopped")
