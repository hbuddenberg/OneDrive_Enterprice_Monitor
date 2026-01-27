"""Configuration loader for OneDrive Monitor."""

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel
import logging

# Initialize logger
logger = logging.getLogger("ValidationLogger")
logger.setLevel(logging.DEBUG)

class TargetConfig(BaseModel):
    """Target OneDrive account configuration."""

    email: str
    folder: str


class MonitorConfig(BaseModel):
    """Monitor settings."""

    check_interval_seconds: int = 60
    status_file: str = "./status.json"
    active_check_enabled: bool = True
    active_check_interval_seconds: int = 30
    active_check_timeout_seconds: int = 20
    log_path: str = "C:\\Users\\hansbuddenberg\\AppData\\Local\\Microsoft\\OneDrive\\logs\\Business1\\SyncDiagnostics.log"
    canary_file: str = ".monitor_canary"
    # If true, the monitor will fully restart OneDrive.exe on startup to avoid ghost states
    restart_on_startup: bool = False
    # How many seconds to wait after restarting OneDrive before proceeding
    restart_wait_seconds: int = 10


class SmtpConfig(BaseModel):
    """SMTP alerting configuration."""

    host: str
    port: int = 587
    user: str
    password_env: str  # Environment variable name for password
    to: list[str]


class WebhookConfig(BaseModel):
    """Webhook alerting configuration."""

    url: str


class AlertingConfig(BaseModel):
    """Alerting configuration."""

    enabled: bool = False
    smtp: Optional[SmtpConfig] = None
    webhook: Optional[WebhookConfig] = None


class DashboardConfig(BaseModel):
    """Dashboard settings."""

    host: str = "0.0.0.0"
    port: int = 8000



class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_server: str = ""
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""
    to_email: str = ""
    cc_email: Optional[str] = None
    bcc_email: Optional[str] = None

class TeamsConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""

class SlackConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""

class NotificationChannels(BaseModel):
    email: EmailConfig = EmailConfig()
    teams: TeamsConfig = TeamsConfig()
    slack: SlackConfig = SlackConfig()

class NotificationConfig(BaseModel):
    enabled: bool = True
    cooldown_minutes: int = 60
    failed_remediation_delay_seconds: int = 300
    channels: NotificationChannels = NotificationChannels()


class ValidationsConfig(BaseModel):
    """Validation toggles - enable/disable specific checks."""
    registry_check: bool = True
    process_check: bool = True
    log_check: bool = True
    canary_check: bool = True
    liveness_check: bool = True
    status_assignment: bool = True


class AppConfig(BaseModel):
    """Root application configuration."""

    target: TargetConfig
    monitor: MonitorConfig = MonitorConfig()
    alerting: AlertingConfig = AlertingConfig()
    notifications: NotificationConfig = NotificationConfig()
    dashboard: DashboardConfig = DashboardConfig()
    validations: ValidationsConfig = ValidationsConfig()



def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config.yaml. Defaults to ./config.yaml.

    Returns:
        Parsed AppConfig object.
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config.yaml"

    with open(config_path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    return AppConfig(**data)


# Singleton config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get or load the application configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config

# Add a method to check if a validation is enabled
def is_validation_enabled(validation_name: str) -> bool:
    """Check if a specific validation is enabled in the configuration.

    Args:
        validation_name: The name of the validation to check.

    Returns:
        True if the validation is enabled, False otherwise.
    """
    config = get_config()
    # Access the validations model directly using getattr for dynamic field access
    is_enabled = getattr(config.validations, validation_name, True)

    logger.debug(f"Validation '{validation_name}' enabled: {is_enabled}")
    return is_enabled

