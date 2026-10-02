"""Booking availability time-windows, reschedule, and clinical-note filters.

- Availability carries per-date start/end time windows; patient-facing
  availability hides past dates.
- PUT /bookings/{id}/reschedule: owner (pending only) or assigned
  psychologist (any status) can move a booking.
- GET /psychologists/notes: filter by client, free text, date range,
  approval state.
"""

from datetime import UTC, datetime, timedelta


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mk_booking(client, patient, psych, date: str, time: str = "10:00") -> int:
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
            "explanation": "weekly check-in",
        },
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


# ── availability time windows ────────────────────────────────────


def test_availability_detailed_returns_time_window(client, make_user):
    psych = make_user(role="psychologist")
    future = (datetime.now(UTC) + timedelta(days=7)).date().isoformat()
    client.post(
        "/api/bookings/availability",
        headers=_headers(psych["access_token"]),
        json={"date": future, "start_time": "10:00", "end_time": "14:00"},
    )

    resp = client.get("/api/bookings/availability/me?detailed=true", headers=_headers(psych["access_token"]))
    slots = resp.json()
    assert len(slots) == 1
    assert slots[0]["date"] == future
    assert slots[0]["start_time"] == "10:00"
    assert slots[0]["end_time"] == "14:00"


def test_availability_default_window(client, make_user):
    psych = make_user(role="psychologist")
    future = (datetime.now(UTC) + timedelta(days=7)).date().isoformat()
    client.post("/api/bookings/availability", headers=_headers(psych["access_token"]), json={"date": future})
    slots = client.get("/api/bookings/availability/me?detailed=true", headers=_headers(psych["access_token"])).json()
    assert slots[0]["start_time"] == "09:00"
    assert slots[0]["end_time"] == "17:00"


def test_patient_availability_hides_past_dates(client, make_user):
    psych = make_user(role="psychologist")
    past = (datetime.now(UTC) - timedelta(days=7)).date().isoformat()
    future = (datetime.now(UTC) + timedelta(days=7)).date().isoformat()
    client.post("/api/bookings/availability", headers=_headers(psych["access_token"]), json={"date": past})
    client.post("/api/bookings/availability", headers=_headers(psych["access_token"]), json={"date": future})

    dates = client.get(f"/api/bookings/availability/{psych['username']}").json()
    assert future in [d["date"] for d in dates]
    assert past not in [d["date"] for d in dates]
    assert all("start" in d and "end" in d for d in dates)


# ── reschedule ───────────────────────────────────────────────────


def test_patient_can_reschedule_pending_booking(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    bid = _mk_booking(client, patient, psych, "2099-01-01", "10:00")

    resp = client.put(
        f"/api/bookings/{bid}/reschedule",
        headers=_headers(patient["access_token"]),
        json={"date": "2099-01-05", "time": "15:00"},
    )
    assert resp.status_code == 200, resp.text
    assert "2099-01-05" in resp.json()["message"]

    bookings = client.get("/api/bookings", headers=_headers(patient["access_token"])).json()
    moved = next(b for b in bookings if b["id"] == bid)
    assert moved["date"] == "2099-01-05" and moved["time"] == "15:00"


def test_patient_cannot_reschedule_approved(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    bid = _mk_booking(client, patient, psych, "2099-01-01")
    client.put(f"/api/bookings/{bid}/status", headers=_headers(psych["access_token"]), json={"status": "Approved"})

    resp = client.put(
        f"/api/bookings/{bid}/reschedule",
        headers=_headers(patient["access_token"]),
        json={"date": "2099-01-05", "time": "15:00"},
    )
    assert resp.status_code == 403


def test_psych_can_reschedule_any_of_theirs(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    bid = _mk_booking(client, patient, psych, "2099-01-01")
    client.put(f"/api/bookings/{bid}/status", headers=_headers(psych["access_token"]), json={"status": "Approved"})

    resp = client.put(
        f"/api/bookings/{bid}/reschedule",
        headers=_headers(psych["access_token"]),
        json={"date": "2099-02-02", "time": "11:00"},
    )
    assert resp.status_code == 200

    bookings = client.get("/api/bookings", headers=_headers(psych["access_token"])).json()
    moved = next(b for b in bookings if b["id"] == bid)
    assert moved["date"] == "2099-02-02"
    assert moved["status"] == "Pending"  # moved appointment needs re-confirmation


def test_stranger_cannot_reschedule(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    stranger = make_user(role="patient")
    bid = _mk_booking(client, patient, psych, "2099-01-01")

    resp = client.put(
        f"/api/bookings/{bid}/reschedule",
        headers=_headers(stranger["access_token"]),
        json={"date": "2099-01-05", "time": "15:00"},
    )
    assert resp.status_code == 403


# ── clinical notes filters ───────────────────────────────────────


def _mk_notes(client, psych, patient) -> dict:
    client.post(
        "/api/psychologists/notes",
        headers=_headers(psych["access_token"]),
        json={"patient_username": patient["username"], "raw_notes": "Discussed exam anxiety and breathing exercises"},
    )
    client.post(
        "/api/psychologists/notes",
        headers=_headers(psych["access_token"]),
        json={"patient_username": patient["username"], "raw_notes": "Sleep hygiene plan agreed"},
    )
    notes = client.get("/api/psychologists/notes", headers=_headers(psych["access_token"])).json()
    return {n["raw_notes"][:20]: n for n in notes}


def test_notes_filters(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    other = make_user(role="patient", assigned_psych=psych["username"])
    made = _mk_notes(client, psych, patient)
    client.post(
        "/api/psychologists/notes",
        headers=_headers(psych["access_token"]),
        json={"patient_username": other["username"], "raw_notes": "Other client note"},
    )
    ids = {n["id"] for n in made.values()}

    hdrs = _headers(psych["access_token"])

    # By client
    resp = client.get(f"/api/psychologists/notes?patient={patient['username']}", headers=hdrs)
    assert {n["id"] for n in resp.json()} == ids

    # Free text (decrypted content)
    resp = client.get("/api/psychologists/notes?q=sleep", headers=hdrs)
    assert len(resp.json()) == 1 and "Sleep" in resp.json()[0]["raw_notes"]

    # Approval state
    note_id = list(ids)[0]
    client.put(f"/api/psychologists/notes/{note_id}/approve", headers=hdrs)
    approved = client.get("/api/psychologists/notes?approved=yes", headers=hdrs).json()
    unapproved = client.get("/api/psychologists/notes?approved=no", headers=hdrs).json()
    assert [n["id"] for n in approved] == [note_id]
    assert note_id not in [n["id"] for n in unapproved]


def test_notes_scoped_to_owner(client, make_user):
    psych_a = make_user(role="psychologist")
    psych_b = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych_a["username"])
    client.post(
        "/api/psychologists/notes",
        headers=_headers(psych_a["access_token"]),
        json={"patient_username": patient["username"], "raw_notes": "private note"},
    )

    resp = client.get("/api/psychologists/notes", headers=_headers(psych_b["access_token"]))
    assert resp.json() == []
