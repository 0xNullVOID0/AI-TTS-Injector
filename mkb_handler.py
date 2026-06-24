import mouse
import keyboard as kb

from autoplay import on_key_event
from config_handler import config


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
        kb.hook(lambda e: on_key_event(e, config.target_window, func))






mkb = _MkbHandler()
