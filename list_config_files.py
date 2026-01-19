"""List OneDrive configuration and log files to a text file."""

import os
from pathlib import Path
from datetime import datetime

def list_files():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        print("LOCALAPPDATA not found")
        return

    base_path = Path(local_app_data) / "Microsoft" / "OneDrive"
    
    output_lines = []
    output_lines.append("ONEDRIVE FILE DISCOVERY")
    output_lines.append("=" * 60)
    
    # 1. Scan Settings
    settings_path = base_path / "settings"
    if settings_path.exists():
        output_lines.append(f"\nScanning: {settings_path}")
        files = []
        for p in settings_path.rglob("*"):
            if p.is_file() and p.suffix.lower() in [".ini", ".xml", ".dat", ".txt"]:
                 files.append(p)
        
        # Sort by modification time
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for p in files[:30]:
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            output_lines.append(f"[{mtime}] {p}")

    # 2. Scan Logs
    logs_path = base_path / "logs"
    if logs_path.exists():
        output_lines.append(f"\nScanning: {logs_path}")
        files = []
        for p in logs_path.rglob("*"):
             if p.is_file() and p.suffix.lower() in [".log", ".txt", ".etl"]:
                 files.append(p)
                 
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for p in files[:30]:
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            output_lines.append(f"[{mtime}] {p}")
            
    # Write output
    out_file = Path("onedrive_files.txt")
    out_file.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"Written to {out_file.absolute()}")

if __name__ == "__main__":
    list_files()
