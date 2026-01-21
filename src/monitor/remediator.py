import logging
import subprocess
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from src.shared.schemas import OneDriveStatus

from src.shared.notifier import Notifier

logger = logging.getLogger(__name__)

class RemediationAction:
    def __init__(self):
        self.cooldown_ends: Optional[datetime] = None
        self.restart_attempts: int = 0
        self.last_restart_hour: int = datetime.now().hour
        self.COOLDOWN_SECONDS = 60
        self.MAX_RESTARTS_PER_HOUR = 3
        
        # Persistence tracking
        self.last_status: Optional[OneDriveStatus] = None
        self.status_first_seen: Optional[datetime] = None
        # How long a bad status must persist before we act (to avoid flapping)
        self.REQUIRED_PERSISTENCE = 30 # seconds

        # Notification Logic
        self.notifier = Notifier()
        self.last_remediation_time: Optional[datetime] = None
        self.notification_sent_for_incident: bool = False

    def act(self, status: OneDriveStatus) -> bool:
        """Attempt to fix the current status if critical. Returns True if action taken."""
        now = datetime.now()
        
        # 1. Update Persistence Tracker
        if status != self.last_status:
            self.last_status = status
            self.status_first_seen = now
            self.notification_sent_for_incident = False # New status, new incident
            # If we just switched to OK, reset counters immediately
            if status == OneDriveStatus.OK:
                self.reset_counters()
            return False
            
        # 2. Check Duration
        time_in_state = (now - self.status_first_seen).total_seconds()
        if time_in_state < self.REQUIRED_PERSISTENCE:
            return False

        from src.shared.config import get_config
        self.config = get_config()

        # 3. Check if we just tried to fix it and it failed (Persistence after fix)
        if self.last_remediation_time:
            time_since_fix = (now - self.last_remediation_time).total_seconds()
            check_delay = self.config.notifications.failed_remediation_delay_seconds
            
            if time_since_fix < check_delay: # If status persists within the check window
                 # Wait, logic check:
                 # If we are strictly LESS than delay, we assume we are still waiting for it to fix?
                 # NO. Attempted restart.
                 # If status is STILL BAD immediately after restart, it's bad.
                 # BUT restarting takes time (process start, sync init).
                 # So we WANT to ignore failures for a grace period?
                 # OR "Si al reiniciar persiste... no esperes 5 min".
                 # This implies: If it fails, report it SOONER.
                 pass
            
            # Revised Logic based on user request:
            # We want to wait AT LEAST X seconds for it to recover.
            # If status is bad AND time_since_fix > X seconds -> NOTIFY.
            # Currently: `if time_since_fix < 300: notify()` -> This notifies REPEATEDLY while inside the window?
            # Wait, my previous logic was:
            # `if time_since_fix < 300: notify()`. 
            # This logic means: "If the bad status is happening AND it is recent (within 5 mins of fix), consider it a FAILED FIX."
            # Which is correct for "Persistence after fix".
            # The USER wants to make "300" configurable (so they can lower it to e.g. 60s).
            
            if time_since_fix < check_delay:
                 # Fix didn't work (we are seeing bad status shortly after fix).
                 if not self.notification_sent_for_incident:
                     msg = f"OneDrive status '{status.value}' persists despite restart attempt {time_since_fix:.0f}s ago."
                     logger.warning(f"REMEDIATION FAILED: {msg}")
                     self.notifier.notify(f"Remediation Failed ({status.value})", msg, "ERROR")
                     self.notification_sent_for_incident = True
                 return False

        # 4. Check Cooldown for ACTION
        if self._in_cooldown():
            return False

        # 5. Act - Force Restart for ALL critical states as requested
        # NOT_RUNNING, AUTH_REQUIRED, PAUSED -> Restart
        if status in [OneDriveStatus.NOT_RUNNING, OneDriveStatus.AUTH_REQUIRED, OneDriveStatus.PAUSED]:
            return self._force_restart_onedrive(status)
            
        return False

    def _in_cooldown(self) -> bool:
        if self.cooldown_ends and datetime.now() < self.cooldown_ends:
            return True
        return False
    
    def reset_counters(self):
        # Reset cooldown if healthy
        self.cooldown_ends = None
        self.last_remediation_time = None
        self.notification_sent_for_incident = False
        
        # Reset hourly counter if hour changed
        current_hour = datetime.now().hour
        if current_hour != self.last_restart_hour:
            self.restart_attempts = 0
            self.last_restart_hour = current_hour

    def _force_restart_onedrive(self, reason_status: OneDriveStatus) -> bool:
        # Check limits
        if self.restart_attempts >= self.MAX_RESTARTS_PER_HOUR:
            logger.warning(f"REMEDIATION: Max restarts ({self.MAX_RESTARTS_PER_HOUR}/hr) reached. Skipping fix.")
            self.notifier.notify("Remediation Skipped", "Max restarts per hour reached. Manual intervention required.", "ERROR")
            return False

        logger.warning(f"REMEDIATION: Force Restart triggered due to {reason_status.value}...")
        
        # 1. Kill Process (Force)
        try:
             subprocess.run(["taskkill", "/F", "/IM", "OneDrive.exe"], 
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
             time.sleep(5) # Wait for complete termination
        except Exception as e:
             logger.error(f"REMEDIATION: Failed to kill OneDrive: {e}")

        # 2. Start Process
        # Locate OneDrive
        paths = [
            Path(os.environ["LOCALAPPDATA"]) / "Microsoft/OneDrive/OneDrive.exe",
            Path("C:/Program Files/Microsoft OneDrive/OneDrive.exe"),
            Path("C:/Program Files (x86)/Microsoft OneDrive/OneDrive.exe")
        ]
        
        target_exe = None
        for p in paths:
            if p.exists():
                target_exe = p
                break
        
        if not target_exe:
            logger.error("REMEDIATION: Could not find OneDrive.exe in standard locations.")
            self.notifier.notify("Remediation Error", "Could not find OneDrive binary to restart.", "ERROR")
            return False

        try:
            # Start Process non-blocking, background
            subprocess.Popen([str(target_exe), "/background"], shell=False)
            logger.info(f"REMEDIATION: Restarted {target_exe}")
            
            self.restart_attempts += 1
            self.cooldown_ends = datetime.now() + timedelta(seconds=self.COOLDOWN_SECONDS)
            self.last_remediation_time = datetime.now()
            return True
        except Exception as e:
            logger.error(f"REMEDIATION: Failed to start process: {e}")
            self.notifier.notify("Remediation Error", f"Failed to start OneDrive: {e}", "ERROR")
            return False
