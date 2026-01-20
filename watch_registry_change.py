import winreg
import time
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("RegistryWatcher")

def get_registry_state():
    state = {}
    path = r"Software\Microsoft\OneDrive\Accounts"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            info = winreg.QueryInfoKey(key)
            for i in range(info[0]):
                subkey_name = winreg.EnumKey(key, i)
                state[subkey_name] = {}
                sub_path = f"{path}\\{subkey_name}"
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_path) as subkey:
                        vals_count = winreg.QueryInfoKey(subkey)[1]
                        for j in range(vals_count):
                            val_name, val_data, _ = winreg.EnumValue(subkey, j)
                            state[subkey_name][val_name] = str(val_data)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error reading registry: {e}")
    return state

def diff_states(old, new):
    changes = []
    # Check for new or modified keys/values
    for key, val in new.items():
        if key not in old:
            changes.append(f"New Account Subkey: {key}")
        else:
            for sub_k, sub_v in val.items():
                if sub_k not in old[key]:
                    changes.append(f"New Value in {key}: {sub_k} = {sub_v}")
                elif old[key][sub_k] != sub_v:
                    changes.append(f"Changed Value in {key}: {sub_k} = {sub_v} (was {old[key][sub_k]})")
    
    # Check for deleted keys/values
    for key in old:
        if key not in new:
            changes.append(f"Deleted Account Subkey: {key}")
        else:
            for sub_k in old[key]:
                if sub_k not in new[key]:
                    changes.append(f"Deleted Value in {key}: {sub_k}")
    
    return changes

def main():
    logger.info("Starting Registry Watcher for OneDrive Accounts...")
    initial_state = get_registry_state()
    logger.info(f"Initial state captured. Monitoring {len(initial_state)} accounts.")
    
    while True:
        try:
            current_state = get_registry_state()
            changes = diff_states(initial_state, current_state)
            
            if changes:
                logger.info("!" * 20)
                logger.info("REGISTRY CHANGE DETECTED:")
                for change in changes:
                    logger.info(change)
                logger.info("!" * 20)
                # Update state to current
                initial_state = current_state
                # We could exit here if we want to stop on first change, but user said "avisame"
                # For now just log it clearly.
                
            time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in watch loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
