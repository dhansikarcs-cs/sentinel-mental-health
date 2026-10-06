"""Doctor feature: in-app crisis alerts for the assigned psychologist.

Emails can be unconfigured — the clinician's in-app inbox is the channel
they always see. A crisis trigger must drop a crisis-type notification for
the assigned psychologist; a resolution must drop an informational one.
"""


def _crisis_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_trigger_notifies_assigned_psych(client, make_user, db_session):
    from app.models.notification import Notification

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    resp = client.post("/api/crisis/trigger", headers=_crisis_headers(patient["access_token"]))
    assert resp.status_code == 200, resp.text

    rows = db_session.query(Notification).filter(Notification.recipient_username == psych["username"]).all()
    assert len(rows) == 1
    assert rows[0].notification_type == "crisis"
    assert patient["username"] in rows[0].message or patient["username"] in rows[0].title


def test_patient_without_psych_does_not_error(client, make_user, db_session):
    from app.models.notification import Notification

    patient = make_user(role="patient")
    resp = client.post("/api/crisis/trigger", headers=_crisis_headers(patient["access_token"]))
    assert resp.status_code == 200

    assert db_session.query(Notification).count() == 0


def test_resolve_notifies_assigned_psych(client, make_user, db_session):
    from app.models.notification import Notification

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    client.post("/api/crisis/trigger", headers=_crisis_headers(patient["access_token"]))
    client.post("/api/crisis/resolve", headers=_crisis_headers(patient["access_token"]))

    rows = (
        db_session.query(Notification)
        .filter(Notification.recipient_username == psych["username"])
        .order_by(Notification.id)
        .all()
    )
    assert len(rows) == 2
    assert rows[0].notification_type == "crisis"
    assert rows[1].notification_type == "info"
    assert "resolved" in (rows[1].title + rows[1].message).lower()


def test_other_psychs_are_not_notified(client, make_user, db_session):
    from app.models.notification import Notification

    psych_a = make_user(role="psychologist")
    make_user(role="psychologist")  # psych_b — not assigned
    patient = make_user(role="patient", assigned_psych=psych_a["username"])

    client.post("/api/crisis/trigger", headers=_crisis_headers(patient["access_token"]))

    rows = db_session.query(Notification).all()
    assert all(n.recipient_username == psych_a["username"] for n in rows)


def test_auto_detected_crisis_notifies_assigned_psych_not_patient(client, make_user, db_session):
    from app.models.notification import Notification

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    resp = client.post(
        "/api/journal",
        headers=_crisis_headers(patient["access_token"]),
        json={"raw_content": "I can't take it anymore, I want to end my life"},
    )
    assert resp.status_code == 200, resp.text

    rows = db_session.query(Notification).order_by(Notification.id).all()
    # The clinician alert ("CRITICAL: Auto-Crisis Triggered") must reach the
    # assigned psychologist's inbox — it must NOT be dropped with no recipient
    # nor routed to the patient.
    clinician_alerts = [
        n for n in rows if n.notification_type == "crisis" and n.recipient_username
    ]
    assert clinician_alerts, "auto-detected crisis must alert the assigned clinician"
    assert all(
        n.recipient_username == psych["username"] for n in clinician_alerts
    ), "crisis clinician alert must route to the assigned psychogist"
    assert all(
        n.recipient_username != patient["username"] for n in rows
    ), "crisis notifications must never be addressed to the patient"
