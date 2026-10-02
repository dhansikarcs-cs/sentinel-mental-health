"""Doctor feature: weekly digest endpoint.

GET /agents/weekly-digest — one Monday-morning rollup of the last 7 days:
caseload activity totals with week-over-week trend, completed follow-ups,
resolved crisis episodes, and per-client highlights (silent drop-offs,
high engagement, recoveries).
"""

from datetime import UTC, datetime, timedelta


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_digest_requires_clinician(client, make_user):
    patient = make_user(role="patient")
    resp = client.get("/api/agents/weekly-digest", headers=_headers(patient["access_token"]))
    assert resp.status_code == 403


def test_digest_empty_caseload(client, make_user):
    psych = make_user(role="psychologist")
    resp = client.get("/api/agents/weekly-digest", headers=_headers(psych["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total_clients"] == 0
    assert body["summary"]["checkins"] == 0
    assert body["summary"]["checkin_trend"] == "flat"
    assert body["highlights"] == []


def test_digest_counts_activity_and_trend(client, make_user, db_session):
    from app.models.journal import JournalEntry

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    headers = _headers(patient["access_token"])

    # This week: 2 journals + 1 mood
    client.post("/api/journal", headers=headers, json={"raw_content": "entry one"})
    client.post("/api/journal", headers=headers, json={"raw_content": "entry two"})
    client.post(
        "/api/mood",
        headers=headers,
        json={"date": datetime.now(UTC).date().isoformat(), "emoji": "🙂", "label": "okay"},
    )
    # Last week: 1 journal (backdated)
    session = db_session
    session.add(
        JournalEntry(
            patient_username=patient["username"],
            raw_content="old",
            summary="old",
            clinical_summary="old",
            timestamp=(datetime.now(UTC) - timedelta(days=10)).isoformat(),
        )
    )
    session.commit()

    resp = client.get("/api/agents/weekly-digest", headers=_headers(psych["access_token"]))
    body = resp.json()
    assert body["summary"]["total_clients"] == 1
    assert body["summary"]["journals"] == 2
    assert body["summary"]["moods"] == 1
    assert body["summary"]["checkins"] == 3
    assert body["summary"]["checkin_trend"] == "up"


def test_digest_followups_and_crisis_and_highlights(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    headers = _headers(patient["access_token"])

    # 3 completed follow-ups → highlight
    for title in ["T1", "T2", "T3"]:
        client.post(
            "/api/followups",
            headers=_headers(psych["access_token"]),
            json={"patient_username": patient["username"], "title": title},
        )
    tasks = client.get("/api/followups", headers=headers).json()
    for t in tasks:
        client.put(f"/api/followups/{t['id']}", headers=headers, json={"status": "completed"})

    # 1 resolved crisis episode → highlight
    client.post("/api/crisis/trigger", headers=headers)
    client.post("/api/crisis/resolve", headers=headers)

    resp = client.get("/api/agents/weekly-digest", headers=_headers(psych["access_token"]))
    body = resp.json()
    assert body["summary"]["followups_completed"] == 3
    assert body["summary"]["crisis_episodes_resolved"] == 1

    kinds = {h["kind"] for h in body["highlights"]}
    assert "followups" in kinds
    assert "crisis_resolved" in kinds


def test_digest_flags_silent_dropoff(client, make_user, db_session):
    from app.models.journal import JournalEntry

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    # Activity only in the previous week → went silent this week
    db_session.add(
        JournalEntry(
            patient_username=patient["username"],
            raw_content="last week",
            summary="last week",
            clinical_summary="last week",
            timestamp=(datetime.now(UTC) - timedelta(days=10)).isoformat(),
        )
    )
    db_session.commit()

    resp = client.get("/api/agents/weekly-digest", headers=_headers(psych["access_token"]))
    kinds = {h["kind"] for h in resp.json()["highlights"]}
    assert "went_silent" in kinds
