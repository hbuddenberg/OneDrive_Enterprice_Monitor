"""Alerting module for OneDrive Monitor."""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional

try:
    import urllib.request
    import json

    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

from src.shared.config import get_config
from src.shared.schemas import OneDriveStatus, StatusReport

logger = logging.getLogger(__name__)


class Alerter:
    """Send alerts via SMTP or webhook when critical status changes occur."""

    def __init__(self) -> None:
        self.config = get_config()
        self._last_alerted_status: Optional[OneDriveStatus] = None

    def should_alert(self, status: OneDriveStatus) -> bool:
        """Determine if an alert should be sent.

        Args:
            status: Current OneDrive status.

        Returns:
            True if alert should be sent.
        """
        if not self.config.alerting.enabled:
            return False

        # Only alert on critical statuses
        critical_statuses = {
            OneDriveStatus.AUTH_REQUIRED,
            OneDriveStatus.ERROR,
            OneDriveStatus.NOT_RUNNING,
        }

        if status not in critical_statuses:
            # Reset last alerted status when things are OK
            if status == OneDriveStatus.OK:
                self._last_alerted_status = None
            return False

        # Don't spam alerts for same status
        if status == self._last_alerted_status:
            return False

        return True

    def send_alert(self, report: StatusReport) -> bool:
        """Send alert for the given status report.

        Args:
            report: The status report to alert about.

        Returns:
            True if alert was sent successfully.
        """
        if not self.should_alert(OneDriveStatus(report.status)):
            return False

        success = False

        # Try SMTP
        if self.config.alerting.smtp:
            success = self._send_smtp_alert(report) or success

        # Try Webhook
        if self.config.alerting.webhook:
            success = self._send_webhook_alert(report) or success

        if success:
            self._last_alerted_status = OneDriveStatus(report.status)

        return success

    def _send_smtp_alert(self, report: StatusReport) -> bool:
        """Send alert via SMTP email."""
        try:
            smtp_config = self.config.alerting.smtp
            if not smtp_config:
                return False

            # Get password from environment
            password = os.environ.get(smtp_config.password_env, "")
            if not password:
                logger.error(
                    f"SMTP password not found in env var: {smtp_config.password_env}"
                )
                return False

            subject = f"[Alerta OneDrive] {report.status} - {report.account_email}"
            body = f"""Alerta del Monitor OneDrive Empresarial

Estado: {report.status}
Cuenta: {report.account_email}
Carpeta: {report.account_folder}
Hora: {report.timestamp}

Tooltip: {report.tooltip_text or 'N/A'}
Mensaje: {report.message or 'N/A'}

---
Esta es una alerta automática del Monitor OneDrive Empresarial.
"""

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = smtp_config.user
            msg["To"] = ", ".join(smtp_config.to)

            with smtplib.SMTP(smtp_config.host, smtp_config.port) as server:
                server.starttls()
                server.login(smtp_config.user, password)
                server.sendmail(smtp_config.user, smtp_config.to, msg.as_string())

            logger.info(f"SMTP alert sent to {smtp_config.to}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMTP alert: {e}")
            return False

    def _send_webhook_alert(self, report: StatusReport) -> bool:
        """Send alert via webhook (e.g., Slack, Teams)."""
        if not HAS_URLLIB:
            logger.error("urllib not available for webhook")
            return False

        try:
            webhook_config = self.config.alerting.webhook
            if not webhook_config:
                return False

            payload = {
                "text": f"🚨 Alerta OneDrive: {report.status}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Alerta del Monitor OneDrive Empresarial*\n\n"
                            f"*Estado:* `{report.status}`\n"
                            f"*Cuenta:* {report.account_email}\n"
                            f"*Hora:* {report.timestamp}\n"
                            f"*Tooltip:* {report.tooltip_text or 'N/A'}",
                        },
                    }
                ],
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_config.url,
                data=data,
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.info("Webhook alert sent successfully")
                    return True
                else:
                    logger.error(f"Webhook returned status {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False
