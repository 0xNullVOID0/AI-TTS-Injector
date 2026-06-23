import time
import cv2
import mss
import numpy as np
import win32gui


class Window:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.title = win32gui.GetWindowText(hwnd)
        print(f'Window object init: {self.title}')

    def is_target_window(self, target_window_title):
        # TODO more reliable check with hwnd or something else instead?
        if self.title == target_window_title:
            print(f'IS target window')
            # target_window_hwnd = hwnd  # save its hwnd so we can always easily find and use it #TODO set this somewhere else, other function outside this?
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
                img_array = np.array(image) # turn into numpy array so it can be used by cv and ocr

                # save images for debugging
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                cv2.imwrite(f"screenshots/window_{self.title}_{timestamp}.png", img_array)

                return img_array
            except Exception as e:
                print(f"ERROR: Failed to grab window boundaries: {e}.")