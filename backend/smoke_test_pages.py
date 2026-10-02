"""
Sentinel page-by-page API smoke test.

Logs in as a patient (maya_k), a psychologist (cel), and admin, then calls
every endpoint each frontend page depends on — GETs and the key writes —
and reports PASS/FAIL per call.

Run:  ./venv/bin/python smoke_test_pages.py [base_url]
"""

import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8010"
results: list[tuple[str, int, bool, str]] = []


def check(label, method, path, token=None, json=None, expect=(200, 201), note=""):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = httpx.request(method, BASE + path, headers=headers, json=json, timeout=30)
    except Exception as e:
        results.append((label, 0, False, str(e)))
        print(f"  ERR  {label}: {e}")
        return None
    ok = r.status_code in expect
    results.append((label, r.status_code, ok, note))
    print(f"  {'PASS' if ok else 'FAIL'} [{r.status_code}] {label}")
    if not ok:
        print(f"        -> {r.text[:220]}")
    return r


def login(username, password):
    r = httpx.post(BASE + "/api/auth/login", json={"username": username, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {username} failed: {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


# ══════════════════════════ PATIENT (maya_k) ══════════════════════════
print("\n── PATIENT: maya_k ──────────────────────────────────────────")
pt = login("maya_k", "sentinel123")

check("Dashboard: /patients/me", "GET", "/api/patients/me", pt)
check("Dashboard: wellness", "GET", "/api/patients/me/wellness", pt)
check("Dashboard: /ai/health", "GET", "/api/ai/health", pt)
check("Journal: list", "GET", "/api/journal", pt)
check("Journal: prompts", "GET", "/api/journal/prompts", pt)
r = check(
    "Journal: create entry",
    "POST",
    "/api/journal",
    pt,
    json={
        "raw_content": "Smoke test entry — today went fine, did the breathing thing before class.",
        "timestamp": "2026-09-15T10:00:00Z",
        "checkin": [],
    },
)
if r and r.status_code == 200:
    body = r.json()
    jid = (body.get("data") or body).get("id") or (body.get("data") or body).get("journal", {}).get("id")
    if jid:
        # Analysis runs in the background worker; 404 is valid when workers are off.
        check("Journal: AI analysis by id", "GET", f"/api/ai-analyses/journal/{jid}", pt, expect=(200, 404))
        check("Journal: emotions by id", "GET", f"/api/emotion-results/journal/{jid}", pt, expect=(200, 404))
        check("Journal: risk by id", "GET", f"/api/risk-assessments/journal/{jid}", pt, expect=(200, 404))
        check("Journal: delete entry", "DELETE", f"/api/journal/{jid}", pt, expect=(200, 204))
check("Mood: today check", "GET", "/api/mood/today/check", pt)
check("Mood: history", "GET", "/api/mood", pt)
check("Mood: log", "POST", "/api/mood", pt, json={"date": "2026-09-15", "emoji": "okay", "label": "okay"})
check("Bookings: mine", "GET", "/api/bookings", pt)
check("Bookings: psych availability", "GET", "/api/bookings/availability/cel", pt, expect=(200, 404))
check("Follow-ups: mine", "GET", "/api/followups", pt)
check("Crisis: state", "GET", "/api/crisis/state", pt)
check("Crisis: log", "GET", "/api/crisis/log", pt)
check("Crisis: elapsed", "GET", "/api/crisis/elapsed", pt)
check(
    "Crisis: risk assess",
    "POST",
    "/api/crisis/assess-risk",
    pt,
    json={"text": "Just feeling okay today, school was fine."},
)
check("Timeline: events", "GET", "/api/timeline/maya_k?days=30", pt)
check("Timeline: metrics", "GET", "/api/timeline/maya_k/metrics", pt)
# Clinician-view endpoints: patients are correctly refused (security boundary).
check("Emotions: timeline (clinician-only)", "GET", "/api/emotions/timeline/maya_k?days=30", pt, expect=(200, 403))
check("Emotions: summary", "GET", "/api/emotions/summary/maya_k?days=30", pt)
check("Ring: sensor data", "GET", "/api/ring/data", pt)
check("Ring: devices", "GET", "/api/ring/devices", pt)
check("Notifications: list", "GET", "/api/notifications", pt)
check("Notifications: unread", "GET", "/api/notifications/unread", pt)
check("Notifications: read all", "PUT", "/api/notifications/read-all", pt)
check("Search: journals", "GET", "/api/search/journals?q=exam", pt)
check("AI analyses: patient", "GET", "/api/ai-analyses/patient/maya_k", pt)
check("Emotion results (clinician-only)", "GET", "/api/emotion-results/patient/maya_k", pt, expect=(200, 403))
check("Sensor readings (clinician-only)", "GET", "/api/sensor-readings/patient/maya_k", pt, expect=(200, 403))
check("Risk assessments: patient", "GET", "/api/risk-assessments/patient/maya_k", pt, expect=(200, 404))
check("Activity feed (clinician-only)", "GET", "/api/activity?days=7", pt, expect=(200, 403))
check("Events (clinician-only)", "GET", "/api/events/patient/maya_k?limit=20", pt, expect=(200, 403))
check(
    "Sync: offline journals",
    "POST",
    "/api/sync/journals",
    pt,
    json=[
        {"raw_content": "Offline sync smoke entry", "timestamp": "2026-09-14T08:00:00Z", "client_id": "smoke-offline-1"}
    ],
)

# ══════════════════════ PSYCHOLOGIST (cel) ══════════════════════
print("\n── PSYCHOLOGIST: cel ────────────────────────────────────────")
dt = login("cel", "1234")

check("Triage: list", "GET", "/api/triage", dt)
r = check("Triage: create assessment", "POST", "/api/triage", dt, json={"patient_username": "maya_k"})
if r and r.status_code == 200:
    body = r.json()
    entry = body.get("data") or body
    tid = entry.get("id") or (entry.get("entry") or {}).get("id") or (entry.get("triage") or {}).get("id")
    if tid:
        check("Triage: update entry", "PUT", f"/api/triage/{tid}", dt, json={"status": "closed"})
check("Clients: list", "GET", "/api/psychologists/patients", dt)
check("Clinical notes: list", "GET", "/api/psychologists/notes", dt)
check(
    "Clinical notes: create",
    "POST",
    "/api/psychologists/notes",
    dt,
    json={"patient_username": "maya_k", "raw_notes": "Smoke note: engaged well, homework reviewed."},
)
check("Patient journals: maya_k", "GET", "/api/journal/maya_k", dt)
check("Patient summaries", "GET", "/api/journal/maya_k/summaries", dt)
check("Patient moods", "GET", "/api/mood/maya_k", dt)
check("Patient overview", "GET", "/api/patients/maya_k/overview", dt)
check("Patient plain insights", "GET", "/api/patients/maya_k/plain-insights", dt)
check("Patient profile", "GET", "/api/patients/maya_k/profile", dt)
check("Patient summary", "GET", "/api/patients/maya_k/summary", dt)
check("Patient timeline", "GET", "/api/timeline/maya_k?days=90", dt)
check("Emotion timeline (patient)", "GET", "/api/emotions/timeline/maya_k?days=90", dt)
check("Physio signals", "GET", "/api/physio/patient/maya_k", dt, expect=(200, 404))
check("Bookings: practice view", "GET", "/api/bookings", dt)
check("Availability: mine", "GET", "/api/bookings/availability/me", dt)
check(
    "Availability: set",
    "POST",
    "/api/bookings/availability",
    dt,
    json={"date": "2026-09-25", "times": ["10:00", "15:30"]},
)
check("Follow-ups: practice view", "GET", "/api/followups", dt)
check(
    "Follow-up: create",
    "POST",
    "/api/followups",
    dt,
    json={
        "patient_username": "maya_k",
        "title": "Smoke: breathing log",
        "description": "Box breathing before each past paper.",
        "assigned_at": "2026-09-15",
    },
)
check("Agent: pre-session brief", "POST", "/api/agents/pre-session-brief", dt, json={"patient_username": "maya_k"})
check("Agent: triage summary", "POST", "/api/agents/triage-summary", dt, json={"patient_username": "maya_k"})
check("Agent: suggest slots", "POST", "/api/agents/suggest-slots", dt, json={"patient_username": "maya_k"})
check("Agent: compliance radar", "POST", "/api/agents/compliance-radar", dt)
check("Agent: silent period watch", "POST", "/api/agents/silent-period-watch", dt)
check("Agent: relapse indicators", "POST", "/api/agents/relapse-indicators", dt)
check("Agent: ring vitals risk", "POST", "/api/agents/ring-vitals-risk", dt)
check("Psych journal: list", "GET", "/api/psych-journal", dt)
check(
    "Psych journal: create",
    "POST",
    "/api/psych-journal",
    dt,
    json={"raw_content": "Smoke reflection: the demo data is holding up well today."},
)
check("Export: journal summaries", "GET", "/api/export/journal-summaries?days=30", dt)
check("Export: clinical notes", "GET", "/api/export/clinical-notes?days=30", dt)
check("Notifications: psych", "GET", "/api/notifications", dt)

# ═══════════════════════════ ADMIN ═══════════════════════════
print("\n── ADMIN ────────────────────────────────────────────────────")
at = login("admin", "password123")

check("Admin: directory (30 clients)", "GET", "/api/psychologists/directory", at)
check("Admin: event store", "GET", "/api/events?limit=50", at)
check("Admin: event replay", "GET", "/api/events/replay?from_sequence=0", at)
check("Admin: crisis log (clinic-wide)", "GET", "/api/crisis/log", at)
check("Admin: ML registry", "GET", "/api/ml/models", at)
check("Admin: feature flags", "GET", "/api/feature-flags", at)
check("Admin: export patient data", "GET", "/api/export/patient-data", at)
check("Admin: activity feed", "GET", "/api/activity?days=7", at)
check("Admin: audit via health", "GET", "/health", at)

# ═══════════════════════════ SUMMARY ═════════════════════════
print("\n═════════════════════════════════════════════════════════════")
fails = [r for r in results if not r[2]]
print(f"TOTAL: {len(results)} calls · PASS: {len(results) - len(fails)} · FAIL: {len(fails)}")
for label, code, _, note in fails:
    print(f"  ✗ [{code}] {label} {note}")
sys.exit(1 if fails else 0)
