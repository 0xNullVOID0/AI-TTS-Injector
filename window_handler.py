import time

import cv2
import mss
import numpy as np
import pywintypes
import win32api
import win32gui
import win32process

from config_handler import config


class Window:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.title = win32gui.GetWindowText(hwnd)
        self.pid = None
        self.path = self.get_process_path()
        self.blacklisted = False
        print(f'Window object init: {self.title}')

    def is_blacklisted(self):
        if self.path and any(word in self.path for word in config.blacklist):
            print("[Window] Program on blacklist, skipping")
            self.blacklisted = True
        return self.blacklisted

    def is_target_window(self):
        if self.is_blacklisted():
            return

        # TODO test programs with multiple windows, instances, popups whatever
        # check both process path and title since title alone is too unreliable
        ctwT = config.target_window_title
        ctwP = config.target_window_path
        print(f'target window title: {ctwT}')
        print(f'target window path: {ctwP}')

        print(f'SELF window title: {self.title}')
        print(f'SELF window path: {self.path}')



        if config.target_window_title == self.title and config.target_window_path == self.path:
            print(f'IS target window')
            return True
        print(f'NOT target window')
        return False

    def get_bounds(self):
        return win32gui.GetWindowRect(self.hwnd)

    def get_dimensions(self):
        rect = self.get_bounds()
        # calculate width and height using relative screen coords
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        print(f'window dimensions: width={width}, height={height}')
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
        print(f'window region: {region}')
        return region

    def capture(self):
        with mss.MSS() as sct:
            try:
                image = sct.grab(self.get_capture_region())
                print(f"window capture: {image}")

                # image = OCRImage(image)
                image = np.array(image)

                # save images for debugging
                if config.debug and not config.duplicate:
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    cv2.imwrite(f"screenshots/window_{self.title}_{timestamp}.png", image)

                # img_array = process_image(img_array)
                return image
            except Exception as e:
                print(f"ERROR: Failed to grab window boundaries: {e}.")

    # use process path instead of window name for more reliability
    def get_process_path(self):
        try:
            # use PID and handle to get process path
            _, pid = win32process.GetWindowThreadProcessId(self.hwnd)
            handle = win32api.OpenProcess(0x0400 | 0x0010, False, pid)
            self.pid = pid
            path = win32process.GetModuleFileNameEx(handle, 0)
            print(f'window PID: {pid}, path: {path}')
            return path
        except pywintypes.error as e:
            if e.winerror == 87:
                print(f"Failed to get process path but most likely the window just got minimized: {e}")
            elif e.winerror == 5:
                print(f"ERROR Access denied: {e}")
            else:
                print(f"ERROR: Failed to get process path: {e}")