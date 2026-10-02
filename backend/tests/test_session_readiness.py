"""Doctor feature: session readiness score.

GET /agents/session-readiness/{patient} — a 0-100 score with contributing
factors that tells the clinician how engaged and stable a client is going
into their next session. Deterministic and explainable: every point comes
from a named factor (check-ins, mood trend, follow-up completion, crisis
recency) so the score is never a black box.
"""

from datetime import UTC, datetime, timedelta


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_readiness_requires_clinician(client, make_user):
    patient = make_user(role="patient")
    resp = client.get(f"/api/agents/session-readiness/{patient['username']}", headers=_headers(patient["access_token"]))
    assert resp.status_code == 403


def test_readiness_requires_assignment(client, make_user):
    psych = make_user(role="psychologist")
    stranger = make_user(role="patient")
    resp = client.get(f"/api/agents/session-readiness/{stranger['username']}", headers=_headers(psych["access_token"]))
    assert resp.status_code == 403


def test_readiness_unknown_patient(client, make_user):
    psych = make_user(role="psychologist")
    resp = client.get("/api/agents/session-readiness/ghost", headers=_headers(psych["access_token"]))
    assert resp.status_code == 404


def test_readiness_new_patient_scores_low_with_factors(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    resp = client.get(f"/api/agents/session-readiness/{patient['username']}", headers=_headers(psych["access_token"]))
    assert resp.status_code == 200
    data = resp.json()
    assert 0 <= data["score"] <= 100
    assert data["score"] < 50  # no engagement yet
    assert isinstance(data["factors"], list) and len(data["factors"]) >= 3
    for f in data["factors"]:
        assert set(["factor", "points", "max_points", "detail"]).issubset(f.keys())
    assert data["band"] in ("low", "medium", "high")


def test_readiness_active_engagement_raises_score(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    headers = _headers(patient["access_token"])

    # Active engagement: journals + moods across several days
    client.post("/api/journal", headers=headers, json={"raw_content": "day one thoughts"})
    client.post("/api/journal", headers=headers, json={"raw_content": "day two thoughts"})
    client.post("/api/journal", headers=headers, json={"raw_content": "day three reflections"})
    today = datetime.now(UTC).date()
    client.post("/api/mood", headers=headers, json={"date": today.isoformat(), "emoji": "🙂", "label": "okay"})
    client.post(
        "/api/mood",
        headers=headers,
        json={"date": (today - timedelta(days=1)).isoformat(), "emoji": "😀", "label": "good"},
    )

    base = client.get(
        f"/api/agents/session-readiness/{patient['username']}", headers=_headers(psych["access_token"])
    ).json()
    assert base["score"] >= 50

    # Completing a follow-up adds points
    client.post(
        "/api/followups",
        headers=_headers(psych["access_token"]),
        json={"patient_username": patient["username"], "title": "Breathing log"},
    )
    tasks = client.get("/api/followups", headers=headers).json()
    assert len(tasks) == 1
    client.put(f"/api/followups/{tasks[0]['id']}", headers=headers, json={"status": "completed"})

    after = client.get(
        f"/api/agents/session-readiness/{patient['username']}", headers=_headers(psych["access_token"])
    ).json()
    assert after["score"] > base["score"]


def test_readiness_recent_crisis_lowers_score(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    headers = _headers(patient["access_token"])

    # Some engagement so other factors don't dominate
    client.post("/api/journal", headers=headers, json={"raw_content": "hello world"})

    before = client.get(
        f"/api/agents/session-readiness/{patient['username']}", headers=_headers(psych["access_token"])
    ).json()

    # Trigger + resolve a crisis (recent crisis recency penalty)
    client.post("/api/crisis/trigger", headers=headers)
    client.post("/api/crisis/resolve", headers=headers)

    after = client.get(
        f"/api/agents/session-readiness/{patient['username']}", headers=_headers(psych["access_token"])
    ).json()
    assert after["score"] < before["score"]
    crisis_factor = next((f for f in after["factors"] if "crisis" in f["factor"].lower()), None)
    assert crisis_factor is not None and crisis_factor["points"] < crisis_factor["max_points"]


def test_readiness_is_deterministic(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    a = client.get(
        f"/api/agents/session-readiness/{patient['username']}", headers=_headers(psych["access_token"])
    ).json()
    b = client.get(
        f"/api/agents/session-readiness/{patient['username']}", headers=_headers(psych["access_token"])
    ).json()
    assert a["score"] == b["score"]
    assert a["factors"] == b["factors"]
