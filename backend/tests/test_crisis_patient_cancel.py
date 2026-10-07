"""Regression: a patient MUST be able to cancel their own active crisis.

Bug: POST /crisis/resolve required the psychologist role, so the patient's
"I'm safe — cancel crisis" button always failed with 403 and the crisis kept
escalating (trusted contact at 30s, helpline at 60s) with no way to stop it.
"""

import pytest

from conftest import auth_headers


@pytest.fixture()
def patient_a(make_user):
    return make_user(role="patient")


@pytest.fixture()
def patient_b(make_user):
    return make_user(role="patient")


def test_patient_can_cancel_own_crisis(client, patient_a):
    """The core bug: patient triggers a crisis, then cancels it themselves."""
    h = auth_headers(patient_a["access_token"])

    assert client.post("/api/crisis/trigger", headers=h).status_code == 200

    state = client.get("/api/crisis/state", headers=h).json()
    assert state["active"] is True, "crisis should be active after trigger"

    # THE FIX: patient resolving their own crisis must succeed (was 403 before).
    r = client.post("/api/crisis/resolve", headers=h)
    assert r.status_code == 200, f"patient cancel failed: {r.status_code} {r.text[:200]}"

    state = client.get("/api/crisis/state", headers=h).json()
    assert state["active"] is False, "crisis must no longer be active after cancel"
    assert client.get("/api/crisis/elapsed", headers=h).json()["is_active"] is False


def test_patient_cannot_cancel_someone_elses_crisis(client, patient_a, patient_b):
    """Ownership clamp: a patient must not resolve another patient's crisis.

    Patient requests are scoped to their own state row (any ?patient= param is
    ignored), so a cross-patient resolve is a harmless no-op for the caller and
    leaves the other patient's crisis fully active.
    """
    h_a = auth_headers(patient_a["access_token"])
    h_b = auth_headers(patient_b["access_token"])

    client.post("/api/crisis/trigger", headers=h_a)
    r = client.post("/api/crisis/resolve?patient=" + patient_a["username"], headers=h_b)
    assert r.status_code == 200, r.text  # no-op on patient_b's own (inactive) row

    state = client.get("/api/crisis/state", headers=h_a).json()
    assert state["active"] is True, "patient_b must not be able to cancel patient_a's crisis"

    client.post("/api/crisis/resolve", headers=h_a)  # cleanup


def test_psychologist_can_still_resolve_any_crisis(client, patient_a, make_user):
    """Existing behavior preserved: psychologist resolves a patient's crisis."""
    h_p = auth_headers(patient_a["access_token"])
    psych = make_user(role="psychologist")
    h_d = auth_headers(psych["access_token"])

    client.post("/api/crisis/trigger", headers=h_p)
    r = client.post("/api/crisis/resolve", headers=h_d)
    assert r.status_code == 200, f"psych resolve failed: {r.status_code} {r.text[:200]}"

    state = client.get("/api/crisis/state", headers=h_p).json()
    assert state["active"] is False


def test_patient_can_cancel_auto_detected_crisis(client, patient_a, db_session):
    """The patient's cancel button must work for AI-detected crises too.

    Auto-detected crises set triggered_by='ai_detection' (not 'patient'), which
    used to hide the "I'm safe — cancel crisis" control in the UI. The patient
    was then locked inside an active crisis with no way out. Backend already
    permits self-cancel; the regression guards that the state is cancellable.
    """
    from app.models.crisis import CrisisState

    h = auth_headers(patient_a["access_token"])

    crisis_text = "I want to die, nobody can help me, end my life"
    client.post("/api/journal", json={"raw_content": crisis_text}, headers=h)

    state = db_session.query(CrisisState).filter(CrisisState.patient_username == patient_a["username"]).first()
    assert state is not None and state.active == 1
    assert state.triggered_by == "ai_detection", "auto-detected crisis must be tagged ai_detection"

    r = client.post("/api/crisis/resolve", headers=h)
    assert r.status_code == 200, f"patient cancel of auto crisis failed: {r.status_code} {r.text[:200]}"

    state = client.get("/api/crisis/state", headers=h).json()
    assert state["active"] is False, "auto-detected crisis must be cancellable by the patient"
