import winreg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RegistryDebug")

def dump_registry():
    path = r"Software\Microsoft\OneDrive\Accounts"
    print(f"Opening {path}...")
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            info = winreg.QueryInfoKey(key)
            print(f"Found {info[0]} subkeys.")
            for i in range(info[0]):
                subkey_name = winreg.EnumKey(key, i)
                print(f"\n--- Subkey: {subkey_name} ---")
                
                sub_path = f"{path}\\{subkey_name}"
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_path) as subkey:
                        # List all values
                        try:
                            # Just print UserEmail and UserFolder if they exist, or all values
                            vals_count = winreg.QueryInfoKey(subkey)[1]
                            for j in range(vals_count):
                                val_name, val_data, _ = winreg.EnumValue(subkey, j)
                            print(f"  {val_name}: {val_data}")
                        except Exception as e:
                            print(f"  Error iterating values: {e}")
                except Exception as e:
                    print(f"  Error opening subkey {subkey_name}: {e}")

    except Exception as e:
        print(f"Failed to open root key: {e}")

if __name__ == "__main__":
    dump_registry()
