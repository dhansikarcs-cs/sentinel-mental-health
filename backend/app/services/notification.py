import json
import logging
import smtplib
import socket
import urllib.error
import urllib.request
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


def _resend_sender() -> str:
    if settings.resend_from:
        return settings.resend_from
    # Fresh Resend accounts can send test mail from the built-in sender without
    # verifying a domain. EMAIL_FROM is a Gmail address we can never verify here.
    return "Sentinel <onboarding@resend.dev>"


def _send_resend(to: str, subject: str, body: str) -> bool:
    payload = {
        "from": _resend_sender(),
        "to": [to],
        "subject": subject,
        "text": body,
    }
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "sentinel/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            logger.info("Email sent successfully to %s via Resend (HTTP %s)", to, resp.status)
            return True
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        logger.error("Resend send failed: HTTP %s: %s", e.code, detail)
        return False
    except Exception as e:
        logger.error("Email send failed: %s: %s", type(e).__name__, e)
        return False


def _send_smtp(to: str, subject: str, body: str) -> bool:
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
            s = smtplib.SMTP_SSL(host, port, timeout=20) if mode == "ssl" else smtplib.SMTP(host, port, timeout=20)
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


def send_email(to: str, subject: str, body: str) -> bool:
    logger.info("Sending email to %s: %s", to, subject)
    if not settings.resend_api_key and not settings.smtp_host:
        logger.warning("No email transport configured — email logged only")
        return False
    if settings.resend_api_key:
        return _send_resend(to, subject, body)
    return _send_smtp(to, subject, body)
