import logging
import smtplib
import socket
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("sentinel.notification")


def _smtp_connect() -> smtplib.SMTP:
    """Return an SMTP client connected over IPv4.

    Some hosting networks (e.g. Render free instances) have no IPv6 route, and
    smtplib's default resolution can select an AAAA record first, failing with
    ``OSError: [Errno 101] Network is unreachable``. Resolving the host to a
    literal IPv4 address before handing it to smtplib avoids that entirely.
    """
    host = settings.smtp_host
    try:
        host = socket.getaddrinfo(
            host, settings.smtp_port, socket.AF_INET, socket.SOCK_STREAM
        )[0][4][0]
    except OSError:
        pass
    return smtplib.SMTP(host, settings.smtp_port, timeout=10)


def send_email(to: str, subject: str, body: str) -> bool:
    logger.info("Sending email to %s: %s", to, subject)
    if not settings.smtp_host:
        logger.warning("SMTP not configured — email logged only")
        return False
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        sender = settings.email_from
        if not sender or sender == "sentinel@example.com":
            sender = settings.smtp_user or sender
        msg["From"] = sender
        msg["To"] = to
        with _smtp_connect() as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        logger.info("Email sent successfully to %s", to)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP auth failed — app password may be expired. Generate new one at https://myaccount.google.com/apppasswords"
        )
        return False
    except Exception as e:
        logger.error("Email send failed: %s: %s", type(e).__name__, e)
        return False
