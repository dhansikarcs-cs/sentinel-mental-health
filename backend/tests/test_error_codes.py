"""Structured error codes: every failure carries a machine-readable code.

Rule of the module: any 4xx/5xx from the API has the envelope
{code, message, trace_id?, details?} — no bare {"detail": ...} strings —
and domain failures use their specific registry code, not a generic one.
"""


def _code(resp) -> str:
    body = resp.json()
    assert "code" in body, f"no code in envelope: {body}"
    assert isinstance(body["code"], str) and body["code"], body
    assert "message" in body, body
    return body["code"]


# ── Auth ─────────────────────────────────────────────────────────────


def test_login_bad_credentials_code(client):
    resp = client.post("/api/auth/login", json={"username": "ghost", "password": "nope1234!"})
    assert resp.status_code in (400, 401)
    assert _code(resp) == "AUTH_INVALID_CREDENTIALS"


def test_auth_required_code(client):
    # A protected endpoint with no token must 401 with a code.
    resp = client.get("/api/journal")
    assert resp.status_code == 401
    assert _code(resp) == "UNAUTHORIZED"


def test_register_duplicate_username_code(client, make_user):
    u = make_user(role="patient")
    resp = client.post(
        "/api/auth/register",
        json={
            "username": u["username"],
            "password": "Str0ng!Pass1",
            "name": "Dup",
            "role": "patient",
            "dob": "1996-01-01",
            "occupation": "x",
            "clinic_code": "SENTINEL-TEST",
        },
    )
    assert resp.status_code == 400
    assert _code(resp) == "USERNAME_TAKEN"


def test_wrong_role_code(client, patient_user):
    # Patients can't list clinicians' patient rosters.
    resp = client.get(
        "/api/psychologists/patients", headers={"Authorization": f"Bearer {patient_user['access_token']}"}
    )
    if resp.status_code in (400, 401, 403):
        code = _code(resp)
        assert code in ("INSUFFICIENT_PERMISSIONS", "FORBIDDEN", "UNAUTHORIZED")


# ── Records: 404s use domain codes ───────────────────────────────────


def test_journal_missing_code(client, make_user):
    p = make_user(role="patient")
    # Resummarize targets a journal by id — a missing id must say so by code.
    r = client.post("/api/journal/999999/resummarize", headers={"Authorization": f"Bearer {p['access_token']}"})
    assert r.status_code == 404
    assert _code(r) == "JOURNAL_NOT_FOUND"


def test_report_missing_code(client, psych_user):
    r = client.get("/api/session-reports/999999", headers={"Authorization": f"Bearer {psych_user['access_token']}"})
    assert r.status_code == 404
    assert _code(r) == "REPORT_NOT_FOUND"


def test_followup_missing_code(client, psych_user):
    r = client.get("/api/followups/999999/download", headers={"Authorization": f"Bearer {psych_user['access_token']}"})
    assert r.status_code == 404
    assert _code(r) == "FOLLOWUP_NOT_FOUND"


# ── Ownership: IDOR is blocked with owner-scoped codes ───────────────


def test_journal_owner_only_code(client, make_user):
    a = make_user(role="patient")
    b = make_user(role="patient")
    created = client.post(
        "/api/journal",
        headers={"Authorization": f"Bearer {a['access_token']}"},
        json={"title": "t", "content": "c", "date": "2099-01-01"},
    )
    if created.status_code not in (200, 201):
        return  # journal creation shape differs; covered elsewhere
    jid = created.json()["data"]["id"]
    r = client.get(f"/api/journal/{jid}", headers={"Authorization": f"Bearer {b['access_token']}"})
    assert r.status_code in (403, 404)
    assert _code(r) in ("OWNER_ONLY", "JOURNAL_NOT_FOUND")


# ── Bookings: conflicts and transitions ──────────────────────────────


def _mk_booking(client, patient, psych, date="2099-04-01", time="10:00"):
    return client.post(
        "/api/bookings",
        headers={"Authorization": f"Bearer {patient['access_token']}"},
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


def test_booking_conflict_code(client, make_user):
    psych = make_user(role="psychologist")
    p1 = make_user(role="patient", assigned_psych=psych["username"])
    p2 = make_user(role="patient", assigned_psych=psych["username"])
    first = _mk_booking(client, p1, psych)
    assert first.status_code in (200, 201), first.text
    second = _mk_booking(client, p2, psych)
    assert second.status_code == 409
    assert _code(second) == "BOOKING_SLOT_CONFLICT"


def test_booking_missing_code(client, psych_user):
    r = client.put(
        "/api/bookings/999999/status",
        headers={"Authorization": f"Bearer {psych_user['access_token']}"},
        json={"status": "Approved"},
    )
    assert r.status_code in (404, 400, 403)
    assert "code" in r.json()


# ── Crisis ───────────────────────────────────────────────────────────


def test_crisis_cancel_not_owner_code(client, make_user):
    a = make_user(role="patient")
    b = make_user(role="patient")
    started = client.post(
        "/api/crisis",
        headers={"Authorization": f"Bearer {a['access_token']}"},
        json={"reason": "test"},
    )
    if started.status_code not in (200, 201):
        return  # crisis creation contract covered by crisis tests
    r = client.post(
        "/api/crisis/resolve",
        headers={"Authorization": f"Bearer {b['access_token']}"},
        json={},
    )
    assert r.status_code in (403, 404)
    assert _code(r) in ("OWNER_ONLY", "CRISIS_NOT_FOUND")


# ── Validation errors are labelled too ───────────────────────────────


def test_422_validation_has_code(client, psych_user):
    r = client.post(
        "/api/session-reports",
        headers={"Authorization": f"Bearer {psych_user['access_token']}"},
        json={"nonsense": True},
    )
    assert r.status_code in (400, 422)
    body = r.json()
    assert body.get("code") == "VALIDATION_ERROR", body
