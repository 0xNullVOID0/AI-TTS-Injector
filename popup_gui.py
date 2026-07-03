import tkinter as tk
from tkinter import ttk
import threading
import keyboard
from config_handler import config


class LiveControlPanel:
    def __init__(self):
        self.root = None
        self.is_open = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.style = None
        self.name = "AI-TTS Control Panel"
        self.toggle = False
        self.keybind = "shift+home" # TODO set from config and even change/update from within this thing

    def build_ui(self):
        self.root = tk.Tk()
        self.root.title(self.name)

        # borderless window layout configuration
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e24")

        # set size and position
        screen_width = self.root.winfo_screenwidth()
        window_width, window_height = 420, 210
        x_coord = int((screen_width / 2) - (window_width / 2))
        y_coord = 150
        self.root.geometry(f"{window_width}x{window_height}+{x_coord}+{y_coord}")
        self.root.minsize(380, 190)

        # UI config
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TLabel", background="#1e1e24", foreground="#ffffff", font=("Segoe UI", 9))

        # setup toggle buttons with style settings
        self.style.configure("Running.TButton", font=("Segoe UI", 9, "bold"), borderwidth=0, focuscolor="none")
        self.style.configure("Autoplay.TButton", font=("Segoe UI", 9, "bold"), borderwidth=0, focuscolor="none")

        # map the active states so hover doesn't break them
        self.style.map("Running.TButton",
                       background=[("active", "#4a4a5a")],
                       foreground=[("active", "#ffffff")])

        self.style.map("Autoplay.TButton",
                       background=[("active", "#4a4a5a")],
                       foreground=[("active", "#ffffff")])

        # container frame for header elements to allow side by side packing
        self.header_frame = tk.Frame(self.root, bg="#2d2d3a")
        self.header_frame.pack(fill="x", side="top")

        # set header title and drag events
        self.header = tk.Label(self.header_frame, text=f"⚡ {self.name.upper()}", bg="#2d2d3a", fg="#a0a0c0",
                               font=("Segoe UI", 8, "bold"), anchor="w", padx=10, cursor="fleur")
        self.header.pack(fill="x", side="left", expand=True)
        self.header.bind("<Button-1>", self.start_window_drag)
        self.header.bind("<B1-Motion>", self.execute_window_drag)

        # set themed close button
        self.close_button = tk.Button(
            self.header_frame,
            text="✕",
            bg="#2d2d3a",
            fg="#a0a0c0",
            activebackground="#c62828", # turn red when clicked
            activeforeground="#ffffff",
            bd=0,  # set borderless
            font=("Segoe UI", 9),
            padx=12,
            pady=2,
            cursor="hand2",
            command=self.close
        )
        self.close_button.pack(side="right", fill="y")

        # change color on hover
        self.close_button.bind("<Enter>", lambda e: self.close_button.config(bg="#c62828", fg="#ffffff"))
        self.close_button.bind("<Leave>", lambda e: self.close_button.config(bg="#2d2d3a", fg="#a0a0c0"))

        # container for the rest, all its contents
        container = tk.Frame(self.root, bg="#1e1e24")
        container.pack(padx=15, pady=15, fill="both", expand=True)

        # set UI variables
        init_interval = float(config.interval) if config.interval is not None else 1.0
        init_autoplay = float(config.autoplay_interval) if config.autoplay_interval is not None else 2.0
        self.str_interval = tk.StringVar(value=f"{init_interval:.2f}")
        self.str_autoplay = tk.StringVar(value=f"{init_autoplay:.2f}")

        # CONTROLLER 1: Interval Slider Row ---
        ttk.Label(container, text="Interval (s):").grid(row=0, column=0, sticky="w", pady=6)

        self.slider_int = tk.Scale(
            container, from_=0.05, to=5.00, resolution=0.05, orient="horizontal",
            bg="#1e1e24", fg="#ffffff", highlightbackground="#1e1e24", troughcolor="#2d2d3a",
            activebackground="#5a5a6e", showvalue=False,
            command=lambda val: self.on_slider_ui_update("interval", val, self.str_interval, self.entry_int)
        )
        self.slider_int.set(init_interval)
        self.slider_int.grid(row=0, column=1, padx=(10, 5), sticky="ew")

        # number entry box
        self.entry_int = tk.Entry(container, textvariable=self.str_interval, width=6, bg="#2d2d3a", fg="#ffffff",
                                  insertbackground="white", bd=0, font=("Consolas", 10, "bold"), justify="center")
        self.entry_int.grid(row=0, column=2, padx=5, sticky="e")
        self.entry_int.bind("<Return>",
                            lambda e: self.on_text_entry_commit("interval", self.str_interval, self.slider_int,
                                                                (0.05, 5.0)))
        self.entry_int.bind("<FocusOut>",
                            lambda e: self.on_text_entry_commit("interval", self.str_interval, self.slider_int,
                                                                (0.05, 5.0)))

        # --- CONTROLLER 2: Autoplay Slider Row ---
        ttk.Label(container, text="Autoplay (s):").grid(row=1, column=0, sticky="w", pady=6)

        self.slider_auto = tk.Scale(
            container, from_=0.1, to=10.0, resolution=0.1, orient="horizontal",
            bg="#1e1e24", fg="#ffffff", highlightbackground="#1e1e24", troughcolor="#2d2d3a",
            activebackground="#5a5a6e", showvalue=False,
            command=lambda val: self.on_slider_ui_update("autoplay_interval", val, self.str_autoplay, self.entry_auto)
        )
        self.slider_auto.set(init_autoplay)
        self.slider_auto.grid(row=1, column=1, padx=(10, 5), sticky="ew")

        self.entry_auto = tk.Entry(container, textvariable=self.str_autoplay, width=6, bg="#2d2d3a", fg="#ffffff",
                                   insertbackground="white", bd=0, font=("Consolas", 10, "bold"), justify="center")
        self.entry_auto.grid(row=1, column=2, padx=5, sticky="e")
        self.entry_auto.bind("<Return>", lambda e: self.on_text_entry_commit("autoplay_interval", self.str_autoplay,
                                                                             self.slider_auto, (0.1, 10.0)))
        self.entry_auto.bind("<FocusOut>", lambda e: self.on_text_entry_commit("autoplay_interval", self.str_autoplay,
                                                                               self.slider_auto, (0.1, 10.0)))

        # --- CONTROLLER 3: Running Toggle Button Row ---
        ttk.Label(container, text="System Loop:").grid(row=2, column=0, sticky="w", pady=12)

        self.btn_running_toggle = ttk.Button(container, style="Running.TButton", command=lambda: self.on_ui_toggle_press("running"))
        self.btn_running_toggle.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=6)
        self.refresh_running_button_view()

        container.columnconfigure(1, weight=1)

        # --- CONTROLLER 4: Autoplay Toggle Button Row ---
        ttk.Label(container, text="Autoplay:").grid(row=3, column=0, sticky="w", pady=12)

        self.btn_autoplay_toggle = ttk.Button(container, style="Autoplay.TButton", command=lambda: self.on_ui_toggle_press("autoplay"))
        self.btn_autoplay_toggle.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10, pady=6)
        self.refresh_autoplay_button_view()

        container.columnconfigure(1, weight=1)

        # --- Window resize from corner ---
        self.grip = tk.Label(self.root, text="◢", bg="#1e1e24", fg="#3e3e4a", font=("Segoe UI", 8), cursor="size_nw_se")
        self.grip.pack(side="right", anchor="se")
        self.grip.bind("<Button-1>", self.start_resize_drag)
        self.grip.bind("<B1-Motion>", self.execute_resize_drag)

        self.root.bind("<Escape>", lambda e: self.close())

        # hide popup window until popup hotkey pressed
        self.root.withdraw()

    def show(self):
        if not self.is_open:
            self.is_open = True
            self.root.after(0, self._safe_show)
        else:
            self.root.after(0, lambda: (self.root.lift(), self.root.focus_force()))

            # toggle close
            if self.is_open:
                self.close()

    def _safe_show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def on_slider_ui_update(self, key, val, target_str_var, tracking_entry):

        # TODO only update on slider finish drag? instead of every frame

        if self.root.focus_get() != tracking_entry:
            float_val = float(val)
            target_str_var.set(f"{float_val:.2f}")

            print(f"SLIDER UPDATE: key: {key}, val: {val}")
            # TODO make live updating saved settings/config optional or ask to confirm or revert it to original at close?, easy back to default or original settings button
            config.update(key.upper(), float_val)

    def on_text_entry_commit(self, key, tracking_str_var, slider_widget, bounds):
        try:
            raw_val = float(tracking_str_var.get())
            clamped_val = max(bounds[0], min(raw_val, bounds[1]))

            tracking_str_var.set(f"{clamped_val:.2f}")
            slider_widget.set(clamped_val)
            config.update(key.upper(), clamped_val)
        except ValueError:
            current_stable_value = float(config.get(key))
            tracking_str_var.set(f"{current_stable_value:.2f}")
        self.root.focus_set()

    def on_ui_toggle_press(self, key):
        # no need to store such values in json
        # current_state = bool(config.get("running"))
        # new_state = not current_state
        # config.update("running", new_state)

        val = config.__getattribute__(key)
        config.__setattr__(key, not val)
        # config.running = not config.running

        if key == "running":
            self.refresh_running_button_view()
        elif key == "autoplay":
            self.refresh_autoplay_button_view()

    def refresh_running_button_view(self):
        if self.style is None:
            return

        if config.running:
            self.btn_running_toggle.config(text="RUNNING / ACTIVE")
            self.style.configure("Running.TButton", background="#2e7d32", foreground="#ffffff")
        else:
            print("CHANGE BUTTON COLOR")
            self.btn_running_toggle.config(text="STOPPED / INACTIVE")
            self.style.configure("Running.TButton", background="#c62828", foreground="#ffffff")

    def refresh_autoplay_button_view(self):
        if self.style is None:
            return

        if config.autoplay:
            self.btn_autoplay_toggle.config(text="AUTOPLAY ON")
            self.style.configure("Autoplay.TButton", background="#2e7d32", foreground="#ffffff")
        else:
            self.btn_autoplay_toggle.config(text="AUTOPLAY OFF")
            self.style.configure("Autoplay.TButton", background="#c62828", foreground="#ffffff")

    # --- Frame Windows Mechanics ---
    def start_window_drag(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def execute_window_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.drag_start_x)
        y = self.root.winfo_y() + (event.y - self.drag_start_y)
        self.root.geometry(f"+{x}+{y}")

    def start_resize_drag(self, event):
        self.resize_start_width = self.root.winfo_width()
        self.resize_start_height = self.root.winfo_height()
        self.resize_mouse_x = event.x_root
        self.resize_mouse_y = event.y_root

    def execute_resize_drag(self, event):
        delta_w = event.x_root - self.resize_mouse_x
        delta_h = event.y_root - self.resize_mouse_y
        new_w = max(self.root.minsize()[0], self.resize_start_width + delta_w)
        new_h = max(self.root.minsize()[1], self.resize_start_height + delta_h)
        self.root.geometry(f"{new_w}x{new_h}+{self.root.winfo_x()}+{self.root.winfo_y()}")

    def close(self):
        if self.root:
            # hide instead of closing/killing it
            self.root.withdraw()
        self.is_open = False

def set_popup():
    panel_manager = LiveControlPanel()
    panel_manager.build_ui()

    keyboard.add_hotkey(panel_manager.keybind, panel_manager.show)

    # pass popup to config for easy global access
    config.popup = panel_manager

    panel_manager.root.mainloop()