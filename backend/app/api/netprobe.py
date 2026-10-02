"""Temporary outbound-network probe. Remove once SMTP is verified."""
import socket

from fastapi import APIRouter, Query

router = APIRouter(prefix="/_probe", tags=["_probe"])

_TOKEN = "sentinel-netprobe-2026"

_TARGETS = [
    ("gmail-smtp:465", "smtp.gmail.com", 465),
    ("gmail-smtp:587", "smtp.gmail.com", 587),
    ("google-www:443", "www.google.com", 443),
    ("google-dns:53", "8.8.8.8", 53),
    ("cloudflare:443", "1.1.1.1", 443),
    ("sendgrid-smtp:465", "smtp.sendgrid.net", 465),
    ("outlook-smtp:587", "outlook.office365.com", 587),
]


@router.get("")
def probe(token: str = Query(...)):
    if token != _TOKEN:
        return {"ok": False, "error": "bad token"}
    results = {}
    for label, host, port in _TARGETS:
        try:
            ip = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(6)
            try:
                s.connect((ip, port))
                results[label] = f"OK ({ip})"
            finally:
                s.close()
        except socket.timeout:
            results[label] = "TIMEOUT"
        except OSError as e:
            results[label] = f"{type(e).__name__}: {e}"
    return {"ok": True, "results": results}