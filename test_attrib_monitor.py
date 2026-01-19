import os
import time
import win32api
import win32con
import stat

FILE_PATH = r"C:\Users\hansbuddenberg\OneDrive - tipartner\.test_attrib_monitor"

def get_file_attributes(path):
    try:
        attrs = win32api.GetFileAttributes(path)
        attr_list = []
        if attrs & win32con.FILE_ATTRIBUTE_ARCHIVE: attr_list.append("ARCHIVE")
        if attrs & win32con.FILE_ATTRIBUTE_HIDDEN: attr_list.append("HIDDEN")
        if attrs & win32con.FILE_ATTRIBUTE_SYSTEM: attr_list.append("SYSTEM")
        if attrs & win32con.FILE_ATTRIBUTE_READONLY: attr_list.append("READONLY")
        if attrs & win32con.FILE_ATTRIBUTE_OFFLINE: attr_list.append("OFFLINE")
        if attrs & win32con.FILE_ATTRIBUTE_TEMPORARY: attr_list.append("TEMPORARY")
        if attrs & win32con.FILE_ATTRIBUTE_REPARSE_POINT: attr_list.append("REPARSE_POINT")
        if attrs & win32con.FILE_ATTRIBUTE_SPARSE_FILE: attr_list.append("SPARSE_FILE")
        
        # Check specifically for OneDrive status attributes if possible
        # These are not standard constants in win32con always
        # FILE_ATTRIBUTE_PINNED = 0x80000
        # FILE_ATTRIBUTE_UNPINNED = 0x100000
        # FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
        # FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
        
        if attrs & 0x80000: attr_list.append("PINNED")
        if attrs & 0x100000: attr_list.append("UNPINNED")
        if attrs & 0x40000: attr_list.append("RECALL_ON_OPEN")
        if attrs & 0x400000: attr_list.append("RECALL_ON_DATA_ACCESS")
        
        return f"{attrs} ({', '.join(attr_list)})"
    except Exception as e:
        return f"Error: {e}"

print(f"Monitoring {FILE_PATH}...")
print("Step 1: Creating file...")
with open(FILE_PATH, "w") as f:
    f.write(f"Test content {time.time()}")

# Monitor for 30 seconds
start_time = time.time()
while time.time() - start_time < 30:
    print(f"T+{time.time()-start_time:.1f}s: {get_file_attributes(FILE_PATH)}")
    time.sleep(0.5)

print("Step 2: Deleting file...")
try:
    os.remove(FILE_PATH)
    print("Deleted.")
except Exception as e:
    print(f"Delete failed: {e}")
