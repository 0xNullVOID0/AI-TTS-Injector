import win32gui


class Window:
    def __init__(self, hwnd):
        self.window = None
        self.hwnd = hwnd
        self.title = win32gui.GetWindowText(hwnd)
        print(f'Window class init: {self.title}')

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