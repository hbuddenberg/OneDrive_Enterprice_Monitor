import sys
import logging
from src.shared.config import get_config
from src.shared.notifier import Notifier

# Configure basic logging to see Notifier output
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("email_test.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("test_email")

def test_email():
    print("Loading configuration...")
    try:
        config = get_config()
        email_conf = config.notifications.channels.email
        
        print(f"SMTP Server: {email_conf.smtp_server}:{email_conf.smtp_port}")
        print(f"Sender: {email_conf.sender_email}")
        print(f"To: {email_conf.to_email}")
        print(f"CC: {email_conf.cc_email}")
        print(f"BCC: {email_conf.bcc_email}")
        
        if not email_conf.enabled:
            print("ERROR: Email channel is disabled in config!")
            return

        print("\nAttempting to send test email...")
        notifier = Notifier()
        # Force a notification even if cooldown is active (Notifier check cooldown, but we can bypass or wait)
        # Actually Notifier checks cooldown. Let's hijack it or just call _send_email directly if we can, 
        # but calling notify() tests the full path.
        
        # To bypass cooldown for test, we can manually call _send_email
        notifier._send_email(
            subject="Test Email from Monitor",
            body="This is a test email to verify SMTP settings and connectivity.\nIf you are reading this, configuration is correct.",
            is_html=False
        )
        print("\nTest finished. Check logs above for success/failure.")

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_email()
