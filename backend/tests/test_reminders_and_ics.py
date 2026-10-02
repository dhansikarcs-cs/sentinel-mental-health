"""Session reminders (day-before, idempotent) + ICS calendar download."""

from datetime import UTC, datetime, timedelta

from app.models.notification import Notification
from app.workers.reminder_worker import _sweep_session_reminders


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mk_approved_tomorrow(client, patient, psych) -> int:
    tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    r = client.post(
        "/api/bookings",
        headers=_headers(patient["access_token"]),
        json={
            "psychologist_username": psych["username"],
            "date": tomorrow,
            "time": "10:00",
            "session_type": "Therapy",
            "members": "",
            "contact": "p@example.com",
            "explanation": "weekly",
        },
    )
    assert r.status_code in (200, 201), r.text
    bid = r.json()["id"]
    r2 = client.put(f"/api/bookings/{bid}/status", headers=_headers(psych["access_token"]), json={"status": "Approved"})
    assert r2.status_code == 200, r2.text
    return bid


def test_session_reminder_for_both_parties(client, make_user, db_session):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    _mk_approved_tomorrow(client, patient, psych)

    _sweep_session_reminders()

    patient_rows = (
        db_session.query(Notification)
        .filter(Notification.title == "⏰ Session tomorrow", Notification.recipient_username.is_(None))
        .all()
    )
    psych_rows = (
        db_session.query(Notification)
        .filter(Notification.title == "⏰ Session tomorrow", Notification.recipient_username == psych["username"])
        .all()
    )
    assert len(patient_rows) == 1
    assert len(psych_rows) == 1
    assert "tomorrow" in patient_rows[0].message


def test_session_reminder_idempotent(client, make_user, db_session):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    _mk_approved_tomorrow(client, patient, psych)

    _sweep_session_reminders()
    _sweep_session_reminders()
    _sweep_session_reminders()

    count = db_session.query(Notification).filter(Notification.title == "⏰ Session tomorrow").count()
    assert count == 2  # one per party, not per sweep


def test_no_reminder_for_non_approved_or_later_sessions(client, make_user, db_session):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    # Pending session tomorrow → no reminder
    tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    r = client.post(
        "/api/bookings",
        headers=_headers(patient["access_token"]),
        json={
            "psychologist_username": psych["username"],
            "date": tomorrow,
            "time": "10:00",
            "session_type": "T",
            "members": "",
            "contact": "x",
            "explanation": "e",
        },
    )
    assert r.status_code in (200, 201)
    _sweep_session_reminders()
    count = db_session.query(Notification).filter(Notification.title == "⏰ Session tomorrow").count()
    assert count == 0


def test_ics_download_owner_and_psych(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    bid = _mk_approved_tomorrow(client, patient, psych)

    resp = client.get(f"/api/bookings/{bid}/ics", headers=_headers(patient["access_token"]))
    assert resp.status_code == 200
    body = resp.text
    assert body.startswith("BEGIN:VCALENDAR")
    assert "BEGIN:VEVENT" in body
    assert f"UID:sentinel-booking-{bid}@sentinel" in body
    assert "SUMMARY:Session with" in body
    assert resp.headers["content-type"].startswith("text/calendar")

    # Psych can download too
    resp2 = client.get(f"/api/bookings/{bid}/ics", headers=_headers(psych["access_token"]))
    assert resp2.status_code == 200


def test_ics_denied_for_stranger(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    stranger = make_user(role="patient")
    bid = _mk_approved_tomorrow(client, patient, psych)

    resp = client.get(f"/api/bookings/{bid}/ics", headers=_headers(stranger["access_token"]))
    assert resp.status_code == 403
