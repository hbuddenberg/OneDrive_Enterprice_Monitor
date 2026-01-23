"""Test script for validating notification system.

This script tests all notification channels and templates.
Run: uv run python test_notifications.py [test_type]

Test types:
  - preview      : Preview all HTML templates in browser (no email sent)
  - auth         : Test AUTH_REQUIRED notification
  - error        : Test ERROR notification
  - not_running  : Test NOT_RUNNING notification
  - paused       : Test PAUSED notification
  - resolved     : Test RESOLVED notification
  - direct       : Test direct email send (bypass cooldown)
  - all          : Preview all + send test email
"""

import sys
import logging
import argparse
import webbrowser
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Setup path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.shared.config import get_config
from src.shared.notifier import Notifier
from src.shared.templates import render_template, STATUS_TEMPLATES, TEMPLATES_DIR

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_notifications")


def print_config():
    """Print current notification configuration."""
    config = get_config()
    notif = config.notifications

    print("\n" + "=" * 60)
    print("NOTIFICATION CONFIGURATION")
    print("=" * 60)
    print(f"  Enabled:          {notif.enabled}")
    print(f"  Cooldown:         {notif.cooldown_minutes} minutes")
    print(f"  Account:          {config.target.email}")
    print()

    # Email
    email = notif.channels.email
    print("  [EMAIL]")
    print(f"    Enabled:        {email.enabled}")
    print(f"    SMTP Server:    {email.smtp_server}:{email.smtp_port}")
    print(f"    From:           {email.sender_email}")
    print(f"    To:             {email.to_email}")
    print(f"    CC:             {email.cc_email or 'None'}")
    print(f"    BCC:            {email.bcc_email or 'None'}")
    print()

    # Teams
    teams = notif.channels.teams
    print("  [TEAMS]")
    print(f"    Enabled:        {teams.enabled}")
    print(f"    Webhook:        {teams.webhook_url[:50] + '...' if teams.webhook_url else 'Not configured'}")
    print()

    # Slack
    slack = notif.channels.slack
    print("  [SLACK]")
    print(f"    Enabled:        {slack.enabled}")
    print(f"    Webhook:        {slack.webhook_url[:50] + '...' if slack.webhook_url else 'Not configured'}")
    print("=" * 60)


def preview_templates():
    """Preview all HTML templates in browser without sending emails."""
    print("\n[PREVIEW] Opening HTML templates in browser...")

    account = get_config().target.email
    now = datetime.now()
    start_time = (now - timedelta(hours=2, minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    end_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # List all templates and render them
    templates_to_preview = [
        ("AUTH_REQUIRED", {"timestamp": start_time, "account": account}),
        ("ERROR", {"timestamp": start_time, "account": account, "message": "La sincronización falló debido a un error de red"}),
        ("NOT_RUNNING", {"timestamp": start_time, "account": account}),
        ("PAUSED", {"timestamp": start_time, "account": account}),
        ("SYNCING", {"timestamp": start_time, "account": account, "message": "Subiendo 150 archivos..."}),
        ("OK", {"timestamp": start_time, "account": account}),
        ("NOT_FOUND", {"timestamp": start_time, "account": account}),
        ("UNKNOWN", {"timestamp": start_time, "account": account}),
        ("RESOLVED", {"outage_start": start_time, "outage_end": end_time, "account": account, "duration": "2h 15m"}),
    ]

    print(f"\n  Templates directory: {TEMPLATES_DIR}")
    print(f"  Available templates: {list(STATUS_TEMPLATES.keys())}\n")

    for status, params in templates_to_preview:
        try:
            html = render_template(status=status, **params)

            # Save to temp file and open in browser
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8", prefix=f"{status}_"
            ) as f:
                f.write(html)
                temp_path = f.name

            print(f"  Opening {status}: {temp_path}")
            webbrowser.open(f"file://{temp_path}")

        except Exception as e:
            print(f"  ERROR rendering {status}: {e}")

    print("\n[PREVIEW] Templates opened in browser.")


def test_status_notification(status: str):
    """Test sending a notification for a specific status."""
    print(f"\n[TEST] Sending {status} notification...")

    notifier = Notifier()
    notifier._last_notification_time = None  # Bypass cooldown

    start_time = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    notifier.send_status_notification(
        status=status, timestamp=start_time, message=f"Notificación de prueba para estado {status}."
    )

    print(f"[TEST] {status} notification sent (check your inbox).")


def test_resolution_notification():
    """Test sending a resolution notification."""
    print("\n[TEST] Sending RESOLUTION notification...")

    notifier = Notifier()
    notifier._last_notification_time = None  # Bypass cooldown

    start_time = (datetime.now() - timedelta(hours=1, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notifier.send_resolution_notification(start_time, end_time)

    print("[TEST] Resolution notification sent (check your inbox).")


def test_direct_email():
    """Test sending email directly without cooldown checks."""
    print("\n[TEST] Sending direct email (bypassing notify())...")

    notifier = Notifier()

    html = render_template(
        status="AUTH_REQUIRED",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        account=get_config().target.email,
    )

    success = notifier._send_email(subject="Direct Email Test", body=html, is_html=True)

    if success:
        print("[TEST] Direct email sent successfully!")
    else:
        print("[TEST] Direct email FAILED - check configuration.")


def main():
    parser = argparse.ArgumentParser(
        description="Test notification system", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__
    )
    parser.add_argument(
        "test_type",
        nargs="?",
        default="preview",
        choices=[
            "preview",
            "auth",
            "error",
            "not_running",
            "paused",
            "resolved",
            "direct",
            "all",
        ],
        help="Type of test to run (default: preview)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("ONEDRIVE MONITOR - NOTIFICATION TEST SUITE")
    print("=" * 60)

    print_config()

    if args.test_type == "preview":
        preview_templates()

    elif args.test_type == "auth":
        test_status_notification("AUTH_REQUIRED")

    elif args.test_type == "error":
        test_status_notification("ERROR")

    elif args.test_type == "not_running":
        test_status_notification("NOT_RUNNING")

    elif args.test_type == "paused":
        test_status_notification("PAUSED")

    elif args.test_type == "resolved":
        test_resolution_notification()

    elif args.test_type == "direct":
        test_direct_email()

    elif args.test_type == "all":
        preview_templates()

        print("\n" + "-" * 40)
        confirm = input("Send test email? (y/N): ").strip().lower()
        if confirm == "y":
            test_direct_email()
        else:
            print("Skipping email test.")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
