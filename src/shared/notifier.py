# --- Lógica de notificación centralizada (tabla del usuario) ---
INCIDENT_STATES = {"NOT_RUNNING", "ERROR", "PAUSED", "AUTH_REQUIRED", "NOT_FOUND"}
SYNCING_STATE = "SYNCING"
OK_STATE = "OK"


# Devuelve una lista de (enviar, tipo) para soportar transiciones múltiples (ej: INCIDENTE->SYNCING debe enviar RESOLVED y luego SYNCING)
def get_notification_action(prev, curr, is_first_run):
    # No notificar si SYNCING -> SYNCING
    if prev == SYNCING_STATE and curr == SYNCING_STATE:
        return (False, None)
    actions = []
    # 1. Siempre que el estado actual sea INCIDENTE, enviar INCIDENTE
    if curr == "INCIDENTE" or (curr in INCIDENT_STATES and (prev is None or prev not in INCIDENT_STATES)):
        actions.append((True, "INCIDENTE"))
        return actions[0] if len(actions) == 1 else actions

    # 3. INCIDENTE -> SYNCING: enviar RESOLVED y luego SYNCING
    if (prev == "INCIDENTE" or prev in INCIDENT_STATES) and curr == SYNCING_STATE:
        actions.append((True, "RESOLVED"))
        actions.append((True, "SYNCING"))
        return actions

    # 2. INCIDENTE -> OK: enviar RESOLVED
    if (prev == "INCIDENTE" or prev in INCIDENT_STATES) and curr == OK_STATE:
        actions.append((True, "RESOLVED"))
        return actions[0] if len(actions) == 1 else actions

    # 4. OK -> SYNCING: enviar SYNCING
    # 4. OK -> SYNCING: evitar notificar inmediatamente para reducir flapping.
    #    Dejar que la rama de persistencia en `remediator` envíe la notificación
    #    después de que el estado se mantenga el tiempo configurado.

    # 5. SYNCING -> OK: enviar OK
    if prev == SYNCING_STATE and curr == OK_STATE:
        actions.append((True, "OK"))
        return actions[0]

    # 6. Primer arranque en OK
    if is_first_run and curr == OK_STATE:
        actions.append((True, "OK"))
        return actions[0]

    # 7. OK -> OK, RESOLVED -> OK, OK -> RESOLVED: no enviar
    return (False, None)
"""Notification module for OneDrive Monitor.

Sends notifications via email, Teams, and Slack when status changes occur.
"""

import logging
import smtplib
import httpx
from datetime import datetime, timedelta
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.shared.config import get_config
from src.shared.templates import render_status_notification, render_resolution_notification

logger = logging.getLogger(__name__)


