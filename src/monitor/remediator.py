import logging
import subprocess
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from src.shared.schemas import OneDriveStatus

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

    def act(self, status: OneDriveStatus) -> bool:
        """Attempt to fix the current status if critical. Returns True if action taken."""
        now = datetime.now()
        
        # 1. Update Persistence Tracker
        if status != self.last_status:
            self.last_status = status
            self.status_first_seen = now
            # If we just switched to OK, reset counters immediately
            if status == OneDriveStatus.OK:
                self.reset_counters()
            return False
            
        # 2. Check Duration
        time_in_state = (now - self.status_first_seen).total_seconds()
        if time_in_state < self.REQUIRED_PERSISTENCE:
            return False

        # 3. Check Cooldown
        if self._in_cooldown():
            return False

        # 4. Act
        if status == OneDriveStatus.NOT_RUNNING:
            return self._restart_onedrive()
        
        if status == OneDriveStatus.AUTH_REQUIRED:
            return self._focus_auth_window()

        if status == OneDriveStatus.PAUSED:
             return self._handle_paused(time_in_state)
            
        return False

    def _in_cooldown(self) -> bool:
        if self.cooldown_ends and datetime.now() < self.cooldown_ends:
            return True
        return False
    
    def reset_counters(self):
        # Reset cooldown if healthy
        self.cooldown_ends = None
        
        # Reset hourly counter if hour changed
        current_hour = datetime.now().hour
        if current_hour != self.last_restart_hour:
            self.restart_attempts = 0
            self.last_restart_hour = current_hour

    def _restart_onedrive(self) -> bool:
        # Check limits
        if self.restart_attempts >= self.MAX_RESTARTS_PER_HOUR:
            logger.warning(f"REMEDIATION: Max restarts ({self.MAX_RESTARTS_PER_HOUR}/hr) reached. Skipping fix.")
            return False

        logger.warning("REMEDIATION: Attempting to restart OneDrive...")
        
        # Locate OneDrive
        # Standard paths
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
            return False

        try:
            # Start Process non-blocking, background
            subprocess.Popen([str(target_exe), "/background"], shell=False)
            logger.info(f"REMEDIATION: Triggered start of {target_exe}")
            
            self.restart_attempts += 1
            self.cooldown_ends = datetime.now() + timedelta(seconds=self.COOLDOWN_SECONDS)
            return True
        except Exception as e:
            logger.error(f"REMEDIATION: Failed to start process: {e}")
            return False

    def _focus_auth_window(self) -> bool:
        """Attempt to bring the OneDrive Sign In window to the foreground."""
        logger.warning("REMEDIATION: Attempting to focus Auth Window...")
        try:
            # PowerShell script to find and focus window
            ps_script = """
            $wshell = New-Object -ComObject WScript.Shell
            $proc = Get-Process | Where-Object { $_.MainWindowTitle -match 'Sign in|Iniciar sesión|Microsoft OneDrive|Contraseña|Password' } | Select-Object -First 1
            if ($proc) {
                $wshell.AppActivate($proc.Id)
                Write-Output "Focused"
            }
            """
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if "Focused" in result.stdout:
                logger.info("REMEDIATION: Authentication window brought to foreground.")
                self.cooldown_ends = datetime.now() + timedelta(seconds=10) # Short cooldown
                return True
            else:
                logger.warning("REMEDIATION: Could not find auth window to focus.")
                return False
                
        except Exception as e:
            logger.error(f"REMEDIATION: Failed to focus window: {e}")
            return False

    def _handle_paused(self, duration: float) -> bool:
        """Handle long pauses."""
        # Warn if paused for > 2 hours
        if duration > 7200: # 2 hours
             # We trigger this only once per 'incident' effectively due to cooldown or we can just log
             # Cooldown handles frequency
             logger.warning(f"REMEDIATION: OneDrive has been PAUSED for {duration/3600:.1f} hours.")
             # Here we would send a specific alert if we had a direct notification mechanism
             # For now, logging it as a warning triggers the general Alerter if configured
             
             self.cooldown_ends = datetime.now() + timedelta(minutes=30) # Remind every 30 mins
             return True
        return False
