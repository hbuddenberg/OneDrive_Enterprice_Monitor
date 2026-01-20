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
            
            # EARLY DETECTION: Don't wait 60s if we can know NOW that it is paused.
            # Query PowerShell immediately if we are in the "Waiting" phase.
            ps_status = self._get_shell_status_ps(self.canary_path)
            if ps_status:
                ps_lower = ps_status.lower()
                
                # 1. Check for explicit PAUSE or ERROR
                paused_keywords = ["pausado", "paused", "detenido", "stopped", "error", "fallo", "failed", "atencion", "attention"]
                if any(k in ps_lower for k in paused_keywords):
                    logger.warning(f"Active Check: Early Detection! PowerShell says '{ps_status}'. Declaring PAUSED/ERROR.")
                    return OneDriveStatus.PAUSED, f"Paused/Error ({ps_status})"

                # 2. Check for explicit SYNC (Confirmation to keep waiting)
                sync_keywords = ["sincronizando", "syncing", "procesando", "processing", "comprobando", "checking", "cargando", "uploading", "descargando", "downloading", "pendiente", "pending"]
                if any(k in ps_lower for k in sync_keywords):
                     status_detail = f"Active (Syncing... {age:.0f}s)"
                     
                     # Check if we have been syncing for too long
                     if age > SYNC_TIMEOUT:
                         if self.check_auth_window():
                             return OneDriveStatus.AUTH_REQUIRED, "Authentication Required (Window Detected)"
                         
                         # Heuristic: If stuck in "Pending" for > SYNC_TIMEOUT, it's likely Auth Required
                         # especially if "pendiente" is the status.
                         if "pendiente" in ps_lower or "pending" in ps_lower:
                             logger.warning(f"Active Check: Stuck in 'Pending' for {age:.0f}s. Assuming Auth Required.")
                             return OneDriveStatus.AUTH_REQUIRED, f"Auth Required (Stuck in Pending > {SYNC_TIMEOUT}s)"
                         
                         return OneDriveStatus.PAUSED, f"Stalled (Syncing > {SYNC_TIMEOUT}s)"
                     
                     if self.check_auth_window():
                         return OneDriveStatus.AUTH_REQUIRED, "Authentication Required (Window Detected)"
                     
                     return OneDriveStatus.OK, status_detail

                # 3. Check for explicit AVAILABLE (Local but Synced)
                available_keywords = ["disponible", "available", "ok", "listo", "ready"]
                if any(k in ps_lower for k in available_keywords):
                     # It is Synced (Local). Check if we need to re-probe.
                     if age > PROBE_INTERVAL:
                         logger.info(f"Active Check: Probing 'Available' file... (Canary age {age:.0f}s > {PROBE_INTERVAL}s)")
                         self._write_canary()
                         return OneDriveStatus.OK, "Active (Probing...)"
                     return OneDriveStatus.OK, f"Active (Local & Synced {age:.0f}s)"

            # If no explicit Pause or Sync/Available detected, use the Timeout mechanism as safety net
            if age > SYNC_TIMEOUT:
                # If stalled, check for Auth Window before declaring PAUSED
                if self.check_auth_window():
                     return OneDriveStatus.AUTH_REQUIRED, "Authentication Required (Window Detected)"
            
                logger.warning(f"Active Check: Canary stalled for {age:.0f}s. PowerShell: '{ps_status}'. OneDrive likely PAUSED.")
                return OneDriveStatus.PAUSED, f"Paused (Sync Pending > {SYNC_TIMEOUT}s)"
            
            # Still within grace period
            return OneDriveStatus.OK, f"Active (Syncing... {age:.0f}s)"

    def check_auth_window(self) -> bool:
        """Check if a OneDrive authentication window is present."""
        try:
            # Look for typical Sign In window titles
            cmd = "Get-Process | Where-Object { $_.MainWindowTitle -match 'Sign in|Iniciar sesión|Microsoft OneDrive|Contraseña|Password' } | Select-Object -ExpandProperty MainWindowTitle"
            
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                titles = result.stdout.strip().split('\n')
                # Filter out empty strings and check if we have any matches
                msg = [t.strip() for t in titles if t.strip()]
                if msg:
                     logger.warning(f"Auth Window Detected: {msg}")
                     return True
            return False
        except Exception as e:
            logger.error(f"Error checking auth window: {e}")
            return False

    def get_full_status(self) -> tuple[OneDriveStatus, bool, Optional[str]]:
        """Get complete OneDrive status (Headless)."""
        
        # 0. Check if account is still configured (Registry Check)
        # This detects if the user has logged out (Registry key removed)
        if not self.verify_registry_account():
            return OneDriveStatus.NOT_FOUND, False, "Account Config Missing (Logged Out)"

        process_running = self.check_process()

        if not process_running:
            return OneDriveStatus.NOT_RUNNING, False, None

        # Process IS running, but is it OUR process?
        # If the target log file hasn't updated in > 5 minutes, assume our instance is dead/killed
        # (even if another OneDrive.exe is running).
        # Note: OneDrive updates logs even when Paused, so a dead log means a dead app.
        try:
             # Check log mtime
             if self.log_path.exists():
                 log_mtime = self.log_path.stat().st_mtime
                 log_age = time.time() - log_mtime
                 if log_age > 3600: # 1 hour (was 5 mins)
                     logger.warning(f"Process found but Log is stale ({log_age:.0f}s > 3600s). Proceeding anyway.")
                     # return OneDriveStatus.NOT_RUNNING, False, "Process ghost / Instance killed"
        except Exception as e:
             logger.warning(f"Could not verify log age: {e}")

        # Active Liveness Check is now the PRIMARY source of truth
        status, msg = self.active_liveness_check()
        
        return status, process_running, msg
