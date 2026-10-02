"""Doctor feature: clinician coping-tool recommendations.

POST /coping-tools/recommend — the psychologist suggests a coping strategy
for an assigned patient; it lands in the patient's toolbox (stamped with
the clinician's name, pinned to the top) and the patient gets a notification.
GET /coping-tools/patient/{username} — read-only clinician view.
"""


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_patient_cannot_recommend(client, make_user):
    patient = make_user(role="patient")
    resp = client.post(
        "/api/coping-tools/recommend",
        headers=_headers(patient["access_token"]),
        json={"patient_username": patient["username"], "title": "Walk it off"},
    )
    assert resp.status_code == 403


def test_recommend_requires_assignment(client, make_user):
    psych = make_user(role="psychologist")
    stranger = make_user(role="patient")  # not assigned
    resp = client.post(
        "/api/coping-tools/recommend",
        headers=_headers(psych["access_token"]),
        json={"patient_username": stranger["username"], "title": "Box breathing"},
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/coping-tools/recommend",
        headers=_headers(psych["access_token"]),
        json={"patient_username": "ghost", "title": "Box breathing"},
    )
    assert resp.status_code == 404


def test_recommend_lands_in_toolbox_with_attribution_and_notification(client, make_user, db_session):
    from app.models.notification import Notification

    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    resp = client.post(
        "/api/coping-tools/recommend",
        headers=_headers(psych["access_token"]),
        json={
            "patient_username": patient["username"],
            "title": "4-7-8 breathing",
            "description": "Before bed",
            "category": "calming",
        },
    )
    assert resp.status_code == 201, resp.text
    tool = resp.json()
    assert tool["recommended_by"] == psych["username"]
    assert tool["title"] == "4-7-8 breathing"

    # Patient sees it in their own toolbox
    mine = client.get("/api/coping-tools", headers=_headers(patient["access_token"]))
    titles = [t["title"] for t in mine.json()]
    assert "4-7-8 breathing" in titles

    # Patient got a notification
    notifs = db_session.query(Notification).filter(Notification.patient_username == patient["username"]).all()
    assert len(notifs) == 1
    assert "toolbox" in notifs[0].message or "toolbox" in notifs[0].title


def test_clinician_can_view_patient_toolbox(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])

    client.post(
        "/api/coping-tools",
        headers=_headers(patient["access_token"]),
        json={"title": "Music", "category": "distraction"},
    )
    resp = client.get(f"/api/coping-tools/patient/{patient['username']}", headers=_headers(psych["access_token"]))
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert "Music" in titles

    # Another psych cannot view
    other = make_user(role="psychologist")
    resp = client.get(f"/api/coping-tools/patient/{patient['username']}", headers=_headers(other["access_token"]))
    assert resp.status_code == 403


def test_patient_cannot_view_clinician_listing_endpoint(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    resp = client.get(f"/api/coping-tools/patient/{patient['username']}", headers=_headers(patient["access_token"]))
    assert resp.status_code == 403


def test_recommend_invalid_category(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    resp = client.post(
        "/api/coping-tools/recommend",
        headers=_headers(psych["access_token"]),
        json={"patient_username": patient["username"], "title": "x", "category": "bogus"},
    )
    assert resp.status_code == 400
