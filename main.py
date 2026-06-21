# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import time
import pygetwindow as gw

target_window_title = "Task Manager" # TODO make generic, customizable, configurable, with keybinds and manual entry in a config file
target_window_focused = False

def get_active_window():
    active_window = gw.getActiveWindow()
    print(f'Active Window: {active_window}')
    time.sleep(0.5) # slow down script, prevent infinite checking
    return active_window

def run():
    global target_window_focused
    while True:
        window = get_active_window()
        if window.title == target_window_title:
            target_window_focused = True
            print(f'Target Window in FOCUS')
        else:
            if target_window_focused:
                print(f'Lost FOCUS')
            target_window_focused = False


if __name__ == '__main__':
    run()
