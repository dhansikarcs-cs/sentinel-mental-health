"""Patient booking actions + counterpart notifications.

Patients may: accept/decline a session Proposed to them, cancel their own
Pending request or Approved appointment. Everything else stays with the
clinician. Every status change notifies the other party in-app.
"""


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mk_booking(client, patient, psych, status: str | None = None) -> int:
    r = client.post(
        "/api/bookings",
        headers=_headers(patient["access_token"]),
        json={
            "psychologist_username": psych["username"],
            "date": "2099-04-01",
            "time": "10:00",
            "session_type": "Therapy",
            "members": "",
            "contact": "p@example.com",
            "explanation": "check-in",
        },
    )
    assert r.status_code in (200, 201), r.text
    bid = r.json()["id"]
    if status:
        r2 = client.put(f"/api/bookings/{bid}/status", headers=_headers(psych["access_token"]), json={"status": status})
        assert r2.status_code == 200, r2.text
    return bid


# ── patient-allowed transitions ──────────────────────────────────


def test_patient_can_cancel_own_pending(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    bid = _mk_booking(client, patient, psych)

    resp = client.put(
        f"/api/bookings/{bid}/status", headers=_headers(patient["access_token"]), json={"status": "Cancelled"}
    )
    assert resp.status_code == 200, resp.text
    bookings = client.get("/api/bookings", headers=_headers(patient["access_token"])).json()
    assert next(b for b in bookings if b["id"] == bid)["status"] == "Cancelled"


def test_patient_can_cancel_own_approved(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    bid = _mk_booking(client, patient, psych, status="Approved")

    resp = client.put(
        f"/api/bookings/{bid}/status", headers=_headers(patient["access_token"]), json={"status": "Cancelled"}
    )
    assert resp.status_code == 200


def test_patient_cannot_approve_or_complete(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    bid = _mk_booking(client, patient, psych)

    resp = client.put(
        f"/api/bookings/{bid}/status", headers=_headers(patient["access_token"]), json={"status": "Approved"}
    )
    assert resp.status_code == 403

    client.put(f"/api/bookings/{bid}/status", headers=_headers(psych["access_token"]), json={"status": "Approved"})
    resp = client.put(
        f"/api/bookings/{bid}/status", headers=_headers(patient["access_token"]), json={"status": "Completed"}
    )
    assert resp.status_code == 403


def test_stranger_cannot_touch_booking(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    stranger = make_user(role="patient")
    bid = _mk_booking(client, patient, psych)

    resp = client.put(
        f"/api/bookings/{bid}/status", headers=_headers(stranger["access_token"]), json={"status": "Cancelled"}
    )
    assert resp.status_code == 403


# ── counterpart notifications ────────────────────────────────────


def test_psych_notified_on_new_request(client, make_user, db_session):
    from app.models.notification import Notification

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    _mk_booking(client, patient, psych)

    rows = db_session.query(Notification).filter(Notification.recipient_username == psych["username"]).all()
    assert any("session request" in (n.title + n.message).lower() for n in rows)


def test_patient_notified_on_approval_and_cancel(client, make_user, db_session):
    from app.models.notification import Notification

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    bid = _mk_booking(client, patient, psych)

    client.put(f"/api/bookings/{bid}/status", headers=_headers(psych["access_token"]), json={"status": "Approved"})
    client.put(f"/api/bookings/{bid}/status", headers=_headers(psych["access_token"]), json={"status": "Cancelled"})

    rows = (
        db_session.query(Notification)
        .filter(Notification.patient_username == patient["username"], Notification.recipient_username.is_(None))
        .all()
    )
    titles = " ".join(n.title for n in rows)
    assert "Approved" in titles and "Cancelled" in titles


def test_reschedule_notifies_counterpart(client, make_user, db_session):
    from app.models.notification import Notification

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    bid = _mk_booking(client, patient, psych)

    client.put(
        f"/api/bookings/{bid}/reschedule",
        headers=_headers(psych["access_token"]),
        json={"date": "2099-04-02", "time": "11:00"},
    )

    rows = (
        db_session.query(Notification)
        .filter(Notification.patient_username == patient["username"], Notification.recipient_username.is_(None))
        .all()
    )
    assert any("moved" in (n.title + n.message).lower() for n in rows)
