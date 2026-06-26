import tkinter as tk

from config_handler import config


# TODO fix snipping being buggy for fullscreen programs? or other issues

# Creates a fullscreen overlay that allows user to select an area on screen they want scanned
class SnippingSelector:
    def __init__(self, left, top, width, height):
        self.root = tk.Tk()

        # quick conversion for window capture region dict
        x = left
        y = top

        # save offsets for relative coordinates calculations
        self.win_x = x
        self.win_y = y

        # force tkinter to fit exactly over the target window
        geometry_str = f"{width}x{height}+{x}+{y}"
        self.root.geometry(geometry_str)

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes('-alpha', 0.3) # opacity

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="grey")
        self.canvas.pack(fill="both", expand=True)

        self.start_x = self.start_y = 0
        self.rect = None
        self.coords = None

        self.canvas.bind("<ButtonPress-1>", self.on_start)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_end)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    # set starting point of area and draw box
    def on_start(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline='red', width=2)

    # drag box/area
    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_end(self, event):
        # calculate absolute top-left and bottom-right
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)

        # coords local/relative to the window
        self.coords = {
            'left': x1,
            'top': y1,
            'width': x2 - x1,
            'height': y2 - y1
        }
        self.root.destroy()

    def get_selection(self):
        config.snipping = True
        self.root.mainloop()

        config.snipping = False
        return self.coords