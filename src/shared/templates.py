"""Email template loader for OneDrive Monitor notifications.

Templates are stored as HTML files in the templates/ directory.
Each template uses {placeholder} syntax for variable substitution.

Available placeholders:
    - {status}       : Current OneDrive status
    - {timestamp}    : When the event occurred
    - {account}      : Account email
    - {message}      : Additional message/details
    - {generated_at} : When the email was generated
    - {outage_start} : Start time of outage (resolved template)
    - {outage_end}   : End time of outage (resolved template)
    - {duration}     : Duration of outage (resolved template)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Template mapping by status
STATUS_TEMPLATES = {
    "AUTH_REQUIRED": "auth_required.html",
    "ERROR": "error.html",
    "NOT_RUNNING": "not_running.html",
    "PAUSED": "paused.html",
    "SYNCING": "syncing.html",
    "OK": "ok.html",
    "NOT_FOUND": "not_found.html",
    "UNKNOWN": "unknown.html",
    "RESOLVED": "resolved.html",
}

# Fallback template for unknown statuses
FALLBACK_TEMPLATE = "unknown.html"


def load_template(template_name: str) -> Optional[str]:
    """Load a template file from the templates directory.
    
    Args:
        template_name: Name of the template file (e.g., 'error.html')
        
    Returns:
        Template content as string, or None if not found.
    """
    template_path = TEMPLATES_DIR / template_name
    
    try:
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        else:
            logger.warning(f"Template not found: {template_path}")
            return None
    except Exception as e:
        logger.error(f"Error loading template {template_name}: {e}")
        return None


def get_template_for_status(status: str) -> str:
    """Get the appropriate template for a given status.
    
    Args:
        status: OneDrive status string (e.g., 'AUTH_REQUIRED', 'ERROR')
        
    Returns:
        Template content as string.
    """
    template_name = STATUS_TEMPLATES.get(status.upper(), FALLBACK_TEMPLATE)
    template = load_template(template_name)
    
    if template is None:
        # Ultimate fallback - return a basic HTML template
        logger.warning(f"Using inline fallback for status: {status}")
        return _get_fallback_template()
    
    return template


def render_template(
    status: str,
    account: str = "",
    timestamp: str = None,
    message: str = "",
    outage_start: str = None,
    outage_end: str = None,
    duration: str = "",
    **extra_vars
) -> str:
    """Render a template for the given status with variable substitution.
    
    Args:
        status: OneDrive status (determines which template to use)
        account: Account email address
        timestamp: When the event occurred
        message: Additional message/details
        outage_start: Start of outage (for resolved template)
        outage_end: End of outage (for resolved template)
        duration: Duration string (for resolved template)
        **extra_vars: Additional variables for substitution
        
    Returns:
        Rendered HTML string.
    """
    template = get_template_for_status(status)
    
    # Prepare variables
    now = datetime.now()
    variables = {
        "status": status,
        "account": account or "N/A",
        "timestamp": timestamp or now.strftime("%Y-%m-%d %H:%M:%S"),
        "message": message or "No additional details",
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "outage_start": outage_start or "N/A",
        "outage_end": outage_end or "N/A",
        "duration": duration or "N/A",
        **extra_vars
    }
    
    # Substitute variables
    try:
        rendered = template.format(**variables)
    except KeyError as e:
        logger.warning(f"Missing template variable: {e}")
        # Try partial substitution
        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", str(value))
        rendered = template
    
    return rendered


def render_status_notification(
    status: str,
    account: str,
    timestamp: str = None,
    message: str = ""
) -> str:
    """Render a notification template for a status change.
    
    Args:
        status: The new OneDrive status
        account: Account email
        timestamp: When the status changed
        message: Additional context
        
    Returns:
        Rendered HTML string.
    """
    return render_template(
        status=status,
        account=account,
        timestamp=timestamp,
        message=message
    )


def render_resolution_notification(
    account: str,
    outage_start: str,
    outage_end: str,
    duration: str = ""
) -> str:
    """Render a resolution notification template.
    
    Args:
        account: Account email
        outage_start: When the outage started
        outage_end: When service was restored
        duration: Human-readable duration string
        
    Returns:
        Rendered HTML string.
    """
    return render_template(
        status="RESOLVED",
        account=account,
        outage_start=outage_start,
        outage_end=outage_end,
        duration=duration
    )


def list_available_templates() -> list[str]:
    """List all available template files.
    
    Returns:
        List of template filenames.
    """
    if not TEMPLATES_DIR.exists():
        return []
    
    return [f.name for f in TEMPLATES_DIR.glob("*.html")]


def _get_fallback_template() -> str:
    """Return a basic fallback template when no file template is available."""
    return """
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #333;">Alerta del Monitor OneDrive</h2>
    <p><strong>Estado:</strong> {status}</p>
    <p><strong>Cuenta:</strong> {account}</p>
    <p><strong>Hora:</strong> {timestamp}</p>
    <p>{message}</p>
    <hr>
    <p style="color: #666; font-size: 12px;">
        Monitor OneDrive Empresarial - {generated_at}
    </p>
</body>
</html>
"""
