"""Filters: followups (status/patient/overdue/due_before) and bookings
(status/date_from/date_to/upcoming/past), plus the /followups/stats rollup.

Filters are applied in the API layer over role-scoped base queries, so a
patient can never widen their scope with the patient filter.
"""


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mk_tasks(client, psych_token, patient, titles, due="") -> list[str]:
    ids = []
    for t in titles:
        r = client.post(
            "/api/followups",
            headers=_headers(psych_token),
            json={"patient_username": patient["username"], "title": t, "due_date": due},
        )
        assert r.status_code in (200, 201), r.text
        ids.append(r.json()["id"])
    return ids


def test_followup_status_filter(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    ids = _mk_tasks(client, psych["access_token"], patient, ["A", "B", "C"])
    client.put(f"/api/followups/{ids[0]}", headers=_headers(patient["access_token"]), json={"status": "completed"})

    resp = client.get("/api/followups?status=pending", headers=_headers(psych["access_token"]))
    titles = {t["title"] for t in resp.json()}
    assert titles == {"B", "C"}

    resp = client.get("/api/followups?status=completed", headers=_headers(psych["access_token"]))
    titles = {t["title"] for t in resp.json()}
    assert titles == {"A"}


def test_followup_patient_filter_psych_only(client, make_user):
    psych = make_user(role="psychologist")
    p1 = make_user(role="patient", assigned_psych=psych["username"])
    p2 = make_user(role="patient", assigned_psych=psych["username"])
    _mk_tasks(client, psych["access_token"], p1, ["for-one"])
    _mk_tasks(client, psych["access_token"], p2, ["for-two"])

    resp = client.get(f"/api/followups?patient={p1['username']}", headers=_headers(psych["access_token"]))
    assert {t["title"] for t in resp.json()} == {"for-one"}

    # A patient cannot use the filter to see someone else's tasks
    resp = client.get(f"/api/followups?patient={p2['username']}", headers=_headers(p1["access_token"]))
    assert {t["title"] for t in resp.json()} == {"for-one"}


def test_followup_overdue_and_due_before(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    _mk_tasks(client, psych["access_token"], patient, ["past-task"], due="2026-01-01")
    _mk_tasks(client, psych["access_token"], patient, ["future-task"], due="2099-01-01")

    resp = client.get("/api/followups?overdue=true", headers=_headers(psych["access_token"]))
    assert {t["title"] for t in resp.json()} == {"past-task"}

    resp = client.get("/api/followups?due_before=2026-06-01", headers=_headers(psych["access_token"]))
    assert {t["title"] for t in resp.json()} == {"past-task"}


def test_followup_stats(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    ids = _mk_tasks(client, psych["access_token"], patient, ["X", "Y"], due="2026-01-01")
    client.put(f"/api/followups/{ids[0]}", headers=_headers(patient["access_token"]), json={"status": "completed"})

    resp = client.get("/api/followups/stats", headers=_headers(psych["access_token"]))
    body = resp.json()
    assert body["total"] == 2
    assert body["pending"] == 1
    assert body["completed"] == 1
    assert body["overdue"] == 1


def test_booking_status_and_date_filters(client, make_user):
    from datetime import UTC, datetime, timedelta

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    today = datetime.now(UTC).date()

    for i, (d, status) in enumerate(
        [
            ((today + timedelta(days=3)).isoformat(), None),  # stays Pending
            ((today + timedelta(days=5)).isoformat(), "Approved"),
            ((today - timedelta(days=10)).isoformat(), "Approved"),
        ]
    ):
        r = client.post(
            "/api/bookings",
            headers=_headers(patient["access_token"]),
            json={
                "psychologist_username": psych["username"],
                "date": d,
                "time": "10:00",
                "session_type": "video",
                "members": "",
                "contact": "p@example.com",
                "explanation": "check-in",
            },
        )
        assert r.status_code in (200, 201), r.text
        if status:
            client.put(
                f"/api/bookings/{r.json()['id']}/status",
                headers=_headers(psych["access_token"]),
                json={"status": status},
            )

    hdrs = _headers(psych["access_token"])
    assert len(client.get("/api/bookings?status=pending", headers=hdrs).json()) == 1
    assert len(client.get("/api/bookings?status=approved", headers=hdrs).json()) == 2
    upcoming = client.get("/api/bookings?upcoming=true", headers=hdrs).json()
    assert len(upcoming) == 2
    assert all(b["date"] >= today.isoformat() for b in upcoming)
    assert len(client.get("/api/bookings?past=true", headers=hdrs).json()) == 1
    ranged = client.get(
        f"/api/bookings?date_from={(today + timedelta(days=2)).isoformat()}&date_to={(today + timedelta(days=4)).isoformat()}",
        headers=hdrs,
    ).json()
    assert len(ranged) == 1
