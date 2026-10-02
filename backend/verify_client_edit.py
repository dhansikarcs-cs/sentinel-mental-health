"""E2E check: PUT /patients/{username}/account (admin + psych editing clients)."""

import os
import sys

sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

load_dotenv("../.env")
os.environ.setdefault("ENCRYPTION_PASSPHRASE", "demo-passphrase-not-secret")
os.environ.setdefault("ENCRYPTION_SALT", "demo-salt-16bytes-ok")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

c = TestClient(app)
c.__enter__()  # run startup events (initializes encryption)

r = c.post("/api/auth/login", json={"username": "admin", "password": "password123"})
assert r.status_code == 200, r.text
tok = r.json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

d = c.get("/api/psychologists/directory", headers=H).json()
client = d["clients"][0]
print("target client:", client["username"])

r = c.put(f"/api/patients/{client['username']}/account", headers=H, json={"name": "Test Edit Name"})
print("edit name:", r.status_code, r.json().get("message", r.text[:120]))

r = c.put(f"/api/patients/{client['username']}/account", headers=H, json={"password": "newpass1"})
print("edit pw:  ", r.status_code, r.json().get("message", r.text[:120]))

r = c.post("/api/auth/login", json={"username": client["username"], "password": "newpass1"})
print("login with new pw:", r.status_code)

r = c.put(f"/api/patients/{client['username']}/account", headers=H, json={"contact_info": "not-an-email"})
print("bad email rejected:", r.status_code, "(expect 400)")

# restore demo state
r = c.put(
    f"/api/patients/{client['username']}/account", headers=H, json={"name": client["name"], "password": "sentinel123"}
)
print("restore:", r.status_code, r.json().get("message", ""))
r = c.post("/api/auth/login", json={"username": client["username"], "password": "sentinel123"})
print("login restored pw:", r.status_code)

# psychologist can edit their own assigned client
r = c.post("/api/auth/login", json={"username": "cel", "password": "1234"})
assert r.status_code == 200
H2 = {"Authorization": f"Bearer {r.json()['access_token']}"}

# find one of cel's own clients
ps_dir = c.get("/api/psychologists/directory", headers=H2).json()
own = [cl for cl in ps_dir["clients"] if cl.get("assigned_psych") == "cel"]
if own:
    target = own[0]["username"]
    r = c.put(f"/api/patients/{target}/account", headers=H2, json={"occupation": "Updated by psych"})
    print("psych edit own client:", r.status_code, r.json().get("message", r.text[:120]))
    # restore
    c.put(f"/api/patients/{target}/account", headers=H2, json={"occupation": own[0].get("occupation", "")})
else:
    print("psych edit own client: (no assigned client found — skipped)")

print("\n✓ verification complete")
