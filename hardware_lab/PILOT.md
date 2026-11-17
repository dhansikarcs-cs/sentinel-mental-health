# Hardware-less pilot — runbook

The pilot runs on **real recorded ring data**, not simulations. The physical
ring is not needed at demo time; the values came from an actual Viaking R30 PRO
session and are pushed through Sentinel's own API.

## What the UI shows

`Dashboard` → "💍 Wearable Vitals" card:

| Field | Value | Origin |
| --- | --- | --- |
| Heart rate | 83 bpm | live `0601` frame |
| SpO₂ | 96 % | `0602` frame |
| HRV | 37 ms | combined record `@11` |
| Temperature | 35.86 °C | debug console body-temp mean |
| Stress / Sleep | `—` | never measured; shown as dash, never invented |

Every card carries the device id and recording timestamp. A dash explicitly
means "not measured".

## Run it (from repo root `sentinel3`)

Terminal 1 — backend (uses `backend/data/sentinel.db`):

```powershell
cd backend
$env:ENCRYPTION_REQUIRED="false"; $env:RUN_WORKERS="false"
$env:DATABASE_URL="sqlite:///./data/sentinel.db"
$env:JWT_SECRET="dev-local-demo-8f3a2c9e7b1d4e6f"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend:

```powershell
cd frontend
.\node_modules\.bin\vite.cmd --host 127.0.0.1 --port 5173
```

Open http://127.0.0.1:5173 → log in **alaya / 4321** → Dashboard.

Terminal 3 — seed the recorded readings (only needed once, or after a DB reset):

```powershell
cd hardware_lab
python seed_recorded.py
```

## Verification performed

- `/health` → 200 healthy
- proxy login → 200
- `/api/patients/me/wellness` → real ring object
- `vite build` → passes
- `ruff check backend/` → passes; `ruff format --check` → 178 files
- `pytest backend/tests` → 222 passed

## Files changed for this pilot

- `backend/app/api/patients.py` — `/me/wellness` now returns sourced vitals
  (device id, timestamp, temperature, nulls for unmeasured fields).
- `frontend/src/pages/Dashboard.tsx` — new Wearable Vitals card.
- `backend/app/services/ai_service.py` — fixed `_V1` → `_V2` constant typo
  (was a pre-existing lint failure / runtime crash).
- `hardware_lab/seed_recorded.py` — pushes recorded data through the API.

Earlier simulation-removal work (deleted `SimulatedRing`, removed defaults and
derived values) is unchanged. The 10 seeded demo vitals rows in the demo DB
remain but are older, so `/me/wellness` shows the newer real recordings.

## Scope note

All of this is local to the `sentinel3` repo. The live Render deployment uses a
separate repo (`sentinel-mental-health`) and is unaffected until ported.
