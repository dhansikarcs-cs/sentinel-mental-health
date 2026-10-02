"""Patient week-summary + clinician next-free-slots endpoints."""

from datetime import UTC, datetime, timedelta


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── week summary ─────────────────────────────────────────────────


def test_week_summary_requires_auth_shape(client, make_user):
    patient = make_user(role="patient")
    resp = client.get("/api/patients/me/week-summary", headers=_headers(patient["access_token"]))
    assert resp.status_code == 200
    body = resp.json()["data"]
    for key in ("journals_7d", "moods_7d", "checkins_7d", "trend", "top_emotions", "next_session"):
        assert key in body


def test_week_summary_counts_and_trend(client, make_user, db_session):
    from app.models.journal import JournalEntry

    patient = make_user(role="patient")
    h = _headers(patient["access_token"])

    client.post("/api/journal", headers=h, json={"raw_content": "monday thoughts"})
    client.post("/api/journal", headers=h, json={"raw_content": "tuesday thoughts"})
    client.post(
        "/api/mood",
        headers=h,
        json={"date": datetime.now(UTC).date().isoformat(), "emoji": "😀", "label": "great"},
    )
    # Last week: 1 journal
    db_session.add(
        JournalEntry(
            patient_username=patient["username"],
            raw_content="old",
            summary="old",
            clinical_summary="old",
            timestamp=(datetime.now(UTC) - timedelta(days=10)).isoformat(),
        )
    )
    db_session.commit()

    body = client.get("/api/patients/me/week-summary", headers=h).json()["data"]
    assert body["journals_7d"] == 2
    assert body["journals_prev"] == 1
    assert body["checkins_7d"] == 3
    assert body["trend"] == "up"
    assert body["positive_days"] == 1
    assert body["best_day"]["label"] == "great"


def test_week_summary_next_session(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    future = (datetime.now(UTC).date() + timedelta(days=3)).isoformat()
    r = client.post(
        "/api/bookings",
        headers=_headers(patient["access_token"]),
        json={
            "psychologist_username": psych["username"],
            "date": future,
            "time": "10:00",
            "session_type": "T",
            "members": "",
            "contact": "x",
            "explanation": "e",
        },
    )
    bid = r.json()["id"]
    client.put(f"/api/bookings/{bid}/status", headers=_headers(psych["access_token"]), json={"status": "Approved"})

    body = client.get("/api/patients/me/week-summary", headers=_headers(patient["access_token"])).json()["data"]
    assert body["next_session"] == {"date": future, "time": "10:00"}


# ── next free slots ──────────────────────────────────────────────


def test_next_free_skips_taken_and_steps_window(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    # One window 10:00-12:30 tomorrow
    day = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    client.post(
        "/api/bookings/availability",
        headers=_headers(psych["access_token"]),
        json={"date": day, "start_time": "10:00", "end_time": "12:30"},
    )

    # Take 10:00 and 10:30
    for t in ("10:00", "10:30"):
        r = client.post(
            "/api/bookings",
            headers=_headers(patient["access_token"]),
            json={
                "psychologist_username": psych["username"],
                "date": day,
                "time": t,
                "session_type": "T",
                "members": "",
                "contact": "x",
                "explanation": "e",
            },
        )
        assert r.status_code in (200, 201), r.text

    resp = client.get(f"/api/bookings/next-free/{psych['username']}?count=3", headers=_headers(patient["access_token"]))
    slots = resp.json()["free_slots"]
    # 10:00/10:30 taken; 12:00 can't fit (12:00+60m > 12:30 end) → only 11:00, 11:30
    assert len(slots) == 2
    assert all(s["date"] == day for s in slots)
    times = [s["time"] for s in slots]
    assert "10:00" not in times and "10:30" not in times
    assert times[0] == "11:00" and times[1] == "11:30"


def test_next_free_ignores_past_dates(client, make_user):
    psych = make_user(role="psychologist")
    past = (datetime.now(UTC).date() - timedelta(days=2)).isoformat()
    client.post(
        "/api/bookings/availability",
        headers=_headers(psych["access_token"]),
        json={"date": past, "start_time": "09:00", "end_time": "17:00"},
    )
    resp = client.get(f"/api/bookings/next-free/{psych['username']}", headers=_headers(psych["access_token"]))
    assert resp.json()["free_slots"] == []
