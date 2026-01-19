"""Watch SyncDiagnostics.log for changes."""

import time
import os
from pathlib import Path

LOG_PATH = Path(r"C:\Users\hansbuddenberg\AppData\Local\Microsoft\OneDrive\logs\Business1\SyncDiagnostics.log")

def watch_log():
    if not LOG_PATH.exists():
        print(f"Log not found: {LOG_PATH}")
        return

    print(f"Watching {LOG_PATH}")
    print("Toggle OneDrive Pause/Resume to see if this updates...")
    print("-" * 60)

    last_mtime = 0
    
    while True:
        try:
            mtime = LOG_PATH.stat().st_mtime
            if mtime != last_mtime:
                print(f"\n[UPDATED] {time.ctime(mtime)}")
                try:
                    content = LOG_PATH.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    # Print relevant lines
                    for line in lines:
                        if "SyncProgressState" in line or "UtcNow" in line:
                            print(f"  {line}")
                except Exception as e:
                    print(f"  Error reading: {e}")
                
                last_mtime = mtime
            
            time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    watch_log()
