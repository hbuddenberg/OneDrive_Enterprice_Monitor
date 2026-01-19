"""Script to move mouse to OneDrive icon to refresh tooltip."""

from pywinauto import Desktop
import time
import sys

def refresh_icon():
    desktop = Desktop(backend="uia")
    taskbar = desktop.window(class_name="Shell_TrayWnd")
    
    print("Searching for OneDrive icon...", file=sys.stderr)
    
    found = False
    for ctrl in taskbar.descendants():
        try:
            name = ctrl.window_text()
            if name and "onedrive" in name.lower() and "tipartner" in name.lower():
                print(f"Found icon: {name}", file=sys.stderr)
                # Move mouse to center of icon
                rect = ctrl.rectangle()
                try:
                    import pywinauto.mouse
                    print(f"Moving mouse to {rect.mid_point()}", file=sys.stderr)
                    pywinauto.mouse.move(coords=(rect.mid_point().x, rect.mid_point().y))
                    found = True
                    break
                except Exception as e:
                    print(f"Error moving mouse: {e}", file=sys.stderr)
        except Exception:
            pass
            
    if found:
        print("Mouse moved. Waiting 2 seconds...", file=sys.stderr)
        time.sleep(2)
        print("Done.", file=sys.stderr)
    else:
        print("Icon not found.", file=sys.stderr)

if __name__ == "__main__":
    refresh_icon()
