import ctypes
import os
import time
from ctypes import wintypes

import cv2
import keyboard
import mss
import numpy as np
import pywintypes
import win32api
import win32con
import win32gui
import win32process

from config_handler import config
from profiler import profiler


EVENT_WINDOW_FOCUS_CHANGED = win32con.EVENT_OBJECT_FOCUS     # The ID for "Window Focus Changed" in Windows API https://learn.microsoft.com/en-us/windows/win32/winauto/event-constants
EVENT_SYSTEM_FOREGROUND = win32con.EVENT_SYSTEM_FOREGROUND   # The Windows constant for focus change


# TODO move all to window_handler?
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


class Window:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.title = win32gui.GetWindowText(hwnd)
        self.pid = None
        self.path = self.get_process_path()
        self._is_target = False
        self.blacklisted = False
        self.is_blacklisted()
        # print(f'Initialized {self}')


    def __repr__(self):
        return (f"[Window] {self.title}\nPID: {self.pid}\nBlacklisted: {self.blacklisted}\n"
                f"Path: {self.path}")


    def send_background_click(self, window=config.target_window, interval=config.interval):
        try:
            # get relative window size and calc coords
            width, height = window.get_dimensions()
            center_x = int(width / 2)
            center_y = int(height / 2)
            print(f"[Window] calculated center click at: ({center_x}, {center_y})")
            click_coords = win32api.MAKELONG(center_x, center_y)

            # mouse click down and up
            win32gui.PostMessage(window.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, click_coords)
            print(f"[Window] automated background clickie on: {window.title}")
            time.sleep(0.05)
            win32gui.PostMessage(window.hwnd, win32con.WM_LBUTTONUP, 0, click_coords)
        except Exception as e:
            print(f"[Window] failed to calculate window center or click: {e}")


    def is_blacklisted(self):
        # aggressive blacklist check, if path just matches any word in blacklist # TODO maybe too harsh and false positive risk?
        if self.path and any(word in self.path for word in config.blacklist):
            print("[Window] Program on blacklist, skipping")
            self.blacklisted = True
        return self.blacklisted

    def is_target(self, target=config.target_window):
        if self.is_blacklisted():
            return False

        # TODO move this to setters/getters and or just store paths at pathlib.Path?
        # Normalize paths to handle slash mismatches (e.g., / vs \)
        normalized_path = os.path.normpath(self.path) if self.path else ""
        normalized_target = os.path.normpath(config.target_window_path) if config.target_window_path else ""
        normalized_targets = [os.path.normpath(target) for target in config.target_list]

        print(f"normalized path: {normalized_path}")
        print(f"normalized targets: {normalized_target}")
        print(f"normalized targets: {normalized_targets}")

        # TODO still do window title comparisons too?
        # TODO test programs with multiple windows, instances, popups whatever
        # check both process path and title since title alone is too unreliable
        if normalized_path == normalized_target:
            print("[Window] IS target")
            self._is_target = True
        elif normalized_path in normalized_targets:
            print("[Window] on target list, continuing")
            self._is_target = True
        else:
            print("[Window] IS NOT a target")
            self._is_target = False

        # if config.target_window_title == self.title and config.target_window_path == self.path:
        return self._is_target

    def get_bounds(self):
        return win32gui.GetWindowRect(self.hwnd)

    def get_dimensions(self):
        rect = self.get_bounds()
        # calculate width and height using relative screen coords
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        print(f'[Window] dimensions: width={width}, height={height}')
        return width, height

    def get_capture_region(self):
        rect = self.get_bounds()
        width, height = self.get_dimensions()

        # convert rect to appropriate dictionary for mss
        region = {
            "top": rect[1],
            "left": rect[0],
            "width": width,
            "height": height
        }
        print(f'[Window] region: {region}')
        return region

    def capture_area(self, x, y, width, height):
        rect = self.get_bounds()

        with mss.MSS() as sct:
            try:
                image = sct.grab((x, y, width, height))

                
                print(f"[Window] capture: {image}")

                # image = OCRImage(image)
                image = np.array(image)

                # save images for debugging
                if config.debug and not config.duplicate:
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    cv2.imwrite(f"screenshots/window_{self.title}_{timestamp}.png", image)

                # img_array = process_image(img_array)
                return image
            except Exception as e:
                print(f"[Window] ERROR: Failed to grab window boundaries: {e}.")

    @staticmethod
    def get_foreground_window():
        return ctypes.windll.user32.GetForegroundWindow()

    @profiler.time_profile
    def capture(self):
        with mss.MSS() as sct:
            try:
                image = sct.grab(self.get_capture_region())
                print(f"[Window] capture: {image}")

                # image = OCRImage(image)
                image = np.array(image)

                # save images for debugging
                if config.debug and not config.duplicate:
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    cv2.imwrite(f"screenshots/window_{self.title}_{timestamp}.png", image)

                # img_array = process_image(img_array)
                return image
            except Exception as e:
                print(f"[Window] ERROR: Failed to grab window boundaries: {e}.")

    # use process path instead of window name for more reliability
    @profiler.time_profile
    def get_process_path(self):
        try:
            # use PID and handle to get process path
            _, pid = win32process.GetWindowThreadProcessId(self.hwnd)
            handle = win32api.OpenProcess(0x0400 | 0x0010, False, pid)
            self.pid = pid
            path = win32process.GetModuleFileNameEx(handle, 0)
            # print(f'[Window] PID: {pid}, path: {path}')
            return path
        except pywintypes.error as e:
            if e.winerror == 87:
                print(f"[Window] Failed to get process path but most likely the window just got minimized: {e}")
            elif e.winerror == 5:
                print(f"[Window] ERROR Access denied: {e}")
            else:
                print(f"[Window] ERROR: Failed to get process path: {e}")

    # Gets called when focused window changes
    @staticmethod
    @profiler.time_profile
    def on_focus_change(win_event_hook, event, hwnd, id_object, id_child, event_thread, event_time):
        # set active window so its globally available
        config.active_window = Window(hwnd)
        print(f"[Window] FOCUS CHANGED\n{config.active_window}")

        # TODO if autoplay on stop checking as intensely

        if config.active_window.is_target():
            config.target_window = config.active_window
            name_key, text_key = config.get_target_window_selection_keys()

            # TODO fix make more reliable
            config.name_selector = config.get(name_key)
            config.text_selector = config.get(text_key)

            if config.ocr:
                ocr.start_processing(config.target_window)