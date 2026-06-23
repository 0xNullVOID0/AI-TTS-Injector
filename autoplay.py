import threading
import time
import win32api
import win32con
import win32gui
import keyboard as kb

autoplay_on = False
start_ocr_callback = None
interval = 1

# TODO add counters here

# TODO add capturing target window screen instead of just a raw screenshot of monitor for autoplay to continue working even with alt tab and just more reliable in general

def autoplay_loop(hwnd):
def autoplay_loop(window):
    global autoplay_on

    print("autoplay loop started")
    while autoplay_on:
        if window:
            send_background_click(window)

            if start_ocr_callback:
                start_ocr_callback(window)

            time.sleep(1.75) # todo make customizable
            # TODO make autoplay interval dependant on text length for appropiate response time of every function, api whatever
    print("autoplay loop stopped")


# TODO move on key event to seperate keyboard handler file? and just pass function for capslock to this
def on_key_event(event, target_window, ocr_func):
    global autoplay_on, start_ocr_callback

    # get ocr function from main file
    start_ocr_callback = ocr_func

    if event.name == 'scroll lock' and event.event_type ==kb.KEY_UP:
        scroll_lock_on = win32api.GetKeyState(0x91) & 1 # scroll lock key code

        if scroll_lock_on and target_window:
            if not autoplay_on:
                autoplay_on = True
                # spawn the auto clicker loop in a background thread
                autoplay_worker = threading.Thread(target=autoplay_loop,args=[target_window],daemon=True)
                autoplay_worker.start()

        elif not scroll_lock_on:
          autoplay_on = False

def send_background_click(window):
    try:
        # get relative window size and calc coords
        width, height = window.get_dimensions()
        center_x = int(width / 2)
        center_y = int(height / 2)
        print(f"calculated center click at: ({center_x}, {center_y})")
        click_coords = win32api.MAKELONG(center_x, center_y)

        # mouse click down and up
        win32gui.PostMessage(window.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, click_coords)
        print("automated background clickie")
        time.sleep(0.05)
        win32gui.PostMessage(window.hwnd, win32con.WM_LBUTTONUP, 0, click_coords)
    except Exception as e:
        print(f"Autoplay failed to calculate window center or click: {e}")