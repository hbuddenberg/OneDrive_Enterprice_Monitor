import os
import win32com.client
from pathlib import Path

def dump_columns():
    path = r"C:\Users\hansbuddenberg\OneDrive - tipartner"
    name = ".monitor_canary"
    
    if not os.path.exists(os.path.join(path, name)):
        print("Canary file not found!")
        return

    shell = win32com.client.Dispatch("Shell.Application")
    folder = shell.Namespace(path)
    item = folder.ParseName(name)
    
    print(f"--- Details for {name} ---")
    for i in range(320):
        val = folder.GetDetailsOf(item, i)
        col_name = folder.GetDetailsOf(None, i)
        if val:
            print(f"{i}: {col_name} = {val}")

if __name__ == "__main__":
    dump_columns()
