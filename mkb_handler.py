import ctypes
import threading
from ctypes import wintypes

import mouse
import keyboard as kb
import win32api

from autoplay import autoplay_loop
from config_handler import config
from window_handler import Window


# POINT structure for GetCursorPos
class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _MkbHandler:
    def __init__(self):
        self.keybinds = config.get("KEYBINDS")

    # TODO make keybinds properly customizable
    def set_keybinds(self, trigger): # name func or hook instead?
        # start screen selection on trigger
        kb.add_hotkey('shift+[', trigger, args=['name'])
        kb.add_hotkey('shift+]', trigger, args=['text'])
        kb.add_hotkey('shift+.', trigger, args=['set_target_window'])

        # every arrow key direction
        kb.add_hotkey('left', trigger, args=['left'])
        kb.add_hotkey('right', trigger, args=['right'])
        kb.add_hotkey('up', trigger, args=['up'])
        kb.add_hotkey('down', trigger, args=['down'])

    def set_mousebinds(self, trigger):
        mouse.on_click(trigger)

    def set_autoplay_hook(self, func):
        # keybind hook for autoplay keybind events
        kb.hook(lambda e: self.on_key_event(e, config.target_window, func))

    def on_key_event(self, event, window=config.target_window, func=None):
        # get ocr function from main file
        # start_ocr_callback = ocr_func

        # TODO make keybinds / event names enums?

        # if autoplay key pressed/toggled
        if event.name == 'scroll lock' and event.event_type == kb.KEY_UP:
            autoplay_key_toggled = win32api.GetKeyState(0x91) & 1  # scroll lock key code

            if autoplay_key_toggled and window:
                # only if OCR is ON
                if config.ocr:
                    # if autoplay not on then start its thread
                    if not config.autoplay:
                        config.autoplay = True
                        # spawn the auto clicker loop in a background thread
                        autoplay_worker = threading.Thread(target=autoplay_loop, args=[window], daemon=True)
                        autoplay_worker.start()
                elif config.auto_keypress:
                    if config.target_window:
                        window.send_background_key("right", config.target_window)


            elif not autoplay_key_toggled:
                config.autoplay = False





mkb = _MkbHandler()
