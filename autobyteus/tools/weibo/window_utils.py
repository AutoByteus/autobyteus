from Xlib import display

def find_window_by_name(name):
    d = display.Display()
    root = d.screen().root
    windows = root.query_tree().children
    for window in windows:
        try:
            if window.get_wm_name() == name:
                return window
        except:
            pass
    return None