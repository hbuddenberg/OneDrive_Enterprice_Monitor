from src.monitor.remediator import RemediationAction
from src.shared.schemas import OneDriveStatus
from datetime import datetime, timedelta
import logging
import time

# Configure logging to see output
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_paused():
    print("\n--- Testing PAUSED Remediation ---")
    r = RemediationAction()
    r.REQUIRED_PERSISTENCE = 0
    
    # 1. Register State
    r.act(OneDriveStatus.PAUSED)
    print("Registered PAUSED state.")
    
    # 2. Simulate 3 hours passing
    r.status_first_seen = datetime.now() - timedelta(hours=3)
    
    # 3. Trigger
    res = r.act(OneDriveStatus.PAUSED)
    print(f"Result (Should be True): {res}")

def test_auth():
    print("\n--- Testing AUTH_REQUIRED Remediation ---")
    print("Ensure 'dummy_auth_window.py' is running!")
    r = RemediationAction()
    r.REQUIRED_PERSISTENCE = 0
    
    # 1. Register State
    r.act(OneDriveStatus.AUTH_REQUIRED)
    
    # 2. Trigger
    res = r.act(OneDriveStatus.AUTH_REQUIRED)
    print(f"Result (Should be True if window found): {res}")

if __name__ == "__main__":
    test_paused()
    # We will run auth test separately manually or via command chain
    # test_auth()
