"""Booking conflict detection + clinician calendar month view.

- Creating a booking into an already-taken slot (same psych, date, time,
  active status) returns 409.
- Rescheduling into a conflict returns 409; the moved booking itself is
  excluded from the check.
- Booking outside the clinician's availability window for that date
  returns 400.
- GET /bookings/calendar?year&month returns booked sessions grouped by
  date plus open-date windows.
"""


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mk(client, patient, psych, date: str, time: str):
    r = client.post(
        "/api/bookings",
        headers=_headers(patient["access_token"]),
        json={
            "psychologist_username": psych["username"],
            "date": date,
            "time": time,
            "session_type": "Therapy",
            "members": "",
            "contact": "p@example.com",
            "explanation": "check-in",
        },
    )
    return r


def test_double_booking_rejected(client, make_user):
    psych = make_user(role="psychologist")
    p1 = make_user(role="patient", assigned_psych=psych["username"])
    p2 = make_user(role="patient", assigned_psych=psych["username"])

    first = _mk(client, p1, psych, "2099-03-01", "10:00")
    assert first.status_code in (200, 201), first.text

    second = _mk(client, p2, psych, "2099-03-01", "10:00")
    assert second.status_code == 409
    assert "taken" in (second.json().get("message") or second.json().get("detail") or "")


def test_same_slot_different_time_ok(client, make_user):
    psych = make_user(role="psychologist")
    p1 = make_user(role="patient", assigned_psych=psych["username"])
    p2 = make_user(role="patient", assigned_psych=psych["username"])

    assert _mk(client, p1, psych, "2099-03-01", "10:00").status_code in (200, 201)
    assert _mk(client, p2, psych, "2099-03-01", "11:00").status_code in (200, 201)


def test_cancelled_slot_frees_up(client, make_user):
    psych = make_user(role="psychologist")
    p1 = make_user(role="patient", assigned_psych=psych["username"])
    p2 = make_user(role="patient", assigned_psych=psych["username"])

    first = _mk(client, p1, psych, "2099-03-01", "10:00")
    client.put(
        f"/api/bookings/{first.json()['id']}/status",
        headers=_headers(psych["access_token"]),
        json={"status": "Cancelled"},
    )

    second = _mk(client, p2, psych, "2099-03-01", "10:00")
    assert second.status_code in (200, 201)


def test_reschedule_into_conflict_rejected(client, make_user):
    psych = make_user(role="psychologist")
    p1 = make_user(role="patient", assigned_psych=psych["username"])
    p2 = make_user(role="patient", assigned_psych=psych["username"])

    _mk(client, p1, psych, "2099-03-01", "10:00")
    b2 = _mk(client, p2, psych, "2099-03-01", "11:00")

    resp = client.put(
        f"/api/bookings/{b2.json()['id']}/reschedule",
        headers=_headers(p2["access_token"]),
        json={"date": "2099-03-01", "time": "10:00"},
    )
    assert resp.status_code == 409, resp.text

    # Moving to a free slot works
    resp = client.put(
        f"/api/bookings/{b2.json()['id']}/reschedule",
        headers=_headers(p2["access_token"]),
        json={"date": "2099-03-02", "time": "10:00"},
    )
    assert resp.status_code == 200


def test_booking_outside_window_rejected(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    client.post(
        "/api/bookings/availability",
        headers=_headers(psych["access_token"]),
        json={"date": "2099-03-01", "start_time": "10:00", "end_time": "14:00"},
    )

    resp = _mk(client, patient, psych, "2099-03-01", "16:00")
    assert resp.status_code == 400
    assert "hours" in (resp.json().get("message") or resp.json().get("detail") or "")

    ok = _mk(client, patient, psych, "2099-03-01", "11:00")
    assert ok.status_code in (200, 201)


def test_calendar_month_view(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    _mk(client, patient, psych, "2099-03-01", "10:00")
    _mk(client, patient, psych, "2099-03-01", "12:00")
    _mk(client, patient, psych, "2099-03-05", "09:00")
    client.post(
        "/api/bookings/availability",
        headers=_headers(psych["access_token"]),
        json={"date": "2099-03-10", "start_time": "08:00", "end_time": "12:00"},
    )

    resp = client.get("/api/bookings/calendar?year=2099&month=3", headers=_headers(psych["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["year"] == 2099 and body["month"] == 3

    day1 = next(d for d in body["sessions"] if d["date"] == "2099-03-01")
    assert len(day1["bookings"]) == 2
    assert day1["bookings"][0]["time"] == "10:00"

    day5 = next(d for d in body["sessions"] if d["date"] == "2099-03-05")
    assert day5["bookings"][0]["patient"] == patient["username"]

    assert "2099-03-10" in body["open_dates"]

    # Other roles denied
    patient_resp = client.get("/api/bookings/calendar?year=2099&month=3", headers=_headers(patient["access_token"]))
    assert patient_resp.status_code == 403
