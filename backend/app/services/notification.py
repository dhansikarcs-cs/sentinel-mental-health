import logging
import smtplib
import socket
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("sentinel.notification")

_TRANSPORTS = (
    ("ssl", 465),
    ("starttls", 587),
)


def _resolve_v4(host: str, port: int) -> str:
    """Resolve ``host`` to a literal IPv4 address.

    Some hosting networks (e.g. Render free instances) have no IPv6 route, and
    smtplib's default resolution can select an AAAA record first, failing with
    ``OSError: [Errno 101] Network is unreachable``. Pinning to IPv4 avoids that.
    """
    try:
        return socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
    except OSError:
        return host


def send_email(to: str, subject: str, body: str) -> bool:
    logger.info("Sending email to %s: %s", to, subject)
    if not settings.smtp_host:
        logger.warning("SMTP not configured — email logged only")
        return False
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    sender = settings.email_from
    if not sender or sender == "sentinel@example.com":
        sender = settings.smtp_user or sender
    msg["From"] = sender
    msg["To"] = to
    errors: list[str] = []
    for mode, port in _TRANSPORTS:
        host = _resolve_v4(settings.smtp_host, port)
        try:
            if mode == "ssl":
                s = smtplib.SMTP_SSL(host, port, timeout=20)
            else:
                s = smtplib.SMTP(host, port, timeout=20)
            with s:
                s.ehlo()
                if mode == "starttls":
                    s.starttls()
                    s.ehlo()
                s.login(settings.smtp_user, settings.smtp_password)
                s.send_message(msg)
            logger.info("Email sent successfully to %s via %s:%s", to, mode, port)
            return True
        except smtplib.SMTPAuthenticationError:
            errors.append("auth-rejected")
            logger.error("SMTP auth failed — app password may be expired")
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")
            logger.error("Email transport %s:%s failed: %s:%s", mode, port, type(e).__name__, e)
    logger.error("All SMTP transports failed (%s) — email NOT sent to %s", ", ".join(errors), to)
    return False
