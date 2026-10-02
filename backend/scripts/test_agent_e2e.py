"""End-to-end smoke test for the agent chat feature.

Spawns uvicorn on port 8001, exercises /api/agent/* endpoints, prints results.
Run from backend/:  ~/.venvs/sentinel/bin/python scripts/test_agent_e2e.py
"""

import json
import subprocess
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8001"
VENV_PY = sys.executable  # same interpreter that runs this script


def req(path, method="GET", body=None, token=None, timeout=40):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def main():
    log = open("/tmp/sentinel-e2e.log", "w")  # noqa: SIM115 — must stay open for the server's lifetime
    server = subprocess.Popen(
        [VENV_PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=".",
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        # wait for boot
        for _ in range(30):
            time.sleep(1)
            try:
                health = req("/health", timeout=5)
                break
            except Exception:
                continue
        else:
            print("FAIL: server never became healthy — see /tmp/sentinel-e2e.log")
            sys.exit(1)
        print(f"health: {health['status']} | azure_agent: {health['checks']['ai_providers'].get('azure_agent')}")

        token = req("/api/auth/login", "POST", {"username": "admin", "password": "password123"}, timeout=15)[
            "access_token"
        ]
        print("login: OK")

        status = req("/api/agent/status", token=token, timeout=15)
        print(
            f"agent/status: configured={status['agent_configured']} client_ready={status['agent_client_ready']} name={status['agent_name']!r} mode={status['mode']}"
        )

        chat = req(
            "/api/agent/chat", "POST", {"message": "Hi, I had a rough day at school and just want to vent."}, token, 45
        )
        print(f"agent/chat: provider={chat['provider']} reply={chat['reply'][:160]!r}")

        plan = req("/api/agent/weekly-plan", "POST", {"focus": "sleep"}, token, 45)
        print(f"agent/weekly-plan: theme={plan['theme']!r} source={plan['source']} days={len(plan['days'])}")

        hist = req("/api/agent/history", token=token, timeout=15)
        print(f"agent/history: {len(hist['messages'])} turns stored (encrypted at rest)")

        cleared = req("/api/agent/history", "DELETE", token=token, timeout=15)
        print(f"agent/history DELETE: removed {cleared['deleted']} turns")

        print("ALL AGENT E2E CHECKS PASSED")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()


if __name__ == "__main__":
    main()
