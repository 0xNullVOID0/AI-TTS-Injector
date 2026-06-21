# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import time
import pygetwindow as gw

TARGET_WINDOW_TITLE = "Task Manager" # TODO make generic, customizable, configurable, with keybinds and manual entry in a config file

def getActiveWindow():
    active_window = gw.getActiveWindow()
    print(f'Active Window: {active_window}')
    time.sleep(0.5) # slow down script, prevent infinite checking

def run():
    while True:
        getActiveWindow()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    run()
