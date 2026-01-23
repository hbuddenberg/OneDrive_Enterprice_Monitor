"""Pydantic schemas for OneDrive Monitor."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class OneDriveStatus(str, Enum):
    """Possible OneDrive sync statuses."""

    OK = "OK"  # Up to date
    SYNCING = "SYNCING"  # Currently syncing
    PAUSED = "PAUSED"  # Sync paused
    AUTH_REQUIRED = "AUTH_REQUIRED"  # Re-authentication needed (critical!)
    ERROR = "ERROR"  # Sync error
    NOT_RUNNING = "NOT_RUNNING"  # OneDrive.exe not running
    NOT_FOUND = "NOT_FOUND"  # Target account icon not found in tray
    UNKNOWN = "UNKNOWN"  # Unknown/unrecognized status


class StatusReport(BaseModel):
    """Status report written to status.json."""

    timestamp: datetime
    account_email: str
    account_folder: str
    status: OneDriveStatus
    status_detail: Optional[str] = None
    process_running: bool
    message: Optional[str] = None
    out_of_sync_since: Optional[datetime] = None

    class Config:
        use_enum_values = True
