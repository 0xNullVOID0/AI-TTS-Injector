import tkinter as tk

# Creates a fullscreen overlay that allows user to select an area on screen they want scanned
class SnippingSelector:
    def __init__(self):
        self.root = tk.Tk()

        # UI config
        self.root.attributes('-alpha', 0.3) # opacity
        self.root.attributes('-fullscreen', True)
        self.root.attributes("-topmost", True)
        self.root.config(cursor="cross") # change cursor

        # canvas for mouse drawing / selection
        self.canvas = tk.Canvas(self.root, cursor="cross", bg="grey")
        self.canvas.pack(fill="both", expand=True)

        self.coords = None

        # set mouse actions to calculation steps with escape as cancel button
        self.canvas.bind("<ButtonPress-1>", self.on_start)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_end)
        self.root.bind("<Escape>", lambda e: self.root.destroy()) # TODO can only press escape once already starting to select, once mouse is already clicking?

    # Set starting point of area and draw box
    def on_start(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline='red', width=2)

    # Drag box/area
    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_end(self, event):
        # calculate absolute top-left and bottom-right
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)

        # ensure width and height are positive
        width = x2 - x1
        height = y2 - y1

        # basic validation to check if user actually dragged a box
        if width > 0 and height > 0:
            self.coords = {'left': x1, 'top': y1, 'width': width, 'height': height}
            print(f'selected coords: {self.coords}')
        else:
            self.coords = None

        self.root.destroy()

    def get_selection(self):
        self.root.mainloop()
        return self.coords