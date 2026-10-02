"""Production signup flow: admin invite codes, email verification, and
doctor-created client accounts."""

import uuid

from app.core.database import SessionLocal
from app.models.user import User

PASSWORD = "Str0ng!Pass1"


def _username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _make_admin(client) -> dict:
    """Create + login an admin directly in the DB (no self-signup path)."""
    from datetime import UTC, datetime

    from app.core.security import hash_password

    session = SessionLocal()
    try:
        session.add(
            User(
                username="admin_" + uuid.uuid4().hex[:8],
                password_hash=hash_password(PASSWORD),
                name="Clinic Admin",
                role="admin",
                clinic_code="SENTINEL-TEST",
                onboarding_step=99,
                encryption_salt=uuid.uuid4().hex,
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        session.commit()
        admin = session.query(User).filter(User.role == "admin").order_by(User.created_at.desc()).first()
        username = admin.username
    finally:
        session.close()
    login = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"username": username, "token": login.json()["access_token"]}


def _create_invite(client, admin: dict, clinic="SENTINEL-TEST", max_uses=1) -> dict:
    resp = client.post(
        "/api/admin/invites",
        json={"clinic_code": clinic, "max_uses": max_uses, "expires_in_days": 14},
        headers={"Authorization": f"Bearer {admin['token']}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_admin_can_create_and_list_invite(client):
    admin = _make_admin(client)
    invite = _create_invite(client, admin)
    assert invite["code"].startswith("INV-")
    assert invite["clinic_code"] == "SENTINEL-TEST"

    listing = client.get("/api/admin/invites", headers={"Authorization": f"Bearer {admin['token']}"})
    assert listing.status_code == 200
    codes = [i["code"] for i in listing.json()["data"]["invites"]]
    assert invite["code"] in codes


def test_invite_requires_admin(client, patient_user):
    resp = client.get(
        "/api/admin/invites",
        headers={"Authorization": f"Bearer {patient_user['access_token']}"},
    )
    assert resp.status_code in (401, 403)


def test_doctor_signup_with_invite_code(client):
    admin = _make_admin(client)
    invite = _create_invite(client, admin)
    username = _username("dr")

    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": PASSWORD,
            "name": "Dr Invite",
            "role": "psychologist",
            "dob": "1986-03-21",
            "occupation": "Trauma specialist",
            "invite_code": invite["code"],
            "license_number": "LIC-88231",
        },
    )
    assert resp.status_code == 200, resp.text

    login = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert login.status_code == 200
    me = client.get("/api/patients/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.status_code == 200
    data = me.json()["data"]
    assert data["role"] == "psychologist"
    assert data["clinic"] == "SENTINEL-TEST"
    assert data.get("license_number") == "LIC-88231"

    # Invite usage incremented
    listing = client.get("/api/admin/invites", headers={"Authorization": f"Bearer {admin['token']}"})
    rows = {i["code"]: i for i in listing.json()["data"]["invites"]}
    assert rows[invite["code"]]["use_count"] == 1


def test_doctor_signup_without_invite_rejected(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "username": _username("dr"),
            "password": PASSWORD,
            "name": "Dr No Invite",
            "role": "psychologist",
            "dob": "1986-03-21",
            "occupation": "Trauma",
            "license_number": "LIC-00001",
        },
    )
    assert resp.status_code == 400
    assert "invite" in resp.json()["message"].lower()


def test_invite_requires_license_number(client):
    admin = _make_admin(client)
    invite = _create_invite(client, admin)
    resp = client.post(
        "/api/auth/register",
        json={
            "username": _username("dr"),
            "password": PASSWORD,
            "name": "Dr No License",
            "role": "psychologist",
            "dob": "1986-03-21",
            "occupation": "Trauma",
            "invite_code": invite["code"],
        },
    )
    assert resp.status_code == 400
    assert "license" in resp.json()["message"].lower()


def test_single_use_invite_cannot_be_reused(client):
    admin = _make_admin(client)
    invite = _create_invite(client, admin, max_uses=1)

    first = client.post(
        "/api/auth/register",
        json={
            "username": _username("dr"),
            "password": PASSWORD,
            "name": "Dr First",
            "role": "psychologist",
            "dob": "1986-03-21",
            "occupation": "Trauma",
            "invite_code": invite["code"],
            "license_number": "LIC-A-1111",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/auth/register",
        json={
            "username": _username("dr"),
            "password": PASSWORD,
            "name": "Dr Second",
            "role": "psychologist",
            "dob": "1986-03-21",
            "occupation": "Trauma",
            "invite_code": invite["code"],
            "license_number": "LIC-B-2222",
        },
    )
    assert second.status_code == 400
    assert "uses" in second.json()["message"].lower()


def test_revoked_invite_rejected(client):
    admin = _make_admin(client)
    invite = _create_invite(client, admin)
    resp = client.delete(
        f"/api/admin/invites/{invite['code']}",
        headers={"Authorization": f"Bearer {admin['token']}"},
    )
    assert resp.status_code == 200

    signup = client.post(
        "/api/auth/register",
        json={
            "username": _username("dr"),
            "password": PASSWORD,
            "name": "Dr Revoked",
            "role": "psychologist",
            "dob": "1986-03-21",
            "occupation": "Trauma",
            "invite_code": invite["code"],
            "license_number": "LIC-C-3333",
        },
    )
    assert signup.status_code == 400
    assert "invalid" in signup.json()["message"].lower()


def test_duplicate_license_rejected(client):
    admin = _make_admin(client)
    invite = _create_invite(client, admin, max_uses=3)
    payload = {
        "password": PASSWORD,
        "name": "Dr Dup",
        "role": "psychologist",
        "dob": "1986-03-21",
        "occupation": "Trauma",
        "invite_code": invite["code"],
        "license_number": "LIC-DUP-999",
    }
    payload["username"] = _username("dr")
    assert client.post("/api/auth/register", json=payload).status_code == 200
    payload["username"] = _username("dr")
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 400
    assert "license" in resp.json()["message"].lower()


def test_email_verification_roundtrip(client):
    username = _username("ver")
    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": PASSWORD,
            "name": "Ver User",
            "dob": "2000-01-01",
            "occupation": "Student",
            "email": f"{username}@example.com",
        },
    )
    assert resp.status_code == 200

    # Without SMTP configured the send is skipped; token exists in DB.
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == username).first()
        assert user is not None
        assert user.email == f"{username}@example.com"
        token = user.verification_token
    finally:
        session.close()

    assert token, "verification token should be stored even if email send fails"
    bad = client.get("/api/auth/verify-email?token=nonsense")
    assert bad.status_code == 400

    ok = client.get(f"/api/auth/verify-email?token={token}")
    assert ok.status_code == 200
    assert ok.json()["data"]["verified"] is True

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == username).first()
        assert user.email_verified_at
        assert user.verification_token == ""
    finally:
        session.close()


