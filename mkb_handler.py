import ctypes
import threading
from ctypes import wintypes
from typing import NamedTuple

import mouse
import keyboard as kb
import win32api

from autoplay import autoplay_loop
from config_handler import config
from window_handler import Window


# POINT structure for GetCursorPos
class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class Keybind(NamedTuple):
    key: str          # KEYBINDS key in config.json
    action: str       # string passed to on_trigger
    default: str      # default keybind, gets overridden by custom binds from config.json
    on_release: bool = False  # fire on key release instead of key press(to prevent multiple triggers when holding down a key, for more precise step adjustments)


class _MkbHandler:
    KEYBIND_ACTIONS = (
        Keybind("NAME", "name", "shift+["),
        Keybind("TEXT", "text", "shift+]"),
        Keybind("SET_TARGET_WINDOW", "set_target_window", "shift+."),
        Keybind("LEFT", "left", "left"),
        Keybind("RIGHT", "right", "right"),
        Keybind("UP", "up", "up"),
        Keybind("DOWN", "down", "down"),
        Keybind("START_OCR", "start_ocr", "shift+up"),
        Keybind("DISABLE_OCR", "disable_ocr", "shift+down"),

        Keybind("SPEED_UP", "speed_up", "alt+page up", True),
        Keybind("SPEED_DOWN", "speed_down", "alt+page down", True),
    )

    def __init__(self):
        self.keybinds = config.get("KEYBINDS")

    def set_keybinds(self, trigger):
        # Keybinds from config.json override the defaults per action
        configured = self.keybinds or {}
        for keybind in self.KEYBIND_ACTIONS:
            hotkey = configured.get(keybind.key) or keybind.default
            try:
                kb.add_hotkey(hotkey, trigger, args=[keybind.action], trigger_on_release=keybind.on_release)
            except Exception as exc:
                # fallback to default keybind if the configured one is invalid
                print(f"Keybind {keybind.key} '{hotkey}' was not accepted: {exc}")
                if hotkey != keybind.default:
                    kb.add_hotkey(keybind.default, trigger, args=[keybind.action], trigger_on_release=keybind.on_release)

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
