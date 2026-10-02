"""Doctor feature: follow-up template library.

GET/POST/PUT/DELETE /followup-templates — reusable homework templates,
private to their author — plus POST /{id}/assign which turns a template
into a real follow-up task for an assigned patient in one tap.
"""


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_patient_cannot_access_templates(client, make_user):
    patient = make_user(role="patient")
    resp = client.get("/api/followup-templates", headers=_headers(patient["access_token"]))
    assert resp.status_code == 403


def test_create_and_list_templates(client, make_user):
    psych = make_user(role="psychologist")

    resp = client.post(
        "/api/followup-templates",
        headers=_headers(psych["access_token"]),
        json={
            "title": "Box breathing log",
            "description": "4-4-4-4 twice daily",
            "category": "anxiety",
            "default_due_days": 3,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["title"] == "Box breathing log"

    resp = client.get("/api/followup-templates", headers=_headers(psych["access_token"]))
    assert resp.status_code == 200
    templates = resp.json()
    assert len(templates) == 1
    assert templates[0]["times_used"] == 0


def test_templates_are_private_to_author(client, make_user):
    psych_a = make_user(role="psychologist")
    psych_b = make_user(role="psychologist")

    created = client.post(
        "/api/followup-templates",
        headers=_headers(psych_a["access_token"]),
        json={"title": "Sleep diary", "category": "sleep"},
    )
    assert created.status_code == 201
    tid = created.json()["id"]

    # B sees nothing
    listed = client.get("/api/followup-templates", headers=_headers(psych_b["access_token"]))
    assert listed.json() == []

    # B cannot read/update/delete A's template even by id
    assert (
        client.put(
            f"/api/followup-templates/{tid}", headers=_headers(psych_b["access_token"]), json={"title": "hijack"}
        ).status_code
        == 404
    )
    assert client.delete(f"/api/followup-templates/{tid}", headers=_headers(psych_b["access_token"])).status_code == 404


def test_invalid_category_rejected(client, make_user):
    psych = make_user(role="psychologist")
    resp = client.post(
        "/api/followup-templates",
        headers=_headers(psych["access_token"]),
        json={"title": "x", "category": "not-a-category"},
    )
    assert resp.status_code == 400


def test_update_template(client, make_user):
    psych = make_user(role="psychologist")
    tid = client.post(
        "/api/followup-templates",
        headers=_headers(psych["access_token"]),
        json={"title": "Old title", "default_due_days": 7},
    ).json()["id"]

    resp = client.put(
        f"/api/followup-templates/{tid}",
        headers=_headers(psych["access_token"]),
        json={"title": "New title", "default_due_days": 14},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New title"
    assert resp.json()["default_due_days"] == 14


def test_delete_template(client, make_user):
    psych = make_user(role="psychologist")
    tid = client.post(
        "/api/followup-templates",
        headers=_headers(psych["access_token"]),
        json={"title": "To delete"},
    ).json()["id"]

    assert client.delete(f"/api/followup-templates/{tid}", headers=_headers(psych["access_token"])).status_code == 200
    assert client.get("/api/followup-templates", headers=_headers(psych["access_token"])).json() == []


def test_assign_from_template_creates_task_and_increments_usage(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    tid = client.post(
        "/api/followup-templates",
        headers=_headers(psych["access_token"]),
        json={"title": "Gratitude journal", "description": "3 entries", "default_due_days": 5},
    ).json()["id"]

    resp = client.post(
        f"/api/followup-templates/{tid}/assign",
        headers=_headers(psych["access_token"]),
        json={"patient_username": patient["username"]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["title"] == "Gratitude journal"
    assert data["due_date"] != ""  # computed from default_due_days
    assert data["times_used"] == 1

    # The task exists in the patient's follow-up list
    listed = client.get("/api/followups", headers=_headers(patient["access_token"]))
    tasks = [t for t in listed.json() if t.get("id") == data["task_id"]]
    assert len(tasks) == 1
    assert tasks[0]["status"] == "pending"
    assert tasks[0]["title"] == "Gratitude journal"


def test_assign_requires_assigned_patient(client, make_user):
    psych = make_user(role="psychologist")
    other_patient = make_user(role="patient")  # assigned to nobody

    tid = client.post(
        "/api/followup-templates",
        headers=_headers(psych["access_token"]),
        json={"title": "Task"},
    ).json()["id"]

    resp = client.post(
        f"/api/followup-templates/{tid}/assign",
        headers=_headers(psych["access_token"]),
        json={"patient_username": other_patient["username"]},
    )
    assert resp.status_code == 403

    # Unknown patient
    resp = client.post(
        f"/api/followup-templates/{tid}/assign",
        headers=_headers(psych["access_token"]),
        json={"patient_username": "ghost"},
    )
    assert resp.status_code == 404


def test_assign_respects_explicit_due_date(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    tid = client.post(
        "/api/followup-templates",
        headers=_headers(psych["access_token"]),
        json={"title": "Explicit due", "default_due_days": 30},
    ).json()["id"]

    resp = client.post(
        f"/api/followup-templates/{tid}/assign",
        headers=_headers(psych["access_token"]),
        json={"patient_username": patient["username"], "due_date": "2026-12-01"},
    )
    assert resp.json()["due_date"] == "2026-12-01"
