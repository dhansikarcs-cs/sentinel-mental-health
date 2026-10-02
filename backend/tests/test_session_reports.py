"""Session reports: CRUD, scoping, attachments, export.

Rule of the module: only the authoring psychologist (or an admin) can touch
a report, and reports can never be moved between clients.
"""

import io


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_report(client, token: str, patient: str, **over) -> dict:
    body = {
        "patient": patient,
        "session_date": "2026-09-10",
        "session_type": "Review",
        "duration_min": 50,
        "title": "Week 6 review",
        "presenting_concerns": "Exam-related panic persists but frequency is down.",
        "mental_state": "Alert, engaged. Speech pressured when anxious. No perceptual disturbance.",
        "interventions": "CBT thought record; breathing retraining reviewed.",
        "risk_assessment": "Low. No SI, no self-harm ideation expressed.",
        "progress_note": "Panic 2x this week vs 4x last. Skills generalising.",
        "homework": "One thought record daily; continue worry postponement.",
        "plan": "Next: exposure ladder rung 3. Letter for school discussed.",
    }
    body.update(over)
    resp = client.post("/api/session-reports", headers=_headers(token), json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_report_crud_roundtrip(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    report = _make_report(client, psych["access_token"], patient["username"])

    assert report["patient"] == patient["username"]
    assert report["risk_assessment"].startswith("Low")
    assert report["approved_by"] == ""

    # Read
    got = client.get(f"/api/session-reports/{report['id']}", headers=_headers(psych["access_token"])).json()
    assert got["title"] == "Week 6 review"

    # Update a field of a PAST report
    upd = client.put(
        f"/api/session-reports/{report['id']}",
        headers=_headers(psych["access_token"]),
        json={"progress_note": "Panic 1x this week — best yet."},
    )
    assert upd.status_code == 200
    assert upd.json()["data"]["progress_note"].startswith("Panic 1x")

    # Delete
    dele = client.delete(f"/api/session-reports/{report['id']}", headers=_headers(psych["access_token"]))
    assert dele.status_code == 200
    assert (
        client.get(f"/api/session-reports/{report['id']}", headers=_headers(psych["access_token"])).status_code == 404
    )


def test_report_stranger_psych_cannot_read_or_edit(client, make_user):
    author = make_user(role="psychologist")
    stranger = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=author["username"])
    report = _make_report(client, author["access_token"], patient["username"])

    assert (
        client.get(f"/api/session-reports/{report['id']}", headers=_headers(stranger["access_token"])).status_code
        == 403
    )
    assert (
        client.put(
            f"/api/session-reports/{report['id']}",
            headers=_headers(stranger["access_token"]),
            json={"plan": "sabotage"},
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/session-reports/{report['id']}", headers=_headers(stranger["access_token"])).status_code
        == 403
    )


def test_report_patient_role_denied(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    resp = client.get("/api/session-reports", headers=_headers(patient["access_token"]))
    assert resp.status_code == 403


def test_report_cannot_be_moved_between_clients(client, make_user):
    psych = make_user(role="psychologist")
    a = make_user(role="patient", assigned_psych=psych["username"])
    report = _make_report(client, psych["access_token"], a["username"])
    resp = client.put(
        f"/api/session-reports/{report['id']}",
        headers=_headers(psych["access_token"]),
        json={"patient": "someone_else"},
    )
    assert resp.status_code == 400


def test_report_psych_only_assigned_clients(client, make_user):
    psych = make_user(role="psychologist")
    other = make_user(role="patient")  # not assigned
    resp = client.post(
        "/api/session-reports",
        headers=_headers(psych["access_token"]),
        json={"patient": other["username"], "session_date": "2026-09-10"},
    )
    assert resp.status_code == 403


def test_report_list_filters(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    r1 = _make_report(client, psych["access_token"], patient["username"], session_date="2026-08-01", title="Intake")
    r2 = _make_report(client, psych["access_token"], patient["username"], session_date="2026-09-01", title="Review")

    # client filter
    by_patient = client.get(
        "/api/session-reports", headers=_headers(psych["access_token"]), params={"patient": patient["username"]}
    ).json()
    assert len(by_patient) == 2

    # date range
    rng = client.get(
        "/api/session-reports", headers=_headers(psych["access_token"]), params={"date_from": "2026-08-15"}
    ).json()
    assert [r["id"] for r in rng] == [r2["id"]]

    # text search across decrypted fields
    hit = client.get(
        "/api/session-reports", headers=_headers(psych["access_token"]), params={"q": "thought record"}
    ).json()
    assert hit and r1["id"] in [r["id"] for r in hit]

    # approval flow changes the 'approved' filter
    client.put(f"/api/session-reports/{r1['id']}/approve", headers=_headers(psych["access_token"]))
    approved = client.get(
        "/api/session-reports", headers=_headers(psych["access_token"]), params={"approved": "yes"}
    ).json()
    assert [r["id"] for r in approved] == [r1["id"]]


def test_report_upload_and_download_attachment(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    report = _make_report(client, psych["access_token"], patient["username"])

    up = client.post(
        f"/api/session-reports/{report['id']}/upload",
        headers=_headers(psych["access_token"]),
        files={"file": ("worksheet.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert up.status_code == 200
    assert up.json()["data"]["file_name"] == "worksheet.pdf"

    down = client.get(f"/api/session-reports/{report['id']}/attachment", headers=_headers(psych["access_token"]))
    assert down.status_code == 200
    assert b"%PDF-1.4" in down.content

    # stranger cannot download
    stranger = make_user(role="psychologist")
    assert (
        client.get(
            f"/api/session-reports/{report['id']}/attachment", headers=_headers(stranger["access_token"])
        ).status_code
        == 403
    )


def test_report_export_is_formatted_text(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"], name="Maya Kaplan")
    report = _make_report(client, psych["access_token"], patient["username"])

    resp = client.get(f"/api/session-reports/{report['id']}/export", headers=_headers(psych["access_token"]))
    assert resp.status_code == 200
    text = resp.text
    assert "SESSION REPORT" in text
    assert "Maya Kaplan" in text
    assert "RISK ASSESSMENT" in text
    assert "Low. No SI" in text
    assert "Confidential" in text
