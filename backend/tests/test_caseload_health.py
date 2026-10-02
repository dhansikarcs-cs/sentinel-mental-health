"""Doctor feature: caseload health summary endpoint.

GET /psychologists/caseload-health gives the clinician one call that ranks
their whole caseload worst-first (crisis → disengaged → watch → ok) with
per-client engagement counts, pending follow-ups, and quiet-days.
"""

from datetime import UTC, datetime, timedelta


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client, username: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_caseload_requires_clinician_role(client, make_user):
    patient = make_user(role="patient")
    resp = client.get("/api/psychologists/caseload-health", headers=_headers(patient["access_token"]))
    assert resp.status_code == 403


def test_caseload_empty(client, make_user):
    psych = make_user(role="psychologist")
    resp = client.get("/api/psychologists/caseload-health", headers=_headers(psych["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total_clients"] == 0
    assert body["clients"] == []


def test_caseload_scopes_to_assigned_clients(client, make_user):
    psych_a = make_user(role="psychologist")
    psych_b = make_user(role="psychologist")
    mine = make_user(role="patient", assigned_psych=psych_a["username"])
    theirs = make_user(role="patient", assigned_psych=psych_b["username"])

    resp = client.get("/api/psychologists/caseload-health", headers=_headers(psych_a["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    usernames = [c["username"] for c in body["clients"]]
    assert mine["username"] in usernames
    assert theirs["username"] not in usernames
    assert body["summary"]["total_clients"] == 1


def test_caseload_flags_active_crisis_first(client, make_user):
    psych = make_user(role="psychologist")
    crisis_patient = make_user(role="patient", assigned_psych=psych["username"])
    make_user(role="patient", assigned_psych=psych["username"])  # quiet client

    resp = client.post("/api/crisis/trigger", headers=_headers(crisis_patient["access_token"]))
    assert resp.status_code == 200

    resp = client.get("/api/psychologists/caseload-health", headers=_headers(psych["access_token"]))
    body = resp.json()
    assert body["summary"]["active_crises"] == 1
    assert body["clients"][0]["crisis_active"] is True
    assert body["clients"][0]["attention"] == "crisis"


def test_caseload_flags_disengaged(client, make_user):
    psych = make_user(role="psychologist")
    make_user(role="patient", assigned_psych=psych["username"])  # no activity at all

    resp = client.get("/api/psychologists/caseload-health", headers=_headers(psych["access_token"]))
    body = resp.json()
    assert body["summary"]["disengaged"] == 1
    assert body["clients"][0]["attention"] == "disengaged"
    assert body["clients"][0]["days_quiet"] is None


def test_caseload_counts_engagement_and_pending_followups(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    headers = _headers(patient["access_token"])

    # 2 journals + 1 mood in the last 7 days
    client.post("/api/journal", headers=headers, json={"raw_content": "feeling okay today"})
    client.post("/api/journal", headers=headers, json={"raw_content": "better afternoon"})
    client.post(
        "/api/mood",
        headers=headers,
        json={"date": datetime.now(UTC).date().isoformat(), "emoji": "🙂", "label": "okay"},
    )

    # Two pending follow-ups assigned by the psych
    client.post(
        "/api/followups",
        headers=_headers(psych["access_token"]),
        json={"patient_username": patient["username"], "title": "Breathing log", "description": "log twice daily"},
    )
    client.post(
        "/api/followups",
        headers=_headers(psych["access_token"]),
        json={"patient_username": patient["username"], "title": "Sleep diary", "description": "one week"},
    )

    resp = client.get("/api/psychologists/caseload-health", headers=_headers(psych["access_token"]))
    body = resp.json()
    row = next(c for c in body["clients"] if c["username"] == patient["username"])
    assert row["journals_7d"] == 2
    assert row["moods_7d"] == 1
    assert row["checkins_7d"] == 3
    assert row["pending_followups"] == 2
    assert body["summary"]["pending_followups"] == 2
    assert row["attention"] == "ok"
    assert body["summary"]["checked_in_today"] == 1


def test_caseload_watch_after_five_quiet_days(client, make_user, db_session):
    from app.models.journal import JournalEntry

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    # One journal, 6 days old → some activity but quiet recently
    session = db_session
    entry = JournalEntry(
        patient_username=patient["username"],
        raw_content="old entry",
        summary="old",
        clinical_summary="old",
        timestamp=(datetime.now(UTC) - timedelta(days=6)).isoformat(),
    )
    session.add(entry)
    session.commit()

    resp = client.get("/api/psychologists/caseload-health", headers=_headers(psych["access_token"]))
    body = resp.json()
    row = next(c for c in body["clients"] if c["username"] == patient["username"])
    assert row["journals_7d"] == 1
    assert row["days_quiet"] == 6
    assert row["attention"] == "watch"
