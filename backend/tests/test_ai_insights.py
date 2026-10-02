"""AI insights: mood forecast, journal reframe, early-warning, goal suggests.

The test env stubs the AI out, so these assert the deterministic rule-based
behavior plus auth/ownership guards — the same contract as test_ai_features.
"""


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── mood forecast ────────────────────────────────────────────────


def test_forecast_requires_patient(client, make_user):
    psych = make_user(role="psychologist")
    resp = client.get("/api/agents/mood-forecast", headers=_headers(psych["access_token"]))
    assert resp.status_code == 403


def test_forecast_empty_history(client, make_user):
    patient = make_user(role="patient")
    resp = client.get("/api/agents/mood-forecast", headers=_headers(patient["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["forecast"] == []
    assert body["basis"] == 0
    assert "check-in" in body["summary"].lower()


def test_forecast_good_streak_stays_measured(client, make_user):
    from datetime import UTC, datetime, timedelta

    patient = make_user(role="patient")
    today = datetime.now(UTC).date()
    for i in range(1, 9):  # 8 straight good days
        client.post(
            "/api/mood",
            headers=_headers(patient["access_token"]),
            json={"date": (today - timedelta(days=i)).isoformat(), "emoji": "😄", "label": "good"},
        )
    body = client.get("/api/agents/mood-forecast", headers=_headers(patient["access_token"])).json()
    assert body["basis"] == 8
    assert len(body["forecast"]) == 3
    # Regression-to-normal pull means no "perfect 3/3 great" overclaim
    assert all(f["label"] in ("good", "okay") for f in body["forecast"])
    assert body["tip"]


def test_forecast_low_stretch_signals_heavy_days(client, make_user):
    from datetime import UTC, datetime, timedelta

    patient = make_user(role="patient")
    today = datetime.now(UTC).date()
    for i in range(1, 8):
        client.post(
            "/api/mood",
            headers=_headers(patient["access_token"]),
            json={"date": (today - timedelta(days=i)).isoformat(), "emoji": "😞", "label": "bad"},
        )
    body = client.get("/api/agents/mood-forecast", headers=_headers(patient["access_token"])).json()
    assert all(f["label"] == "rough" for f in body["forecast"])
    assert "heavy" in body["summary"].lower() or "heavier" in body["summary"].lower()


# ── journal reframe ──────────────────────────────────────────────


def test_reframe_requires_ownership(client, make_user):
    a = make_user(role="patient")
    b = make_user(role="patient")
    entry = client.post(
        "/api/journal", headers=_headers(a["access_token"]), json={"raw_content": "I always ruin everything"}
    ).json()
    entry_id = entry["id"] if isinstance(entry, dict) and "id" in entry else entry.get("entry", {}).get("id")
    resp = client.get(f"/api/agents/journal-reframe/{entry_id}", headers=_headers(b["access_token"]))
    assert resp.status_code == 404  # other people's entries don't exist for you


def test_reframe_detects_absolutist_trap(client, make_user):
    patient = make_user(role="patient")
    entry = client.post(
        "/api/journal",
        headers=_headers(patient["access_token"]),
        json={"raw_content": "I never do anything right, everyone is ahead of me"},
    ).json()
    entry_id = entry["id"] if isinstance(entry, dict) and "id" in entry else entry.get("entry", {}).get("id")
    body = client.get(f"/api/agents/journal-reframe/{entry_id}", headers=_headers(patient["access_token"])).json()
    assert "All-or-nothing" in body["trap"]
    assert body["reframe"] and body["affirmation"]
    assert "not therapy" in body["disclaimer"].lower()
    assert body["source"] in ("rule", "ai")


def test_reframe_detects_should_trap(client, make_user):
    patient = make_user(role="patient")
    entry = client.post(
        "/api/journal",
        headers=_headers(patient["access_token"]),
        json={"raw_content": "I should be over this by now, I must do better"},
    ).json()
    entry_id = entry["id"] if isinstance(entry, dict) and "id" in entry else entry.get("entry", {}).get("id")
    body = client.get(f"/api/agents/journal-reframe/{entry_id}", headers=_headers(patient["access_token"])).json()
    assert "should" in body["trap"].lower()


def test_reframe_missing_entry_404(client, make_user):
    patient = make_user(role="patient")
    resp = client.get("/api/agents/journal-reframe/999999", headers=_headers(patient["access_token"]))
    assert resp.status_code == 404


# ── early warning (clinician) ────────────────────────────────────


def test_early_warning_patient_sees_own_signals(client, make_user):
    """Patients get self-insight: their own signals, nothing else."""
    patient = make_user(role="patient")
    resp = client.get(f"/api/agents/early-warning/{patient['username']}", headers=_headers(patient["access_token"]))
    assert resp.status_code == 200
    assert "signals" in resp.json()


def test_early_warning_patient_cannot_read_others(client, make_user):
    patient = make_user(role="patient")
    other = make_user(role="patient")
    resp = client.get(f"/api/agents/early-warning/{other['username']}", headers=_headers(patient["access_token"]))
    assert resp.status_code == 403


def test_early_warning_requires_assignment(client, make_user):
    psych = make_user(role="psychologist")
    stranger = make_user(role="patient")
    resp = client.get(f"/api/agents/early-warning/{stranger['username']}", headers=_headers(psych["access_token"]))
    assert resp.status_code == 403


def test_early_warning_steady_patient(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    from datetime import UTC, datetime

    client.post(
        "/api/mood",
        headers=_headers(patient["access_token"]),
        json={"date": datetime.now(UTC).date().isoformat(), "emoji": "🙂", "label": "okay"},
    )
    body = client.get(
        f"/api/agents/early-warning/{patient['username']}", headers=_headers(psych["access_token"])
    ).json()
    assert body["overall"] in ("steady", "watch", "urgent")
    assert body["signals"]
    assert all("evidence" in s for s in body["signals"])
    assert "diagnosis" in body["disclaimer"].lower()


def test_early_warning_flags_sustained_low_mood(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    from datetime import UTC, datetime, timedelta

    today = datetime.now(UTC).date()
    for i in range(1, 8):
        client.post(
            "/api/mood",
            headers=_headers(patient["access_token"]),
            json={"date": (today - timedelta(days=i)).isoformat(), "emoji": "😞", "label": "bad"},
        )
    body = client.get(
        f"/api/agents/early-warning/{patient['username']}", headers=_headers(psych["access_token"])
    ).json()
    kinds = [s["signal"] for s in body["signals"]]
    assert any("low mood" in k.lower() for k in kinds)
    assert body["overall"] in ("watch", "urgent")


# ── goal suggestions ─────────────────────────────────────────────


def test_goal_suggestions_fresh_patient(client, make_user):
    patient = make_user(role="patient")
    body = client.get("/api/agents/goal-suggestions", headers=_headers(patient["access_token"])).json()
    assert len(body["suggestions"]) == 3
    assert all(s["title"] and s["why"] for s in body["suggestions"])
    assert body["source"] in ("rule", "ai")


def test_goal_suggestions_react_to_anxiety(client, make_user):
    from datetime import UTC, datetime

    patient = make_user(role="patient")
    client.post(
        "/api/mood",
        headers=_headers(patient["access_token"]),
        json={"date": datetime.now(UTC).date().isoformat(), "emoji": "😖", "label": "anxious"},
    )
    body = client.get("/api/agents/goal-suggestions", headers=_headers(patient["access_token"])).json()
    joined = " ".join(s["title"] + " " + s["why"] for s in body["suggestions"]).lower()
    assert "breath" in joined or "worry" in joined


def test_goal_suggestions_requires_patient(client, make_user):
    psych = make_user(role="psychologist")
    resp = client.get("/api/agents/goal-suggestions", headers=_headers(psych["access_token"]))
    assert resp.status_code == 403
