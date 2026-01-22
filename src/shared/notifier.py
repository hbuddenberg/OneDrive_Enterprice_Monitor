import logging
import smtplib
import json
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.shared.config import get_config

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self):
        self.config = get_config().notifications

    def send_error_notification(self, status: str, outage_start_time: str = None) -> None:
        """Send a notification about a critical error."""
        subject = f"🚨 ERROR: OneDrive Monitor - {status}"
        
        start_time_str = f"Since: {outage_start_time}" if outage_start_time else "Time: Unknown"
        
        # Email Template
        email_body = f"""
        <html>
            <body>
                <h2 style="color: #d9534f;">OneDrive Critical Alert</h2>
                <p><strong>Status:</strong> {status}</p>
                <p><strong>{start_time_str}</strong></p>
                <p>Monitor has attempted auto-remediation but the issue persists.</p>
                <hr>
                <p><em>OneDrive Enterprise Monitor</em></p>
            </body>
        </html>
        """
        
        # Plain text for others
        message = f"🚨 ERROR: OneDrive is {status}. {start_time_str}. Remediation failed."
        
        # We manually call notify to pass the HTML
        self.notify(subject, message, level="ERROR", email_html=email_body)

    def send_resolution_notification(self, outage_start_time: str = None, outage_end_time: str = None) -> None:
        """Send a notification that the issue has been resolved."""
        subject = "✅ RESOLVED: OneDrive Monitor - System OK"
        
        start_msg = f"Outage Start: {outage_start_time}" if outage_start_time else ""
        end_msg = f"Recovered At: {outage_end_time}" if outage_end_time else ""
        
        email_body = f"""
        <html>
            <body>
                <h2 style="color: #5cb85c;">System Recovered</h2>
                <p>OneDrive status is back to <strong>OK</strong>.</p>
                <p>{start_msg}</p>
                <p>{end_msg}</p>
                <hr>
                <p><em>OneDrive Enterprise Monitor</em></p>
            </body>
        </html>
        """
        
        message = f"✅ RESOLVED: OneDrive is back online. {start_msg} - {end_msg}"
        
        self.notify(subject, message, level="INFO", email_html=email_body)

    def notify(self, subject: str, message: str, level: str = "WARNING", email_html: str = None):
        """Send notification via all enabled channels."""
        if not self.config.enabled:
            return

        if self._in_cooldown():
            logger.info("Notification suppressed due to cooldown.")
            return

        logger.info(f"NOTIFIER: Processing notification: {subject}")

        if self.config.channels.email.enabled:
            self._send_email(subject, email_html if email_html else message, is_html=bool(email_html))
            
        if self.config.channels.teams.enabled:
            self._send_teams(subject, message, level)
            
        if self.config.channels.slack.enabled:
            self._send_slack(subject, message, level)

    def _send_email(self, subject: str, body: str, is_html: bool = False):
        cfg = self.config.channels.email
        try:
            msg = MIMEMultipart()
            msg['From'] = cfg.sender_email
            msg['To'] = cfg.to_email
            msg['Subject'] = f"[OneDrive Monitor] {subject}"
            
            # Helper to parse list from comma-separated string or list
            def parse_recipients(val):
                if not val:
                    return []
                if isinstance(val, list):
                    return val
                return [e.strip() for e in val.split(',') if e.strip()]

            # Handle CC
            cc_addrs = parse_recipients(cfg.cc_email)
            if cc_addrs:
                msg['Cc'] = ", ".join(cc_addrs)
            
            # Handle BCC
            bcc_addrs = parse_recipients(cfg.bcc_email)

            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Combine all recipients for envelope
            to_addrs = parse_recipients(cfg.to_email)
            all_recipients = to_addrs + cc_addrs + bcc_addrs

            server = smtplib.SMTP(cfg.smtp_server, cfg.smtp_port)
            server.starttls()
            server.login(cfg.sender_email, cfg.sender_password)
            text = msg.as_string()
            server.sendmail(cfg.sender_email, all_recipients, text)
            server.quit()
            
            log_msg = f"Email sent to {cfg.to_email}"
            if cc_addrs:
                log_msg += f" (CC: {len(cc_addrs)})"
            if bcc_addrs:
                log_msg += f" (BCC: {len(bcc_addrs)})"
            logger.info(f"NOTIFIER: {log_msg}")

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
            response = httpx.post(cfg.webhook_url, json=payload, timeout=10)
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
            response = httpx.post(cfg.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("NOTIFIER: Slack notification sent.")
            else:
                logger.error(f"NOTIFIER: Slack failed with {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"NOTIFIER: Failed to send Slack webhook: {e}")
