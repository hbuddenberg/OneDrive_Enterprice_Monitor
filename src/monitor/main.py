"""OneDrive Business Monitor - Main entry point."""

import json
import logging
import sys
import tempfile
import time
import os
from datetime import datetime
from pathlib import Path

from src.monitor.alerter import Alerter
from src.monitor.checker import OneDriveChecker
from src.shared.config import get_config
from src.shared.schemas import OneDriveStatus, StatusReport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("monitor.log", encoding="utf-8"),
    ],
    encoding="utf-8" if os.name == "nt" else None
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

    status_path = Path(config.monitor.status_file)
    interval = config.monitor.check_interval_seconds

    logger.info("=" * 60)
    logger.info("OneDrive Business Monitor Starting")
    logger.info(f"Target Account: {config.target.email}")
    logger.info(f"Target Folder: {config.target.folder}")
    logger.info(f"Check Interval: {interval}s")
    logger.info(f"Status File: {status_path.absolute()}")
    logger.info(f"Alerting Enabled: {config.alerting.enabled}")
    logger.info("=" * 60)

    # Verify account exists in registry
    if checker.verify_registry_account():
        logger.info("✓ Account verified in Windows Registry")
    else:
        logger.warning("⚠ Account not found in registry - may not be configured")

    check_count = 0
    last_log_msg = ""

    while True:
        try:
            # Get current status
            status, process_running, status_detail = checker.get_full_status()

            # Build report
            report = StatusReport(
                timestamp=datetime.now(),
                account_email=config.target.email,
                account_folder=config.target.folder,
                status=status,
                status_detail=status_detail,
                process_running=process_running,
                message=_get_status_message(status),
            )

            # Log status (deduplicated)
            status_emoji = _get_status_emoji(status)
            current_log_msg = f"{status_emoji} Status: {status.value} | Detail: {status_detail}"
            
            if current_log_msg != last_log_msg or check_count % 20 == 0:
                logger.info(current_log_msg)
                last_log_msg = current_log_msg
            
            check_count += 1

            # Write to file
            write_status_atomic(report, status_path)

            # Send alert if needed
            alerter.send_alert(report)

        except Exception as e:
            logger.error(f"Error during status check: {e}", exc_info=True)

        # Wait for next check
        time.sleep(interval)


def _get_status_message(status: OneDriveStatus) -> str:
    """Get human-readable message for status."""
    messages = {
        OneDriveStatus.OK: "OneDrive is up to date",
        OneDriveStatus.SYNCING: "OneDrive is syncing files",
        OneDriveStatus.PAUSED: "OneDrive sync is paused",
        OneDriveStatus.AUTH_REQUIRED: "⚠️ OneDrive requires re-authentication! Please sign in.",
        OneDriveStatus.ERROR: "❌ OneDrive has encountered an error",
        OneDriveStatus.NOT_RUNNING: "OneDrive.exe is not running",
        OneDriveStatus.NOT_FOUND: "OneDrive Business icon not found in system tray",
    }
    return messages.get(status, "Unknown status")


def _get_status_emoji(status: OneDriveStatus) -> str:
    """Get emoji for status logging."""
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
