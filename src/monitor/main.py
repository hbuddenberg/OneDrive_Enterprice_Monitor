"""OneDrive Business Monitor - Main entry point."""

import json
import logging
import sys
import tempfile
import time
import os
from datetime import datetime
from pathlib import Path

# Fix module search path when running script directly
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.monitor.alerter import Alerter
from src.monitor.checker import OneDriveChecker
from src.shared.config import get_config
from src.shared.schemas import OneDriveStatus, StatusReport

# Configure logging
# Force UTF-8 for stdout/stderr to handle emojis on Windows
if os.name == "nt":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("monitor.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


def write_status_atomic(report: StatusReport, path: Path) -> None:
    """Write status report to file atomically.

    Uses write-to-temp-then-rename to avoid partial reads.

    Args:
        report: The status report to write.
        path: The target file path.
    """
    # Write to temp file first
    temp_fd, temp_path = tempfile.mkstemp(suffix=".json", dir=path.parent)
    try:
        with open(temp_fd, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(mode="json"), f, indent=2, default=str)

        # Atomic rename (works on same filesystem)
        Path(temp_path).replace(path)
        logger.debug(f"Status written to {path}")
    except Exception as e:
        # Clean up temp file on error
        try:
            Path(temp_path).unlink()
        except Exception:
            pass
        raise e


def run_monitor() -> None:
    """Run the OneDrive monitor loop."""
    config = get_config()
    checker = OneDriveChecker()
    alerter = Alerter()
    from src.monitor.remediator import RemediationAction
    remediator = RemediationAction()

    status_path = Path(config.monitor.status_file)
    interval = config.monitor.check_interval_seconds

    logger.info("=" * 60)
    logger.info("Monitor OneDrive Empresarial Iniciando")
    logger.info(f"Cuenta Objetivo: {config.target.email}")
    logger.info(f"Carpeta Objetivo: {config.target.folder}")
    logger.info(f"Intervalo de Verificación: {interval}s")
    logger.info(f"Archivo de Estado: {status_path.absolute()}")
    logger.info(f"Alertas Habilitadas: {config.alerting.enabled}")
    logger.info("=" * 60)

    # Verificar que la cuenta existe en el registro
    if checker.verify_registry_account():
        logger.info("✓ Cuenta verificada en el Registro de Windows")
    else:
        logger.warning("⚠ Cuenta no encontrada en el registro - puede no estar configurada")

    # Inicializar BD
    from src.shared.database import init_db, log_status, get_outage_start_time
    init_db()
    
    # Escribir Estado Inicial (Mitigación para archivos vacíos/corruptos)
    logger.info("Inicializando archivo de estado...")
    initial_report = StatusReport(
        timestamp=datetime.now(),
        account_email=config.target.email,
        account_folder=config.target.folder,
        status=OneDriveStatus.NOT_RUNNING,
        status_detail="Inicializando...",
        process_running=False,
        message="Monitor iniciando..."
    )
    write_status_atomic(initial_report, status_path)
    
    check_count = 0
    last_log_msg = ""
    
    last_db_status = None
    last_db_time = 0.0
    HEARTBEAT_INTERVAL = 300 # 5 minutes
    

    out_of_sync_since_ts = None

    while True:
        try:
            # Get current status
            status, process_running, status_detail = checker.get_full_status()
            
            # Track Out-of-Sync Start Time
            if status == OneDriveStatus.OK:
                out_of_sync_since_ts = None
            else:
                 if out_of_sync_since_ts is None:
                     # Try to recover start time from DB history
                     db_start = get_outage_start_time()
                     if db_start:
                         out_of_sync_since_ts = db_start
                     else:
                         out_of_sync_since_ts = datetime.now()

            # Build report
            report = StatusReport(
                timestamp=datetime.now(),
                account_email=config.target.email,
                account_folder=config.target.folder,
                status=status,
                status_detail=status_detail,
                process_running=process_running,
                message=_get_status_message(status),
                out_of_sync_since=out_of_sync_since_ts
            )

            # Log status (deduplicated)
            status_emoji = _get_status_emoji(status)
            current_log_msg = f"{status_emoji} Status: {status.value} | Detail: {status_detail}"
            
            if current_log_msg != last_log_msg or check_count % 20 == 0:
                logger.info(current_log_msg)
                last_log_msg = current_log_msg
            
            check_count += 1

            # --- Database Logging ---
            current_time = time.time()
            is_change = (status != last_db_status)
            
            if is_change or (current_time - last_db_time > HEARTBEAT_INTERVAL):
                # Ensure we capture detail if present, or just status value
                db_msg = status_detail if status_detail else status.value
                log_status(status.value, db_msg, is_change)
                last_db_time = current_time
                last_db_status = status
                if is_change:
                     logger.debug("DB: Status change stored.")
                else:
                     logger.debug("DB: Heartbeat stored.")
            # ------------------------

            # Write to file
            write_status_atomic(report, status_path)

            # Send alert if needed
            alerter.send_alert(report)

            # --- Remediation (Auto-Healing) ---
            remediator.act(status, outage_start_time=out_of_sync_since_ts)
            # ----------------------------------

        except Exception as e:
            logger.error(f"Error during status check: {e}", exc_info=True)

        # Wait for next check
        time.sleep(interval)


def _get_status_message(status: OneDriveStatus) -> str:
    """Obtiene mensaje legible para el estado."""
    messages = {
        OneDriveStatus.OK: "OneDrive está actualizado",
        OneDriveStatus.SYNCING: "OneDrive está sincronizando archivos",
        OneDriveStatus.PAUSED: "La sincronización de OneDrive está pausada",
        OneDriveStatus.AUTH_REQUIRED: "⚠️ ¡OneDrive requiere re-autenticación! Por favor inicie sesión.",
        OneDriveStatus.ERROR: "❌ OneDrive ha encontrado un error",
        OneDriveStatus.NOT_RUNNING: "OneDrive.exe no está ejecutándose",
        OneDriveStatus.NOT_FOUND: "Icono de OneDrive Empresarial no encontrado en la bandeja del sistema",
    }
    return messages.get(status, "Estado desconocido")


def _get_status_emoji(status: OneDriveStatus) -> str:
    """Obtiene emoji para el logging de estado."""
    emojis = {
        OneDriveStatus.OK: "✅",
        OneDriveStatus.SYNCING: "🔄",
        OneDriveStatus.PAUSED: "⏸️",
        OneDriveStatus.AUTH_REQUIRED: "🔐",
        OneDriveStatus.ERROR: "❌",
        OneDriveStatus.NOT_RUNNING: "💀",
        OneDriveStatus.NOT_FOUND: "🔍",
    }
    return emojis.get(status, "❓")


if __name__ == "__main__":
    try:
        run_monitor()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
        sys.exit(0)