def test_duplicate_email_rejected(client, patient_user):
    session = SessionLocal()
    try:
        existing = session.query(User).filter(User.username == patient_user["username"]).first()
        existing.email = "taken@example.com"
        session.commit()
    finally:
        session.close()

    resp = client.post(
        "/api/auth/register",
        json={
            "username": _username("mail"),
            "password": PASSWORD,
            "name": "Mail User",
            "dob": "2000-01-01",
            "occupation": "Student",
            "email": "taken@example.com",
        },
    )
    assert resp.status_code == 400
    assert "email" in resp.json()["message"].lower()


def test_doctor_creates_client_account(client, psych_user):
    username = _username("made")
    resp = client.post(
        "/api/patients/create-client",
        json={
            "username": username,
            "password": "Temp!Pass9",
            "name": "Made In Clinic",
            "dob": "2005-06-15",
            "occupation": "Student",
            "contact_info": f"{username}@example.com",
            "country": "Singapore",
        },
        headers={"Authorization": f"Bearer {psych_user['access_token']}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["assigned_psych"] == psych_user["username"]
    assert data["clinic"] == "SENTINEL-TEST"

    # The client can log in right away
    login = client.post("/api/auth/login", json={"username": username, "password": "Temp!Pass9"})
    assert login.status_code == 200
    assert login.json()["role"] == "Patient"


def test_doctor_create_client_requires_psychologist(client, patient_user):
    resp = client.post(
        "/api/patients/create-client",
        json={
            "username": _username("nope"),
            "password": "Temp!Pass9",
            "name": "Nope User",
            "dob": "2005-06-15",
        },
        headers={"Authorization": f"Bearer {patient_user['access_token']}"},
    )
    assert resp.status_code in (401, 403)
