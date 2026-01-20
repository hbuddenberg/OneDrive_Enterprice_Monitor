import psutil
import time

print("Scanning for OneDrive processes...")
found = False
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] and 'onedrive' in proc.info['name'].lower():
            print(f"PID: {proc.info['pid']}")
            print(f"Name: {proc.info['name']}")
            print(f"CmdLine: {proc.info['cmdline']}")
            print("-" * 20)
            found = True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass

if not found:
    print("No OneDrive processes found.")