class Notifier:
    """Handles sending notifications through multiple channels."""
    
    def __init__(self):
        self.config = get_config().notifications
        self._account = get_config().target.email
        self._last_notification_time: Optional[datetime] = None

    def _in_cooldown(self) -> bool:
        """Check if we're still in notification cooldown period."""
        cooldown_minutes = self.config.cooldown_minutes
        
        # Si cooldown es 0, nunca hay cooldown
        if cooldown_minutes <= 0:
            return False
            
        if self._last_notification_time is None:
            return False
        
        cooldown_ends = self._last_notification_time + timedelta(minutes=cooldown_minutes)
        
        if datetime.now() < cooldown_ends:
            remaining = (cooldown_ends - datetime.now()).seconds // 60
            logger.debug(f"NOTIFIER: In cooldown, {remaining} minutes remaining")
            return True
        return False

    def _update_cooldown(self):
        """Update the last notification time."""
        self._last_notification_time = datetime.now()

    def send_status_notification(self, status: str, timestamp: str = None, message: str = "") -> None:
        """Send a notification for a status change.
        
        Args:
            status: The OneDrive status (AUTH_REQUIRED, ERROR, NOT_RUNNING, etc.)
            timestamp: When the status occurred
            message: Additional context message
        """
        # Determine notification level based on status
        critical_statuses = {"AUTH_REQUIRED", "ERROR", "NOT_RUNNING"}
        warning_statuses = {"PAUSED", "NOT_FOUND"}
        
        if status.upper() in critical_statuses:
            level = "ERROR"
            emoji = "🚨"
        elif status.upper() in warning_statuses:
            level = "WARNING"
            emoji = "⚠️"
        else:
            level = "INFO"
            emoji = "ℹ️"
        
        subject = f"{emoji} Monitor OneDrive - {status}"
        
        # Render HTML template
        email_html = render_status_notification(
            status=status,
            account=self._account,
            timestamp=timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            message=message
        )
        
        # Plain text for webhooks
        plain_message = f"{emoji} Estado OneDrive: {status}. Cuenta: {self._account}. {message}"
        
        self.notify(subject, plain_message, level=level, email_html=email_html)

    def send_error_notification(self, status: str, outage_start_time: str = None) -> None:
        """Envía una notificación sobre un error crítico.
        
        Args:
            status: El estado de error
            outage_start_time: Cuándo comenzó el problema
        """
        self.send_status_notification(
            status=status,
            timestamp=outage_start_time,
            message="Se intentó auto-remediación pero el problema persiste."
        )

    def send_resolution_notification(self, outage_start_time: str = None, outage_end_time: str = None) -> None:
        """Envía una notificación de que el problema ha sido resuelto.
        
        Args:
            outage_start_time: Cuándo comenzó la interrupción
            outage_end_time: Cuándo se restauró el servicio
        """
        subject = "✅ RESUELTO: Monitor OneDrive - Sistema OK"
        
        start_time = outage_start_time or "Desconocido"
        end_time = outage_end_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate duration
        duration = self._calculate_duration(outage_start_time, outage_end_time)
        
        # Render HTML template
        email_html = render_resolution_notification(
            account=self._account,
            outage_start=start_time,
            outage_end=end_time,
            duration=duration
        )
        
        # Plain text for webhooks
        plain_message = f"✅ OneDrive está de vuelta en línea. Interrupción: {start_time} - {end_time} ({duration})"
        
        self.notify(subject, plain_message, level="INFO", email_html=email_html)

    def _calculate_duration(self, start: str, end: str) -> str:
        """Calculate human-readable duration between two timestamps."""
        if not start or not end:
            return "N/A"
        
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            delta = end_dt - start_dt
            
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if delta.days > 0:
                return f"{delta.days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m {seconds}s"
        except Exception:
            return "N/A"

    def notify(self, subject: str, message: str, level: str = "WARNING", email_html: str = None):
        """Send notification via all enabled channels.
        
        Args:
            subject: Notification subject
            message: Plain text message (for webhooks)
            level: Severity level (ERROR, WARNING, INFO)
            email_html: Optional HTML content for email
        """
        if not self.config.enabled:
            logger.debug("NOTIFIER: Notifications disabled in config")
            return

        if self._in_cooldown():
            logger.info("NOTIFIER: Notification suppressed due to cooldown.")
            return

        logger.info(f"NOTIFIER: Processing notification: {subject}")
        success = False

        if self.config.channels.email.enabled:
            if self._send_email(subject, email_html if email_html else message, is_html=bool(email_html)):
                success = True
            
        if self.config.channels.teams.enabled:
            if self._send_teams(subject, message, level):
                success = True
            
        if self.config.channels.slack.enabled:
            if self._send_slack(subject, message, level):
                success = True

        # Update cooldown only if at least one notification was sent
        if success:
            self._update_cooldown()

    def _send_email(self, subject: str, body: str, is_html: bool = False) -> bool:
        """Envía notificación por email."""
        cfg = self.config.channels.email
        try:
            msg = MIMEMultipart()
            msg['From'] = cfg.sender_email
            msg['To'] = cfg.to_email
            msg['Subject'] = f"[Monitor OneDrive] {subject}"
            
            def parse_recipients(val):
                if not val:
                    return []
                if isinstance(val, list):
                    return val
                return [e.strip() for e in val.split(',') if e.strip()]

            cc_addrs = parse_recipients(cfg.cc_email)
            if cc_addrs:
                msg['Cc'] = ", ".join(cc_addrs)
            
            bcc_addrs = parse_recipients(cfg.bcc_email)

            if is_html:
                msg.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            to_addrs = parse_recipients(cfg.to_email)
            all_recipients = to_addrs + cc_addrs + bcc_addrs

            server = smtplib.SMTP(cfg.smtp_server, cfg.smtp_port)
            server.starttls()
            server.login(cfg.sender_email, cfg.sender_password)
            server.sendmail(cfg.sender_email, all_recipients, msg.as_string())
            server.quit()
            
            log_msg = f"Email sent to {cfg.to_email}"
            if cc_addrs:
                log_msg += f" (CC: {len(cc_addrs)})"
            if bcc_addrs:
                log_msg += f" (BCC: {len(bcc_addrs)})"
            logger.info(f"NOTIFIER: {log_msg}")
            return True

        except Exception as e:
            logger.error(f"NOTIFIER: Failed to send email: {e}")
            return False

    def _send_teams(self, subject: str, message: str, level: str) -> bool:
        """Send Teams webhook notification."""
        cfg = self.config.channels.teams
        try:
            colors = {"ERROR": "FF0000", "WARNING": "FFA500", "INFO": "00FF00"}
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": colors.get(level, "808080"),
                "summary": subject,
                "sections": [{
                    "activityTitle": subject,
                    "text": message
                }]
            }
            response = httpx.post(cfg.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("NOTIFIER: Teams notification sent.")
                return True
            else:
                logger.error(f"NOTIFIER: Teams failed with {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"NOTIFIER: Failed to send Teams webhook: {e}")
            return False

    def _send_slack(self, subject: str, message: str, level: str) -> bool:
        """Send Slack webhook notification."""
        cfg = self.config.channels.slack
        try:
            icons = {"ERROR": ":rotating_light:", "WARNING": ":warning:", "INFO": ":white_check_mark:"}
            payload = {
                "text": f"{icons.get(level, ':bell:')} *{subject}*\n{message}"
            }
            response = httpx.post(cfg.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("NOTIFIER: Slack notification sent.")
                return True
            else:
                logger.error(f"NOTIFIER: Slack failed with {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"NOTIFIER: Failed to send Slack webhook: {e}")
            return False
