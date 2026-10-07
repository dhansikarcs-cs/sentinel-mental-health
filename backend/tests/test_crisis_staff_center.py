"""Staff emergency-center fixes.

1. The `/crisis` route was patient-only, so the psychologist's crisis banner
   (an active crisis + a "View" button) bounced them to /triage — clinicians
   had no way to acknowledge or resolve a crisis from the UI.
2. `/crisis/state` for staff returned the *first* active row (nondeterministic),
   so a stale zombie trigger could shadow a patient's fresh crisis.
3. Admins could resolve (via API) but could not acknowledge, and saw their own
   (empty) state rather than the active crisis.
"""

from conftest import auth_headers


def test_admin_acknowledges_active_crisis(client, make_user):
    """Admin operates the emergency center: see the active crisis and acknowledge it."""
    patient = make_user(role="patient")
    h_p = auth_headers(patient["access_token"])
    admin = make_user(role="admin")
    h_a = auth_headers(admin["access_token"])

    client.post("/api/crisis/trigger", headers=h_p)

    state = client.get("/api/crisis/state", headers=h_a).json()
    assert state["active"] is True, "admin must see the active crisis (was their own empty row)"
    assert state["patient"] == patient["username"]

    r = client.post("/api/crisis/acknowledge", headers=h_a)
    assert r.status_code == 200, f"admin acknowledge failed: {r.status_code} {r.text[:200]}"

    state = client.get("/api/crisis/state", headers=h_a).json()
    assert state["acknowledged"] is True
    assert state["acknowledged_by"] == admin["username"]


def test_admin_acknowledge_allowed(client, make_user):
    """Boundary: the acknowledge endpoint must not reject admin (403) anymore."""
    patient = make_user(role="patient")
    h_p = auth_headers(patient["access_token"])
    admin = make_user(role="admin")
    h_a = auth_headers(admin["access_token"])

    client.post("/api/crisis/trigger", headers=h_p)
    r = client.post("/api/crisis/acknowledge", headers=h_a)
    assert r.status_code != 403, f"admin must be permitted to acknowledge: {r.status_code} {r.text[:200]}"


def test_staff_state_returns_most_recent_active_crisis(client, make_user):
    """With multiple concurrent crises, staff see the freshest one — not an
    arbitrary first row that could be a stale zombie trigger."""
    a = make_user(username="alice_x")
    b = make_user(username="bob_x")
    psych = make_user(role="psychologist")
    h_a = auth_headers(a["access_token"])
    h_b = auth_headers(b["access_token"])
    h_d = auth_headers(psych["access_token"])

    client.post("/api/crisis/trigger", headers=h_a)
    client.post("/api/crisis/trigger", headers=h_b)

    state = client.get("/api/crisis/state", headers=h_d).json()
    assert state["active"] is True
    assert state["patient"] == "bob_x", f"staff state must show the most recent active crisis, got {state['patient']!r}"

    elapsed = client.get("/api/crisis/elapsed", headers=h_d).json()
    assert elapsed["patient"] == "bob_x", "elapsed must agree with the same state row"

    # Cleanup: resolve both so later tests start clean.
    client.post("/api/crisis/resolve", headers=h_d)
    client.post("/api/crisis/resolve", headers=h_b)


def test_admin_sees_most_recent_active_crisis(client, make_user):
    """Admin emergency center follows the same deterministic rule as psych."""
    a = make_user(username="ann_x")
    b = make_user(username="ben_x")
    admin = make_user(role="admin")
    h_a = auth_headers(a["access_token"])
    h_b = auth_headers(b["access_token"])
    h_x = auth_headers(admin["access_token"])

    client.post("/api/crisis/trigger", headers=h_a)
    client.post("/api/crisis/trigger", headers=h_b)

    state = client.get("/api/crisis/state", headers=h_x).json()
    assert state["patient"] == "ben_x"

    client.post("/api/crisis/resolve", headers=h_x)
    client.post("/api/crisis/resolve", headers=h_b)
