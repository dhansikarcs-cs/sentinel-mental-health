"""Stress spikes: when did this client's stress spike, at what time and day?

The endpoint must return spikes with explicit day + time, collapse
back-to-back readings into single episodes, and scope access correctly
(patient sees own; clinician sees assigned; unauthenticated gets 401).
"""

from datetime import UTC, datetime, timedelta

from app.models.physiological_signal import PhysiologicalSignal


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_reading(db, username: str, stress: int, when: datetime, hr: int = 90):
    db.add(
        PhysiologicalSignal(
            patient_username=username,
            device_id="test_ring",
            vendor="simulated",
            heart_rate=hr,
            hrv_rmssd=30.0,
            stress=stress,
            logged_at=when.isoformat(),
        )
    )
    db.commit()


def test_spike_detection_has_day_and_time(client, make_user, db_session):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    now = datetime.now(UTC)
    # Baseline readings around 30 → threshold = max(55, median+18) = 55ish
    for d in range(1, 15):
        _seed_reading(db_session, patient["username"], 28 + (d % 5), now - timedelta(days=d, hours=2))
    # Two spikes: one severe (88) mid-afternoon, one moderate (60) yesterday
    severe = (now - timedelta(days=3)).replace(hour=14, minute=30)
    _seed_reading(db_session, patient["username"], 88, severe)
    _seed_reading(db_session, patient["username"], 60, now - timedelta(days=1, hours=1))

    resp = client.get(
        f"/api/physio/stress-spikes/{patient['username']}?days=30", headers=_headers(psych["access_token"])
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["reading_count"] >= 15
    assert data["baseline"] is not None
    assert data["threshold"] >= 55
    assert len(data["spikes"]) >= 2

    top = max(data["spikes"], key=lambda s: s["stress"])
    assert top["stress"] >= data["threshold"]
    assert top["day"], "spike must carry a human day label"
    assert top["time"], "spike must carry a time of day"
    assert top["weekday"] in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    assert top["severity"] in ("moderate", "high", "severe")
    assert data["worst"] is not None


def test_episode_collapsing(client, make_user, db_session):
    """Readings 30 min apart at spike level = ONE episode (the peak), not three."""
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    now = datetime.now(UTC)
    for d in range(1, 12):
        _seed_reading(db_session, patient["username"], 30, now - timedelta(days=d))
    base = now - timedelta(days=1)
    _seed_reading(db_session, patient["username"], 70, base)
    _seed_reading(db_session, patient["username"], 85, base + timedelta(minutes=30))
    _seed_reading(db_session, patient["username"], 75, base + timedelta(minutes=60))

    resp = client.get(f"/api/physio/stress-spikes/{patient['username']}", headers=_headers(psych["access_token"]))
    data = resp.json()["data"]
    assert len(data["spikes"]) == 1
    assert data["spikes"][0]["stress"] == 85  # the peak survives, not the first/last


def test_patient_sees_own_spikes(client, make_user, db_session):
    patient = make_user(role="patient")
    now = datetime.now(UTC)
    for d in range(1, 10):  # baseline so the spike stands out
        _seed_reading(db_session, patient["username"], 30, now - timedelta(days=d))
    _seed_reading(db_session, patient["username"], 90, now - timedelta(hours=2))
    resp = client.get("/api/physio/stress-spikes?days=30", headers=_headers(patient["access_token"]))
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["patient"] == patient["username"]
    assert len(data["spikes"]) == 1
    assert data["spikes"][0]["stress"] == 90


def test_no_data_returns_empty_shape(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    resp = client.get(f"/api/physio/stress-spikes/{patient['username']}", headers=_headers(psych["access_token"]))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["spikes"] == []
    assert data["baseline"] is None


def test_patient_cannot_view_another_clients_spikes(client, make_user):
    make_user(role="psychologist")
    other = make_user(role="patient")
    stranger = make_user(role="patient")
    resp = client.get(f"/api/physio/stress-spikes/{other['username']}", headers=_headers(stranger["access_token"]))
    assert resp.status_code == 403  # patient role can't use the clinician route at all


def test_spikes_require_auth(client):
    assert client.get("/api/physio/stress-spikes").status_code == 401


def test_ring_sensor_log_readings_are_included(client, make_user, db_session):
    """The legacy RingSensorLog table (what devices + seed data write into)
    must also feed spike detection, not just PhysiologicalSignal."""
    from app.models.ring import RingSensorLog

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    now = datetime.now(UTC)
    for d in range(1, 15):
        db_session.add(
            RingSensorLog(
                patient_username=patient["username"],
                device_id="ring_test",
                bpm=76,
                stress=30 + (d % 5),
                hrv=40,
                logged_at=(now - timedelta(days=d)).isoformat(),
            )
        )
    spike_time = (now - timedelta(days=2)).replace(hour=16, minute=45)
    db_session.add(
        RingSensorLog(
            patient_username=patient["username"],
            device_id="ring_test",
            bpm=95,
            stress=84,
            hrv=18,
            logged_at=spike_time.isoformat(),
        )
    )
    db_session.commit()

    resp = client.get(
        f"/api/physio/stress-spikes/{patient['username']}?days=30",
        headers=_headers(psych["access_token"]),
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["reading_count"] >= 15
    assert len(body["spikes"]) == 1
    s = body["spikes"][0]
    assert s["stress"] == 84
    assert s["time"] == "16:45"
    assert s["weekday"] == spike_time.strftime("%A")


def test_hourly_and_daily_aggregates_present(client, make_user, db_session):
    """The insights graph needs an hourly profile (24 slots) and a day-by-day
    list with avg/peak/peak_time, even when some hours have no readings."""
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    now = datetime.now(UTC)
    # Readings at 09:15 and 14:45 on three different days
    for d in (1, 2, 3):
        for hr, mn in ((9, 15), (14, 45)):
            _seed_reading(
                db_session, patient["username"], 40 + d, (now - timedelta(days=d)).replace(hour=hr, minute=mn)
            )

    resp = client.get(
        f"/api/physio/stress-spikes/{patient['username']}?days=30",
        headers=_headers(psych["access_token"]),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert len(data["hourly"]) == 24
    h9 = next(h for h in data["hourly"] if h["hour"] == 9)
    h14 = next(h for h in data["hourly"] if h["hour"] == 14)
    assert h9["n"] == 3 and h14["n"] == 3
    assert h9["avg"] is not None and h9["max"] is not None
    empty = next(h for h in data["hourly"] if h["hour"] == 3)
    assert empty["avg"] is None and empty["n"] == 0

    assert len(data["daily"]) == 3
    d1 = data["daily"][0]
    assert d1["n"] == 2
    assert d1["peak"] >= d1["avg"]
    assert len(d1["peak_time"]) == 5  # "HH:MM"
