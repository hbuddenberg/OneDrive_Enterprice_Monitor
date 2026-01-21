import logging
import smtplib
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.shared.config import get_config

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self):
        self.config = get_config().notifications

    def notify(self, subject: str, message: str, level: str = "WARNING"):
        """Send notification via all enabled channels."""
        if not self.config.enabled:
            return

        logger.info(f"NOTIFIER: Processing notification: {subject}")

        if self.config.channels.email.enabled:
            self._send_email(subject, message)
            
        if self.config.channels.teams.enabled:
            self._send_teams(subject, message, level)
            
        if self.config.channels.slack.enabled:
            self._send_slack(subject, message, level)

    def _send_email(self, subject: str, message: str):
        cfg = self.config.channels.email
        try:
            msg = MIMEMultipart()
            msg['From'] = cfg.sender_email
            msg['To'] = cfg.recipient_email
            msg['Subject'] = f"[OneDrive Monitor] {subject}"
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(cfg.smtp_server, cfg.smtp_port)
            server.starttls()
            server.login(cfg.sender_email, cfg.sender_password)
            text = msg.as_string()
            server.sendmail(cfg.sender_email, cfg.recipient_email, text)
            server.quit()
            logger.info("NOTIFIER: Email sent successfully.")
        except Exception as e:
            logger.error(f"NOTIFIER: Failed to send email: {e}")

    def _send_teams(self, subject: str, message: str, level: str):
        cfg = self.config.channels.teams
        try:
            color = "FF0000" if level == "ERROR" else "FFA500"
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": color,
                "summary": subject,
                "sections": [{
                    "activityTitle": subject,
                    "text": message
                }]
            }
            response = requests.post(cfg.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("NOTIFIER: Teams notification sent.")
            else:
                logger.error(f"NOTIFIER: Teams failed with {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"NOTIFIER: Failed to send Teams webhook: {e}")

    def _send_slack(self, subject: str, message: str, level: str):
        cfg = self.config.channels.slack
        try:
            icon = ":rotating_light:" if level == "ERROR" else ":warning:"
            payload = {
                "text": f"{icon} *{subject}*\n{message}"
            }
            response = requests.post(cfg.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("NOTIFIER: Slack notification sent.")
            else:
                logger.error(f"NOTIFIER: Slack failed with {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"NOTIFIER: Failed to send Slack webhook: {e}")
