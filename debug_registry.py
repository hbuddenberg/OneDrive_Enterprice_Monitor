"""Dump all Registry values for OneDrive Business account."""

import winreg
import json
from datetime import datetime

def dump_registry():
    try:
        # Check Business accounts in registry
        accounts_path = r"Software\Microsoft\OneDrive\Accounts"
        
        print("REGISTRY DUMP FOR ONEDRIVE ACCOUNTS")
        print("=" * 60)
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, accounts_path) as accounts_key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(accounts_key, i)
                    print(f"\nScanning: {subkey_name}")
                    
                    if subkey_name.startswith("Business") or subkey_name.startswith("Personal"):
                        subkey_path = f"{accounts_path}\\{subkey_name}"
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey_path) as subkey:
                            # Dump all values
                            j = 0
                            while True:
                                try:
                                    name, value, type_ = winreg.EnumValue(subkey, j)
                                    # Mask sensitive data
                                    if "Email" in name or "UserFolder" in name or "MountPoint" in name:
                                       print(f"  {name}: {value}")
                                    else:
                                       print(f"  {name}: {value} (Type: {type_})")
                                    j += 1
                                except OSError:
                                    break
                    i += 1
                except OSError:
                    break
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_registry()
