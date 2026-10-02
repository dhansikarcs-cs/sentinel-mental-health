"""AI features: reflect-prompt (patient), weekly-theme (patient+psych),
next-session-prep (clinician).

House AI contract: versioned prompt first, deterministic rule-based fallback
when no model answers — so tests assert the rule-based behavior (the test
env stubs the AI out) plus guards and ownership clamps.
"""


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── reflect-prompt ───────────────────────────────────────────────


def test_reflect_prompt_requires_patient(client, make_user):
    psych = make_user(role="psychologist")
    resp = client.get("/api/agents/reflect-prompt", headers=_headers(psych["access_token"]))
    assert resp.status_code == 403


def test_reflect_prompt_fresh_patient(client, make_user):
    patient = make_user(role="patient")
    resp = client.get("/api/agents/reflect-prompt", headers=_headers(patient["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["prompt"] and body["why"]
    assert body["wrote_today"] is False
    assert body["source"] in ("rule", "ai")


def test_reflect_prompt_reacts_to_low_mood(client, make_user):
    from datetime import UTC, datetime

    patient = make_user(role="patient")
    client.post(
        "/api/mood",
        headers=_headers(patient["access_token"]),
        json={"date": datetime.now(UTC).date().isoformat(), "emoji": "😞", "label": "bad"},
    )
    resp = client.get("/api/agents/reflect-prompt", headers=_headers(patient["access_token"]))
    body = resp.json()
    assert body["mood"] == "bad"
    assert "tomorrow" in body["prompt"].lower() or "heavy" in body["prompt"].lower()


def test_reflect_prompt_after_writing_today(client, make_user):
    patient = make_user(role="patient")
    client.post("/api/journal", headers=_headers(patient["access_token"]), json={"raw_content": "a decent day overall"})
    resp = client.get("/api/agents/reflect-prompt", headers=_headers(patient["access_token"]))
    body = resp.json()
    assert body["wrote_today"] is True


# ── weekly-theme ─────────────────────────────────────────────────


def test_weekly_theme_patient_cannot_read_others(client, make_user):
    a = make_user(role="patient")
    b = make_user(role="patient")
    resp = client.get(f"/api/agents/weekly-theme/{b['username']}", headers=_headers(a["access_token"]))
    assert resp.status_code == 403
    # Own theme is fine
    resp = client.get(f"/api/agents/weekly-theme/{a['username']}", headers=_headers(a["access_token"]))
    assert resp.status_code == 200


def test_weekly_theme_requires_assignment(client, make_user):
    psych = make_user(role="psychologist")
    stranger = make_user(role="patient")
    resp = client.get(f"/api/agents/weekly-theme/{stranger['username']}", headers=_headers(psych["access_token"]))
    assert resp.status_code == 403


def test_weekly_theme_empty_and_heavy_weeks(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    empty = client.get(
        f"/api/agents/weekly-theme/{patient['username']}", headers=_headers(psych["access_token"])
    ).json()
    assert empty["entries"] == 0

    client.post(
        "/api/journal",
        headers=_headers(patient["access_token"]),
        json={"raw_content": "so anxious about exams, feeling overwhelmed and stressed all week"},
    )
    resp = client.get(f"/api/agents/weekly-theme/{patient['username']}", headers=_headers(psych["access_token"]))
    body = resp.json()
    assert body["entries"] == 1
    assert body["theme"] and body["tone"] in ("positive", "mixed", "heavy")
    assert body["tone"] == "heavy"


def test_weekly_theme_positive(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    client.post(
        "/api/journal",
        headers=_headers(patient["access_token"]),
        json={"raw_content": "genuinely happy today, proud of myself and grateful for my friends"},
    )
    body = client.get(f"/api/agents/weekly-theme/{patient['username']}", headers=_headers(psych["access_token"])).json()
    assert body["tone"] == "positive"


# ── next-session-prep ────────────────────────────────────────────


def test_prep_requires_clinician(client, make_user):
    patient = make_user(role="patient")
    resp = client.get(f"/api/agents/next-session-prep/{patient['username']}", headers=_headers(patient["access_token"]))
    assert resp.status_code == 403


def test_prep_requires_assignment(client, make_user):
    psych = make_user(role="psychologist")
    stranger = make_user(role="patient")
    resp = client.get(f"/api/agents/next-session-prep/{stranger['username']}", headers=_headers(psych["access_token"]))
    assert resp.status_code == 403


def test_prep_baseline_and_agenda(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    ph = _headers(patient["access_token"])

    base = client.get(
        f"/api/agents/next-session-prep/{patient['username']}", headers=_headers(psych["access_token"])
    ).json()
    assert 3 <= len(base["agenda"]) <= 4
    assert base["opening_question"] and base["watch_for"]
    assert base["context"]["journals_7d"] == 0
    assert base["context"]["crisis"] is False

    # Context flows into the agenda: pending follow-up + journal + crisis
    client.post(
        "/api/followups",
        headers=_headers(psych["access_token"]),
        json={"patient_username": patient["username"], "title": "Breathing log"},
    )
    client.post("/api/journal", headers=ph, json={"raw_content": "rough night, anxious morning"})
    client.post("/api/crisis/trigger", headers=ph)
    client.post("/api/crisis/resolve", headers=ph)

    after = client.get(
        f"/api/agents/next-session-prep/{patient['username']}", headers=_headers(psych["access_token"])
    ).json()
    assert after["context"]["pending_followups"] == 1
    assert after["context"]["journals_7d"] == 1
    assert any("follow-up" in a.lower() for a in after["agenda"])
