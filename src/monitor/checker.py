"""OneDrive Business status checker - Headless Mode (No Tooltips)."""

import logging
import winreg
import os
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import psutil
import win32api
import win32con

from src.shared.config import get_config
from src.shared.schemas import OneDriveStatus

logger = logging.getLogger(__name__)


class OneDriveChecker:
    """Check OneDrive for Business status via Process and File Attributes (Headless)."""

    def __init__(self) -> None:
        self.config = get_config()
        # tooltip_prefix is no longer used for detection, but kept in config if needed later
        
        # Active Check State
        self.log_path = Path(os.path.expandvars(self.config.monitor.log_path))
        self.canary_path = Path(self.config.target.folder) / self.config.monitor.canary_file
        self.last_log_mtime = 0.0
        self.last_canary_write_time = 0.0
        self.waiting_for_log_update = False
        self.stalled_detected = False  # Persist STALLED state
        self.stalled_since = 0.0

    def check_process(self) -> bool:
        """Check if OneDrive.exe is running."""
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == "onedrive.exe":
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def _get_shell_status_ps(self, file_path: Path) -> Optional[str]:
        """Query 'Availability status' (Col 305) via PowerShell Shell.Application.
        
        Args:
            file_path: Valid path to a file in OneDrive.
            
        Returns:
             Status string (e.g. 'Disponible en este dispositivo', 'Sincronizando') or None.
        """
        if not file_path.exists():
            return None
            
        try:
            # PowerShell command to get detail 305 specifically
            # We use -EncodedCommand ideally, but simple string is easier for now if no special chars
            ps_script = f"""
            $path = "{file_path.parent}"
            $name = "{file_path.name}"
            $shell = New-Object -ComObject Shell.Application
            $folder = $shell.Namespace($path)
            $item = $folder.ParseName($name)
            if ($item) {{ $folder.GetDetailsOf($item, 305) }}
            """
            
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                raw = result.stdout.strip()
                if raw:
                    logger.debug(f"PowerShell Status for {file_path.name}: '{raw}'")
                    return raw
            return None
        except Exception as e:
            logger.error(f"Error checking PowerShell status: {e}")
            return None

    def verify_registry_account(self) -> bool:
        """Verify the target account exists in registry."""
        try:
            accounts_path = r"Software\Microsoft\OneDrive\Accounts"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, accounts_path) as accounts_key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(accounts_key, i)
                        if subkey_name.startswith("Business"):
                            subkey_path = f"{accounts_path}\\{subkey_name}"
                            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey_path) as subkey:
                                try:
                                    user_email, _ = winreg.QueryValueEx(subkey, "UserEmail")
                                    user_folder, _ = winreg.QueryValueEx(subkey, "UserFolder")

                                    if user_email.lower() == self.config.target.email.lower():
                                        logger.info(f"Found matching account in registry: {user_email} -> {user_folder}")
                                        return True
                                except FileNotFoundError:
                                    pass
                        i += 1
                    except OSError:
                        break
            logger.warning(f"Account {self.config.target.email} not found in OneDrive registry")
            return False
        except Exception as e:
            logger.error(f"Error checking registry: {e}")
            return False

    def _check_canary_attributes_changed(self) -> bool:
        """Check if canary file attributes indicate it was processed by OneDrive (ReparsePoint)."""
        if not self.canary_path.exists():
            return False
        try:
            attrs = win32api.GetFileAttributes(str(self.canary_path))
            # FILE_ATTRIBUTE_REPARSE_POINT (0x400) is the standard indicator for Cloud Files
            is_reparse = bool(attrs & win32con.FILE_ATTRIBUTE_REPARSE_POINT)
            if is_reparse:
                logger.debug(f"Canary has REPARSE_POINT attribute ({attrs:X}). OneDrive alive.")
                return True
            return False
        except Exception as e:
            logger.debug(f"Error checking canary attributes: {e}")
            return False

    def _write_canary(self) -> bool:
        """Write timestamp to canary file."""
        try:
            logger.info(f"Active Check: Writing canary to {self.canary_path}")
            self.canary_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Clear attributes to ensure we can write (remove Hidden/ReadOnly if set)
            if self.canary_path.exists():
                try:
                    win32api.SetFileAttributes(str(self.canary_path), win32con.FILE_ATTRIBUTE_NORMAL)
                except Exception:
                    pass

            with open(self.canary_path, "w") as f:
                f.write(f"Monitor Verification: {datetime.now().isoformat()}")
            
            # Try to hide it again
            try:
                win32api.SetFileAttributes(str(self.canary_path), win32con.FILE_ATTRIBUTE_HIDDEN)
            except Exception:
                pass
                
            self.last_canary_write_time = time.time()
            return True
        except Exception as e:
            logger.error(f"Failed to write canary file: {e}")
            return False

    def active_liveness_check(self) -> tuple[OneDriveStatus, str]:
        """Perform active liveness check using Canary File + Attributes.
        
        Strategy (Active Polling):
        1. If Canary is Cloud (ReparsePoint) -> OK.
           - If verification too old (> 60s), 'Touch' file to force new sync.
        2. If Canary is Local (No Reparse) -> Check Age.
           - If age < timeout (60s) -> OK (Syncing).
           - If age > timeout -> PAUSED (Stalled).
        """
        current_time = time.time()
        
        # Ensure canary exists
        if not self.canary_path.exists():
            self._write_canary()
            return OneDriveStatus.OK, "Initializing (Canary Created)"

        # Check Attributes
        is_cloud = self._check_canary_attributes_changed()
        
        try:
             mtime = self.canary_path.stat().st_mtime
        except FileNotFoundError:
             self._write_canary()
             return OneDriveStatus.OK, "Initializing (Canary Missing)"

        age = current_time - mtime
        
        # PROBE_INTERVAL: How often to force a re-check (turn valid cloud file into local)
        PROBE_INTERVAL = 60 
        # SYNC_TIMEOUT: How long to wait for sync before declaring PAUSED
        SYNC_TIMEOUT = 60

        if is_cloud:
            # It is synced. Status is healthy.
            # But is it STALE?
            if age > PROBE_INTERVAL:
                # Force a new check by modifying the file
                logger.info(f"Active Check: Probing... (Canary age {age:.0f}s > {PROBE_INTERVAL}s)")
                self._write_canary() # This removes ReparsePoint, makes it local
                return OneDriveStatus.OK, "Active (Probing...)"
            
            return OneDriveStatus.OK, f"Active (Synced {age:.0f}s ago)"
        
        else:
            # It is Local (Not Synced yet)
            if age > SYNC_TIMEOUT:
                # It's been local for too long. Stalled.
                logger.warning(f"Active Check: Canary stalled for {age:.0f}s. OneDrive likely PAUSED.")
                
                # Check PowerShell as last resort confirmation?
                ps_status = self._get_shell_status_ps(self.canary_path)
                if ps_status:
                    valid = ["sincronizando", "syncing"] # "Disponible" is ambiguous if local
                    ps_lower = ps_status.lower()
                    
                    # If PS explicitly says Syncing, we trust it
                    if any(k in ps_lower for k in valid):
                        logger.info(f"Active Check: Recovered via PowerShell Status ('{ps_status}').")
                        return OneDriveStatus.OK, f"Active ({ps_status})"
                    
                    # If PS says "Disponible" but attributes say "Local", it is ambiguous.
                    # We stick to PAUSED because Attributes are lower-level truth for sync.

                return OneDriveStatus.PAUSED, f"Paused (Sync Pending > {SYNC_TIMEOUT}s)"
            
            # Still within grace period
            return OneDriveStatus.OK, f"Active (Syncing... {age:.0f}s)"

    def get_full_status(self) -> tuple[OneDriveStatus, bool, Optional[str]]:
        """Get complete OneDrive status (Headless)."""
        process_running = self.check_process()

        if not process_running:
            return OneDriveStatus.NOT_RUNNING, False, None

        # Active Liveness Check is now the PRIMARY source of truth
        status, msg = self.active_liveness_check()
        
        return status, process_running, msg
