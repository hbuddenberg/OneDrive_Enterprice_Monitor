

import logging
import subprocess
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from src.shared.schemas import OneDriveStatus
from src.shared.notifier import Notifier

from src.shared.notifier import get_notification_action
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
        # How long a bad status must persist before we act (per-state configuration)
        self.PERSISTENCE_BY_STATUS = {
            OneDriveStatus.NOT_RUNNING: 10,      # 10 seconds - critical, notify fast
            OneDriveStatus.AUTH_REQUIRED: 60,    # 60 seconds - needs user action
            OneDriveStatus.PAUSED: 90,           # 90 seconds - may auto-resume
            OneDriveStatus.ERROR: 30,            # 30 seconds
            OneDriveStatus.SYNCING: 45,          # 45 seconds (3 ciclos) - transient state
            OneDriveStatus.NOT_FOUND: 30,        # 30 seconds
        }
        self.DEFAULT_PERSISTENCE = 30  # Default for unlisted states

        # Notification Logic
        self.notifier = Notifier()
        self.last_remediation_time: Optional[datetime] = None
        self.notification_sent_for_incident: bool = False
        self.is_first_run: bool = True  # Para enviar OK al inicio vs RESOLVED después de incidente
        self.pre_syncing_status: Optional[OneDriveStatus] = None  # Estado antes de entrar a SYNCING

    def act(self, status: OneDriveStatus, outage_start_time: Optional[datetime] = None) -> bool:
        """Attempt to fix the current status if critical. Returns True if action taken."""
        now = datetime.now()

        # DEBUG: log current persistence tracking state for diagnosis
        logger.debug(f"ACT: now={now.isoformat()} | last_status={self.last_status} | status_first_seen={self.status_first_seen} | notification_sent={self.notification_sent_for_incident} | is_first_run={self.is_first_run}")

        # 1. Update Persistence Tracker & Immediate Notifications
        if status != self.last_status or self.is_first_run:
            prev = self.last_status.name if self.last_status else None
            curr = status.name
            
            # Rastrear estado pre-SYNCING
            if curr == "SYNCING" and prev != "SYNCING":
                # Guardamos el estado que había antes de entrar a SYNCING
                self.pre_syncing_status = prev
            elif curr != "SYNCING" and prev == "SYNCING":
                # Al salir de SYNCING, usamos el pre_syncing_status guardado
                pass  # Se usará self.pre_syncing_status en get_notification_action
            elif curr != "SYNCING":
                # Si no estamos en SYNCING, reseteamos el pre_syncing_status
                self.pre_syncing_status = None
            
            # Si ambos estados son SYNCING, no hacer nada CON NOTIFICACIONES pero SI continuar al timeout check
            if prev == "SYNCING" and curr == "SYNCING":
                logger.debug("STATE: SYNCING -> SYNCING | Skipping notification, but will check timeout.")
                # No hacemos return aquí - dejamos que continúe al check de timeout
            
            # Pasar pre_syncing_status a get_notification_action
            notify, tipo = get_notification_action(prev, curr, self.is_first_run, self.pre_syncing_status)
            logger.info(f"STATE CHANGE: {prev} -> {curr} | is_first_run={self.is_first_run} | pre_syncing={self.pre_syncing_status} | notification_sent={self.notification_sent_for_incident} | notify={notify} tipo={tipo}")

            # Definir time_in_state para los mensajes
            if hasattr(self, 'status_first_seen') and self.status_first_seen:
                time_in_state = (now - self.status_first_seen).total_seconds()
            else:
                time_in_state = 0

            if outage_start_time:
                timestamp_str = outage_start_time.strftime("%Y-%m-%d %H:%M:%S")
            elif self.status_first_seen:
                timestamp_str = self.status_first_seen.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

            if notify:
                try:
                    if tipo == "RESOLVED":
                        self.notifier.send_resolution_notification(timestamp_str, now.strftime("%Y-%m-%d %H:%M:%S"))
                        logger.info("RESOLVED: Sent resolution notification immediately.")
                        self.notification_sent_for_incident = False
                    elif tipo == "INCIDENTE":
                        self.notifier.send_status_notification(
                            status=status.value,
                            timestamp=timestamp_str,
                            message=f"Estado persistente detectado despues de {time_in_state:.0f}s"
                        )
                        logger.info(f"INCIDENTE: Sent notification for {status.value} after persistence ({time_in_state:.1f}s).")
                        self.notification_sent_for_incident = True
                        self.is_first_run = False
                    elif tipo == "SYNCING":
                        self.notifier.send_status_notification(
                            status=status.value,
                            timestamp=timestamp_str,
                            message=f"Sincronizando archivos despues de {time_in_state:.0f}s"
                        )
                        logger.info(f"SYNCING: Sent notification for {status.value} after persistence ({time_in_state:.1f}s).")
                        self.notification_sent_for_incident = True
                        self.is_first_run = False
                    elif tipo == "OK":
                        # Solo enviar OK si es primer arranque
                        if self.is_first_run:
                            self.notifier.send_status_notification(
                                status="OK",
                                timestamp=timestamp_str,
                                message="Sistema funcionando correctamente"
                            )
                            logger.info(f"OK: Sent OK notification after persistence ({time_in_state:.1f}s).")
                        self.notification_sent_for_incident = False
                        self.is_first_run = False
                except Exception as e:
                    logger.error(f"Failed to send status notification: {e}")

            self.last_status = status
            if outage_start_time and outage_start_time < now:
                self.status_first_seen = outage_start_time
            else:
                self.status_first_seen = now
            
            # CRITICAL: Check SYNCING timeout even on first run / state change
            # This ensures we catch prolonged SYNCING states that persist across restarts
            from src.shared.config import get_config
            config = get_config()
            syncing_timeout = config.monitor.syncing_restart_timeout_seconds
            
            # Recalculate time_in_state using outage_start_time (the actual sync pending time)
            if outage_start_time:
                actual_time_in_state = (now - outage_start_time).total_seconds()
            else:
                actual_time_in_state = time_in_state
            
            if status == OneDriveStatus.SYNCING and syncing_timeout > 0 and actual_time_in_state >= syncing_timeout:
                if not self._in_cooldown():
                    logger.warning(f"REMEDIATION: SYNCING state persisted for {actual_time_in_state:.0f}s (timeout: {syncing_timeout}s). Forcing restart.")
                    return self._force_restart_onedrive(status)
            
            return False
            
        # 2. Check Duration (per-state persistence time)
        time_in_state = (now - self.status_first_seen).total_seconds()
        required_persistence = self.PERSISTENCE_BY_STATUS.get(status, self.DEFAULT_PERSISTENCE)
        logger.debug(f"PERSISTENCE CHECK: status={status} | time_in_state={time_in_state:.1f}s | required={required_persistence}s | notified={self.notification_sent_for_incident}")
        if time_in_state < required_persistence:
            return False

        # PERSISTENCE REACHED - Status is confirmed

        # 3. Notify status change (if not yet notified)
        if not self.notification_sent_for_incident:
            timestamp_str = outage_start_time.strftime("%Y-%m-%d %H:%M:%S") if outage_start_time else self.status_first_seen.strftime("%Y-%m-%d %H:%M:%S")
            try:
                if status == OneDriveStatus.OK:
                    if self.is_first_run:
                        # Primer arranque con OK: enviar ok.html
                        self.notifier.send_status_notification(
                            status="OK",
                            timestamp=timestamp_str,
                            message="🚀 MONITOR INICIADO - Sistema funcionando correctamente"
                        )
                        logger.info(f"STARTUP: Sent OK notification after persistence ({time_in_state:.1f}s).")
                        self.is_first_run = False
                    # Si no es first_run y está OK, no enviamos nada (RESOLVED se envía en cambio de estado)
                else:
                    # Estado no-OK o SYNCING: enviar template correspondiente
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

        # 5. Act - Force Restart for critical states
        # NOT_RUNNING, AUTH_REQUIRED, PAUSED -> Restart immediately
        if status in [OneDriveStatus.NOT_RUNNING, OneDriveStatus.AUTH_REQUIRED, OneDriveStatus.PAUSED]:
            return self._force_restart_onedrive(status)
        
        # 6. SYNCING for too long -> Force Restart (configurable via syncing_restart_timeout_seconds)
        syncing_timeout = self.config.monitor.syncing_restart_timeout_seconds
        if status == OneDriveStatus.SYNCING and syncing_timeout > 0:
            if time_in_state >= syncing_timeout:
                logger.warning(f"REMEDIATION: SYNCING state persisted for {time_in_state:.0f}s (timeout: {syncing_timeout}s). Forcing restart.")
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
            # No enviar email de remediación omitida - solo log
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
