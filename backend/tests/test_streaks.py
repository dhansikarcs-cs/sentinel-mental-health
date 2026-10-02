"""Tests for the check-in streaks endpoint (GET /api/patients/me/streaks)."""

from datetime import date, timedelta

from conftest import auth_headers


def _streaks(client, h):
    r = client.get("/api/patients/me/streaks", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _log_mood(client, h, day: date):
    r = client.post("/api/mood", headers=h, json={"date": day.isoformat(), "emoji": "okay", "label": "okay"})
    assert r.status_code == 200, r.text


def test_empty_state(client, patient_user):
    d = _streaks(client, auth_headers(patient_user["access_token"]))
    assert d["current_streak"] == 0
    assert d["longest_streak"] == 0
    assert d["checked_in_today"] is False
    assert len(d["heatmap"]) == 28


def test_today_checkin_gives_streak_1(client, patient_user):
    h = auth_headers(patient_user["access_token"])
    _log_mood(client, h, date.today())
    d = _streaks(client, h)
    assert d["checked_in_today"] is True
    assert d["current_streak"] == 1
    assert d["longest_streak"] == 1


def test_streak_counts_consecutive_days(client, patient_user):
    h = auth_headers(patient_user["access_token"])
    today = date.today()
    for offset in (2, 1, 0):  # two days ago, yesterday, today
        _log_mood(client, h, today - timedelta(days=offset))
    d = _streaks(client, h)
    assert d["current_streak"] == 3
    assert d["longest_streak"] == 3


def test_gap_resets_current_not_longest(client, patient_user):
    h = auth_headers(patient_user["access_token"])
    today = date.today()
    # 4-day run ending 3 days ago, gap, then today only.
    for offset in (6, 5, 4, 3):
        _log_mood(client, h, today - timedelta(days=offset))
    _log_mood(client, h, today)
    d = _streaks(client, h)
    assert d["current_streak"] == 1
    assert d["longest_streak"] == 4


def test_streak_alive_when_today_missing_but_yesterday_present(client, patient_user):
    """No check-in yet today: the streak is still alive from yesterday."""
    h = auth_headers(patient_user["access_token"])
    today = date.today()
    for offset in (2, 1):
        _log_mood(client, h, today - timedelta(days=offset))
    d = _streaks(client, h)
    assert d["checked_in_today"] is False
    assert d["current_streak"] == 2


def test_journal_entry_counts_as_checkin(client, patient_user):
    h = auth_headers(patient_user["access_token"])
    r = client.post(
        "/api/journal",
        headers=h,
        json={
            "raw_content": "Streak test entry — feeling steady today.",
            "timestamp": date.today().isoformat() + "T09:00:00",
            "checkin": [],
        },
    )
    assert r.status_code == 200, r.text
    d = _streaks(client, h)
    assert d["checked_in_today"] is True
    assert d["current_streak"] >= 1


def test_psychologist_can_call_own_streaks(client, psych_user):
    h = auth_headers(psych_user["access_token"])
    d = _streaks(client, h)
    assert d["current_streak"] == 0
