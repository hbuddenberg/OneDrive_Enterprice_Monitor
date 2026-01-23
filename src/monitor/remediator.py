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
        self.is_first_run: bool = True  # Para enviar OK al inicio vs RESOLVED después de incidente

    def act(self, status: OneDriveStatus, outage_start_time: Optional[datetime] = None) -> bool:
        """Attempt to fix the current status if critical. Returns True if action taken."""
        now = datetime.now()
        
        # 1. Update Persistence Tracker & Immediate Notifications
        if status != self.last_status:
            # Check for resolution (state changed to OK)
            if status == OneDriveStatus.OK:
                # Solo enviar RESOLVED si hubo un incidente previo (no en el primer arranque)
                if self.notification_sent_for_incident and not self.is_first_run:
                    outage_str = outage_start_time.strftime("%Y-%m-%d %H:%M:%S") if outage_start_time else "Unknown"
                    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        self.notifier.send_resolution_notification(outage_str, now_str)
                        logger.info("RESOLUTION: Sent resolution notification immediately.")
                    except Exception as e:
                        logger.error(f"Failed to send resolution notification: {e}")
                    self.notification_sent_for_incident = False
                self.reset_counters()

            # Check for NEW critical state
            # (We wait for persistence in Step 2 to notify)
            pass

            self.last_status = status
            
            # If we have a historical outage time (e.g. from DB on startup), use it
            if outage_start_time and outage_start_time < now:
                 self.status_first_seen = outage_start_time
                 # If we just started up and found historical error, ensure we marked it as notified?
                 # logic above handles "last_status is None" -> Notify.
            else:
                 self.status_first_seen = now
            # self.notification_sent_for_incident = False # KEEP IT TRUE if we are just flapping between bad states? 
            # No, if status changes (e.g. Pause -> Auth), it's a new "incident" type? 
            # Or should we treat it as one continuous outage?
            # User wants "Resolution" when it goes to OK.
            # If we go Error A -> Error B -> OK.
            # We sent Error A. 
            # If we reset here, we might send Error B.
            # If we don't reset, we won't send Error B (assuming check checks flag).
            
            # Let's reset on OK only mainly. But if we change error type, we probably want to notify again eventually?
            # For simplicity, if status changes to anything other than OK, we reset the flag?
            # If we go Error A (Notified) -> Error B. Should we notify Error B? Yes.
            # Counter reset is now handled above.
            pass
            
            return False
            
        # 2. Check Duration
        time_in_state = (now - self.status_first_seen).total_seconds()
        if time_in_state < self.REQUIRED_PERSISTENCE:
            return False

        # PERSISTENCE REACHED - Status is confirmed

        # 3. Notify status change (if not yet notified)
        if not self.notification_sent_for_incident:
            timestamp_str = outage_start_time.strftime("%Y-%m-%d %H:%M:%S") if outage_start_time else self.status_first_seen.strftime("%Y-%m-%d %H:%M:%S")
            try:
                if status == OneDriveStatus.OK:
                    if self.is_first_run:
                        # Primer arranque con OK → enviar ok.html
                        self.notifier.send_status_notification(
                            status="OK",
                            timestamp=timestamp_str,
                            message="🚀 MONITOR INICIADO - Sistema funcionando correctamente"
                        )
                        logger.info(f"STARTUP: Sent OK notification after persistence ({time_in_state:.1f}s).")
                        self.is_first_run = False
                    # Si no es first_run y está OK, no enviamos nada (RESOLVED se envía en cambio de estado)
                else:
                    # Estado no-OK → enviar template correspondiente
                    self.notifier.send_status_notification(
                        status=status.value,
                        timestamp=timestamp_str,
                        message=f"Estado persistente detectado después de {time_in_state:.0f}s"
                    )
                    logger.info(f"ALERT: Sent notification for {status.value} after persistence ({time_in_state:.1f}s).")
                    self.is_first_run = False  # Ya no es primer arranque
                self.notification_sent_for_incident = True
            except Exception as e:
                logger.error(f"Failed to send status notification: {e}")

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
                     
                     start_str = outage_start_time.strftime("%Y-%m-%d %H:%M:%S") if outage_start_time else "Unknown"
                     self.notifier.send_error_notification(status.value, start_str)
                     
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
            self.notifier.notify("Remediación Omitida", "Se alcanzó el máximo de reinicios por hora. Se requiere intervención manual.", "ERROR")
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
            self.notifier.notify("Error de Remediación", "No se encontró el binario de OneDrive para reiniciar.", "ERROR")
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
            self.notifier.notify("Error de Remediación", f"Error al iniciar OneDrive: {e}", "ERROR")
            return False
