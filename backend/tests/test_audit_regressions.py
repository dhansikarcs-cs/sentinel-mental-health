"""Regression tests for the QA audit confirmed bugs.

Covered:
- B7/B8  offline-synced journals must enter the AI analysis pipeline
- B9/B10 re-summarizing a journal must not duplicate analysis rows
- B11    "emergency" must not false-trigger crisis (routine ER visits)
- B13    bookings reject non-calendar dates / non-clock times
- B15    follow-up status must not reset when only grade/feedback is sent
"""

import uuid
from datetime import UTC, datetime

from app.ml.risk_engine import assess_risk_with_explainability


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _ts() -> str:
    return datetime.now(UTC).isoformat()


# ── B7/B8: offline sync runs the AI pipeline ─────────────────────────────────


def test_offline_synced_journal_is_ai_analyzed(client, patient_user, db_session):
    from app.models.ai_analysis import AIAnalysis
    from app.models.emotion_result import EmotionResult
    from app.models.journal import JournalEntry
    from app.models.risk_assessment import RiskAssessment

    entry = {
        "raw_content": f"offline entry {uuid.uuid4().hex[:6]} — feeling tired but okay",
        "timestamp": _ts(),
        "client_id": f"c-{uuid.uuid4().hex}",
    }
    resp = client.post("/api/sync/journals", json=[entry], headers=_auth(patient_user["access_token"]))
    assert resp.status_code == 200, resp.text
    journal_id = resp.json()["synced"][0]["server_id"]

    row = db_session.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    assert row is not None
    assert row.ai_source != "pending", "offline journal was never analyzed"
    assert db_session.query(EmotionResult).filter(EmotionResult.journal_id == journal_id).count() == 1
    assert db_session.query(AIAnalysis).filter(AIAnalysis.journal_id == journal_id).count() == 1
    risk = db_session.query(RiskAssessment).filter(RiskAssessment.journal_id == journal_id).first()
    assert risk is not None and 1 <= risk.risk_score <= 10


def test_offline_synced_crisis_journal_flags_risk(client, patient_user, db_session):
    from app.models.risk_assessment import RiskAssessment

    entry = {
        "raw_content": "I want to kill myself tonight, end my life",
        "timestamp": _ts(),
        "client_id": f"c-{uuid.uuid4().hex}",
    }
    resp = client.post("/api/sync/journals", json=[entry], headers=_auth(patient_user["access_token"]))
    assert resp.status_code == 200, resp.text
    journal_id = resp.json()["synced"][0]["server_id"]

    risk = db_session.query(RiskAssessment).filter(RiskAssessment.journal_id == journal_id).first()
    assert risk is not None
    assert risk.triggered == 1
    assert risk.risk_score == 10


# ── B9/B10: resummarize is idempotent ────────────────────────────────────────


def test_resummarize_does_not_duplicate_analysis_rows(client, patient_user, db_session):
    from app.models.ai_analysis import AIAnalysis
    from app.models.emotion_result import EmotionResult
    from app.models.risk_assessment import RiskAssessment

    created = client.post(
        "/api/journal",
        json={"raw_content": f"steady day {uuid.uuid4().hex[:6]}, calm and fine"},
        headers=_auth(patient_user["access_token"]),
    )
    assert created.status_code == 200, created.text
    journal_id = created.json()["id"]

    def counts():
        return {
            "emotion": db_session.query(EmotionResult).filter(EmotionResult.journal_id == journal_id).count(),
            "analysis": db_session.query(AIAnalysis).filter(AIAnalysis.journal_id == journal_id).count(),
            "risk": db_session.query(RiskAssessment).filter(RiskAssessment.journal_id == journal_id).count(),
        }

    assert counts() == {"emotion": 1, "analysis": 1, "risk": 1}

    for _ in range(2):
        resp = client.post(
            f"/api/journal/{journal_id}/resummarize",
            headers=_auth(patient_user["access_token"]),
        )
        assert resp.status_code == 200, resp.text

    assert counts() == {"emotion": 1, "analysis": 1, "risk": 1}


def test_resummarize_denied_for_unassigned_psych(client, make_user):
    owner = make_user(role="patient")
    outsider = make_user(role="psychologist")
    created = client.post(
        "/api/journal",
        json={"raw_content": f"entry {uuid.uuid4().hex[:6]}"},
        headers=_auth(owner["access_token"]),
    )
    assert created.status_code == 200
    resp = client.post(
        f"/api/journal/{created.json()['id']}/resummarize",
        headers=_auth(outsider["access_token"]),
    )
    assert resp.status_code == 403


# ── B11: "emergency" must not be a crisis keyword ────────────────────────────


def test_emergency_room_visit_does_not_trigger_crisis():
    result = assess_risk_with_explainability("I went to the emergency room yesterday for a check-up.")
    assert result["triggered"] is False
    assert result["risk_score"] < 10
    assert result["explainability"]["keyword_signals"]["crisis_keywords"] == []


def test_explicit_suicide_language_still_triggers_crisis():
    result = assess_risk_with_explainability("I keep thinking I want to kill myself.")
    assert result["triggered"] is True
    assert result["risk_score"] == 10


# ── B13: booking date/time validation ────────────────────────────────────────


def _booking_payload(**over) -> dict:
    payload = {
        "psychologist_username": "some_psych",
        "date": "2099-01-05",
        "time": "10:00",
        "session_type": "check-in",
    }
    payload.update(over)
    return payload


def test_booking_rejects_garbage_date(client, patient_user):
    resp = client.post(
        "/api/bookings",
        json=_booking_payload(date="not-a-date"),
        headers=_auth(patient_user["access_token"]),
    )
    assert resp.status_code == 422, resp.text


def test_booking_rejects_impossible_calendar_date(client, patient_user):
    resp = client.post(
        "/api/bookings",
        json=_booking_payload(date="2026-02-30"),
        headers=_auth(patient_user["access_token"]),
    )
    assert resp.status_code == 422, resp.text


def test_booking_rejects_garbage_time(client, patient_user):
    resp = client.post(
        "/api/bookings",
        json=_booking_payload(time="25:99"),
        headers=_auth(patient_user["access_token"]),
    )
    assert resp.status_code == 422, resp.text


def test_booking_accepts_valid_date_and_time(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    resp = client.post(
        "/api/bookings",
        json=_booking_payload(psychologist_username=psych["username"]),
        headers=_auth(patient["access_token"]),
    )
    assert resp.status_code in (200, 201), resp.text  # schema passed; route-level logic may reject


# ── B15: follow-up status survives grade-only updates ────────────────────────


def test_followup_grade_only_update_keeps_completed_status(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    created = client.post(
        "/api/followups",
        json={"patient_username": patient["username"], "title": "Homework", "description": ""},
        headers=_auth(psych["access_token"]),
    )
    assert created.status_code == 200, created.text
    task_id = created.json()["id"]

    done = client.put(
        f"/api/followups/{task_id}",
        json={"status": "completed"},
        headers=_auth(patient["access_token"]),
    )
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "completed"
    assert done.json()["completed_at"]

    grade_only = client.put(
        f"/api/followups/{task_id}",
        json={"grade": "green", "feedback": "Nice work."},
        headers=_auth(psych["access_token"]),
    )
    assert grade_only.status_code == 200, grade_only.text
    assert grade_only.json()["status"] == "completed", "grade update must not reset the status"
    assert grade_only.json()["grade"] == "green"
