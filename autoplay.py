import threading
import time
import win32api
import win32con
import win32gui
import keyboard as kb

autoplay_on = False
start_ocr_callback = None

# TODO add capturing target window screen instead of just a raw screenshot of monitor for autoplay to continue working even with alt tab and just more reliable in general

def autoplay_loop(hwnd):
    global autoplay_on

    print("autoplay loop started")
    while autoplay_on:
        if hwnd:
            send_background_click(hwnd)

            if start_ocr_callback:
                start_ocr_callback(hwnd)

            time.sleep(1) # todo make customizable
    print("autoplay loop stopped")


# TODO move on key event to seperate keyboard handler file? and just pass function for capslock to this
def on_key_event(event, target_window_hwnd, ocr_func):
    global autoplay_on, start_ocr_callback

    # get ocr function from main file
    start_ocr_callback = ocr_func

    if event.name == 'scroll lock' and event.event_type ==kb.KEY_UP:
        scroll_lock_on = win32api.GetKeyState(0x91) & 1

        if scroll_lock_on and target_window_hwnd:
            if not autoplay_on:
                autoplay_on = True
                # spawn the auto clicker loop in a background thread
                autoplay_worker = threading.Thread(target=autoplay_loop,args=[target_window_hwnd],daemon=True)
                autoplay_worker.start()

        elif not scroll_lock_on:
          autoplay_on = False

def send_background_click(hwnd):
    try:
        # get relative window size and calc coords
        _, _, width, height = win32gui.GetClientRect(hwnd)
        center_x = int(width / 2)
        center_y = int(height / 2)
        print(f"calculated center click at: ({center_x}, {center_y})")
        click_coords = win32api.MAKELONG(center_x, center_y)

        # mouse click down and up
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, click_coords)
        print("automated background clickie")
        time.sleep(0.05)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, click_coords)
    except Exception as e:
        print(f"Autoplay failed to calculate window center or click: {e}")