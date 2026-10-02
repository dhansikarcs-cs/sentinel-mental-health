"""Tests for the Coping Toolbox feature (personal coping strategies CRUD)."""

import pytest

from conftest import auth_headers


@pytest.fixture()
def patient_a(make_user):
    return make_user(role="patient")


@pytest.fixture()
def patient_b(make_user):
    return make_user(role="patient")


def test_create_and_list_own_tools(client, patient_a):
    h = auth_headers(patient_a["access_token"])

    r = client.post(
        "/api/coping-tools",
        headers=h,
        json={"title": "Box breathing", "description": "4-4-4-4 counts", "category": "calming"},
    )
    assert r.status_code == 201, r.text
    tool = r.json()
    assert tool["title"] == "Box breathing"
    assert tool["patient_username"] == patient_a["username"]

    r = client.get("/api/coping-tools", headers=h)
    assert r.status_code == 200
    tools = r.json()
    assert len(tools) == 1
    assert tools[0]["title"] == "Box breathing"


def test_update_own_tool(client, patient_a):
    h = auth_headers(patient_a["access_token"])
    r = client.post("/api/coping-tools", headers=h, json={"title": "Walk"})
    tool_id = r.json()["id"]

    r = client.put(
        f"/api/coping-tools/{tool_id}",
        headers=h,
        json={"title": "Evening walk", "description": "Around the block", "sort_order": 2},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Evening walk"
    assert body["sort_order"] == 2


def test_delete_own_tool(client, patient_a):
    h = auth_headers(patient_a["access_token"])
    r = client.post("/api/coping-tools", headers=h, json={"title": "Temp"})
    tool_id = r.json()["id"]

    assert client.delete(f"/api/coping-tools/{tool_id}", headers=h).status_code == 200
    tools = client.get("/api/coping-tools", headers=h).json()
    assert all(t["id"] != tool_id for t in tools)


def test_cannot_access_other_patients_tool(client, patient_a, patient_b):
    """Ownership clamp: patient B must not read/update/delete patient A's tool."""
    h_a = auth_headers(patient_a["access_token"])
    h_b = auth_headers(patient_b["access_token"])

    tool_id = client.post("/api/coping-tools", headers=h_a, json={"title": "Private"}).json()["id"]

    assert client.get("/api/coping-tools", headers=h_b).json() == []
    assert client.put(f"/api/coping-tools/{tool_id}", headers=h_b, json={"title": "Hacked"}).status_code == 404
    assert client.delete(f"/api/coping-tools/{tool_id}", headers=h_b).status_code == 404


def test_invalid_category_rejected(client, patient_a):
    h = auth_headers(patient_a["access_token"])
    r = client.post("/api/coping-tools", headers=h, json={"title": "X", "category": "bogus"})
    assert r.status_code == 400


def test_title_length_validated(client, patient_a):
    h = auth_headers(patient_a["access_token"])
    r = client.post("/api/coping-tools", headers=h, json={"title": "x" * 90})
    assert r.status_code == 422


def test_psychologist_reads_own_list_only(client, psych_user):
    """Psychologists have their own (empty) list; they don't see patient tools here."""
    h = auth_headers(psych_user["access_token"])
    assert client.get("/api/coping-tools", headers=h).json() == []
