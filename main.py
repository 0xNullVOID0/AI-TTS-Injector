# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import win32con
import win32gui
import pythoncom
import ctypes
from ctypes import wintypes

# The ID for "Window Focus Changed" in Windows API
EVENT_WINDOW_FOCUS_CHANGED = win32con.EVENT_OBJECT_FOCUS
TARGET_WINDOW_TITLE = "Settings" # TODO make generic, customizable, configurable, with keybinds and manual entry in a config file

# Load the Windows DLL for SetWinEventHook
user32 = ctypes.windll.user32

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

def on_focus_change(win_event_hook, event, hwnd, id_object, id_child, event_thread, event_time):
    window_title = win32gui.GetWindowText(hwnd)
    print(f'Active Window: {window_title}')

    if window_title == TARGET_WINDOW_TITLE:
        print(f'Target Window in FOCUS')

def run():
    process = WinEventProcess(on_focus_change)

    # Use the window event hook from user32.dll
    hook = user32.SetWinEventHook(
        EVENT_WINDOW_FOCUS_CHANGED, EVENT_WINDOW_FOCUS_CHANGED, 0,
        process, 0, 0,
        win32con.WINEVENT_OUTOFCONTEXT
    )

    if not hook:
        print("Failed to set hook")
        return

    try:
        # Keep script running and listens for Windows events
        pythoncom.PumpMessages()
    except KeyboardInterrupt:
        user32.UnhookWinEvent(hook)
        print("Hook removed cleanly.")

if __name__ == '__main__':
    run()
