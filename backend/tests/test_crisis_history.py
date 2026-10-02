"""Doctor feature: per-patient crisis history endpoint.

GET /crisis/history/{patient} reconstructs crisis episodes from the event
log (triggered → resolved pairs), computes durations and outcome stats, and
is restricted to the assigned psychologist (or admin).
"""

from datetime import UTC, datetime, timedelta


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_episodes(client, patient_token: str, psych_username: str, n: int, durations_s: list[int]) -> None:
    """Create n closed crisis episodes by trigger/resolve cycles."""
    for i in range(n):
        client.post("/api/crisis/trigger", headers=_headers(patient_token))
        if i < len(durations_s):
            # Backdate the trigger so the duration is deterministic.
            from app.core.database import SessionLocal
            from app.models.crisis import CrisisLog

            session = SessionLocal()
            try:
                past = datetime.now(UTC) - timedelta(seconds=durations_s[i])
                row = (
                    session.query(CrisisLog)
                    .filter(CrisisLog.event == "triggered", CrisisLog.patient == psych_username or True)
                    .order_by(CrisisLog.id.desc())
                    .first()
                )
                if row:
                    row.timestamp = past.isoformat()
                    session.commit()
            finally:
                session.close()
        client.post("/api/crisis/resolve", headers=_headers(patient_token))


def test_history_requires_psych_role(client, make_user):
    patient = make_user(role="patient")
    resp = client.get(f"/api/crisis/history/{patient['username']}", headers=_headers(patient["access_token"]))
    assert resp.status_code == 403


def test_history_requires_assignment(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")  # assigned to nobody
    resp = client.get(f"/api/crisis/history/{patient['username']}", headers=_headers(psych["access_token"]))
    assert resp.status_code == 403


def test_history_unknown_patient_404(client, make_user):
    psych = make_user(role="psychologist")
    resp = client.get("/api/crisis/history/ghost_user", headers=_headers(psych["access_token"]))
    assert resp.status_code == 404


def test_history_empty(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    resp = client.get(f"/api/crisis/history/{patient['username']}", headers=_headers(psych["access_token"]))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["episodes"] == []
    assert data["stats"]["total_episodes"] == 0
    assert data["stats"]["avg_duration_seconds"] == 0


def test_history_single_episode(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    client.post("/api/crisis/trigger", headers=_headers(patient["access_token"]))
    _backdate_last_trigger(client, 120)
    client.post("/api/crisis/resolve", headers=_headers(patient["access_token"]))

    resp = client.get(f"/api/crisis/history/{patient['username']}", headers=_headers(psych["access_token"]))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["stats"]["total_episodes"] == 1
    assert data["stats"]["active"] == 0
    assert 110 <= data["episodes"][0]["duration_seconds"] <= 200
    assert data["stats"]["longest_duration_seconds"] == data["episodes"][0]["duration_seconds"]


def _backdate_last_trigger(client, seconds: int) -> None:
    """Backdate the most recent 'triggered' CrisisLog row for deterministic durations."""
    from app.core.database import SessionLocal
    from app.models.crisis import CrisisLog

    session = SessionLocal()
    try:
        row = session.query(CrisisLog).filter(CrisisLog.event == "triggered").order_by(CrisisLog.id.desc()).first()
        assert row is not None
        row.timestamp = (datetime.now(UTC) - timedelta(seconds=seconds)).isoformat()
        session.commit()
    finally:
        session.close()


def test_history_multiple_episodes_and_patient_resolved_stat(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    # Episode 1: patient resolves it themselves (60s)
    client.post("/api/crisis/trigger", headers=_headers(patient["access_token"]))
    _backdate_last_trigger(client, 60)
    client.post("/api/crisis/resolve", headers=_headers(patient["access_token"]))

    # Episode 2: psychologist resolves it (300s)
    client.post("/api/crisis/trigger", headers=_headers(patient["access_token"]))
    _backdate_last_trigger(client, 300)
    client.post("/api/crisis/resolve", headers=_headers(psych["access_token"]))

    resp = client.get(f"/api/crisis/history/{patient['username']}", headers=_headers(psych["access_token"]))
    data = resp.json()["data"]
    assert data["stats"]["total_episodes"] == 2
    assert data["stats"]["resolved_by_patient"] == 1
    # Most recent first
    assert data["episodes"][0]["duration_seconds"] >= data["episodes"][1]["duration_seconds"]
    expected_avg = (60 + 300) // 2
    assert abs(data["stats"]["avg_duration_seconds"] - expected_avg) <= 3


def test_history_shows_active_episode(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    client.post("/api/crisis/trigger", headers=_headers(patient["access_token"]))

    resp = client.get(f"/api/crisis/history/{patient['username']}", headers=_headers(psych["access_token"]))
    data = resp.json()["data"]
    assert data["stats"]["active"] == 1
    assert data["stats"]["total_episodes"] == 1
    assert data["episodes"][0]["resolved_at"] == ""
    assert data["episodes"][0]["duration_seconds"] is None
