# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import time
import pygetwindow as gw

TARGET_WINDOW_TITLE = "Task Manager" # TODO make generic, customizable, configurable, with keybinds and manual entry in a config file
targetWindowFocused = False

def getActiveWindow():
    active_window = gw.getActiveWindow()
    print(f'Active Window: {active_window}')
    time.sleep(0.5) # slow down script, prevent infinite checking
    return active_window

def run():
    global targetWindowFocused
    while True:
        window = getActiveWindow()
        if window.title == TARGET_WINDOW_TITLE:
            targetWindowFocused = True
            print(f'Target Window in FOCUS')
        else:
            if targetWindowFocused:
                print(f'Lost FOCUS')
            targetWindowFocused = False


if __name__ == '__main__':
    run()
