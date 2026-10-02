"""Device-agnostic physiological ingestion API.

Accepts raw payloads from any vendor (Oura, Samsung, ring, simulated,
generic), normalizes to the common PhysiologicalSignal schema, and — for
backward compatibility — also mirrors into the legacy SensorReading /
RingSensorLog tables so existing risk-engine and dashboard logic keeps
working without modification.

Every row is labeled with its vendor and (for synthetic data) quality, so
simulated physiology is never silently mixed with real readings.
"""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.input_validator import validate_sensor_data
from app.models.physiological_signal import PhysiologicalSignal
from app.models.ring import RingSensorLog
from app.models.sensor_reading import SensorReading
from app.models.user import User
from app.schemas.physiological import NormalizedSignalResponse, PhysiologicalPayload
from app.services.audit import log_audit
from app.services.physio import normalize_payload, to_signal_model

router = APIRouter(prefix="/physio", tags=["physio"])


@router.post("/push", response_model=NormalizedSignalResponse)
def push_physiological(
    payload: PhysiologicalPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = (payload.vendor or "generic").lower()
    device_id = payload.device_id or f"{vendor}_{user.username}"
    now = datetime.now(UTC).isoformat()

    raw = payload.extra_payload()
    raw.setdefault("logged_at", now)
    raw_json = json.dumps(raw) if raw else ""

    reading = normalize_payload(vendor, raw)
    validate_sensor_data(
        bpm=reading.heart_rate,
        stress=reading.stress,
        sleep_hours=reading.sleep_hours,
        spo2=reading.spo2,
        hrv=reading.hrv_rmssd,
    )
    reading.raw_json = raw_json

    # Store into the common schema
    signal = to_signal_model(user.username, device_id, vendor, reading)
    db.add(signal)
    db.flush()

    is_synthetic = vendor in ("simulated", "ring")

    # Mirror into legacy tables for backward compatibility with the risk engine.
    bpm = reading.heart_rate
    hrv = reading.hrv_rmssd
    db.add(
        RingSensorLog(
            device_id=device_id,
            patient_username=user.username,
            bpm=bpm,
            stress=reading.stress,
            sleep_hours=reading.sleep_hours,
            spo2=reading.spo2,
            hrv=int(round(hrv)),
            raw_json=raw_json,
            logged_at=reading.logged_at,
        )
    )
    db.add(
        SensorReading(
            patient_username=user.username,
            device_id=device_id,
            heart_rate=bpm,
            rmssd=float(hrv),
            sdnn=float(hrv) * 0.8,
            temperature=reading.temperature,
            logged_at=reading.logged_at,
        )
    )

    db.commit()
    db.refresh(signal)

    log_audit(
        "physio_pushed",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        resource=vendor,
        details=f"vendor={vendor}, synthetic={is_synthetic}, bpm={bpm}, hrv={hrv}, device={device_id}",
        db=db,
    )

    return NormalizedSignalResponse(
        id=signal.id,
        patient_username=signal.patient_username,
        device_id=signal.device_id,
        vendor=signal.vendor,
        heart_rate=signal.heart_rate,
        hrv_rmssd=signal.hrv_rmssd,
        stress=signal.stress,
        sleep_hours=signal.sleep_hours,
        spo2=signal.spo2,
        temperature=signal.temperature,
        respiratory_rate=signal.respiratory_rate,
        quality=signal.quality,
        confidence=signal.confidence,
        logged_at=signal.logged_at,
    )


@router.get("/signals", response_model=list[NormalizedSignalResponse])
def list_own_signals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(PhysiologicalSignal)
        .filter(PhysiologicalSignal.patient_username == user.username)
        .order_by(PhysiologicalSignal.logged_at.desc())
        .limit(200)
        .all()
    )


@router.get("/patient/{username}", response_model=list[NormalizedSignalResponse])
def list_patient_signals(
    username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    return (
        db.query(PhysiologicalSignal)
        .filter(PhysiologicalSignal.patient_username == username)
        .order_by(PhysiologicalSignal.logged_at.desc())
        .limit(200)
        .all()
    )


@router.get("/stress-spikes")
def list_own_stress_spikes(
    days: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Patient view: stress spikes from their own ring, with day+time of each."""
    return ok(data=_stress_spikes(db, user.username, days))


@router.get("/stress-spikes/{username}")
def list_patient_stress_spikes(
    username: str,
    days: int = 30,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """Clinician view: when this client's stress spiked, and when it tends to."""
    return ok(data=_stress_spikes(db, username, days))


@router.get("/vendors")
def list_vendors(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vendors = (
        db.query(PhysiologicalSignal.vendor)
        .filter(PhysiologicalSignal.patient_username == user.username)
        .distinct()
        .all()
    )
    return {"vendors": [v[0] for v in vendors]}


def _stress_spikes(db: Session, username: str, days: int = 30) -> dict:
    """Find stress spikes with explicit day + time for each.

    A spike = a reading whose stress crosses (max(55, patient median + 18))
    while sitting at least 12 points above the patient's baseline. Each spike
    carries the exact logged day/time so clinicians can see WHEN stress hits,
    plus hour-of-day and weekday histograms for pattern-spotting.

    Reads from BOTH stress sources — the normalized PhysiologicalSignal
    table and the legacy RingSensorLog that devices/seed write into —
    and merges them so no source is silently missed.
    """
    from collections import Counter
    from datetime import datetime, timedelta

    from app.models.ring import RingSensorLog

    days = max(1, min(int(days or 30), 365))
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()

    def _rows(model, ts_col):
        return (
            db.query(model)
            .filter(
                model.patient_username == username,
                ts_col >= since,
            )
            .all()
        )

    # (stress, heart_rate, hrv, logged_at) tuples from every source
    merged: list[tuple] = []
    for r in _rows(PhysiologicalSignal, PhysiologicalSignal.logged_at):
        if r.stress is not None:
            merged.append((int(r.stress), int(r.heart_rate or 0), float(r.hrv_rmssd or 0), r.logged_at))
    for r in _rows(RingSensorLog, RingSensorLog.logged_at):
        if r.stress:
            merged.append((int(r.stress), int(r.bpm or 0), float(r.hrv or 0), r.logged_at))
    merged.sort(key=lambda t: t[3])

    if not merged:
        return {
            "patient": username,
            "window_days": days,
            "reading_count": 0,
            "baseline": None,
            "threshold": None,
            "spikes": [],
            "by_hour": {},
            "by_weekday": {},
            "worst": None,
            "hourly": [],
            "daily": [],
        }

    stresses = [m[0] for m in merged]
    srt = sorted(stresses)
    median = srt[len(srt) // 2] if srt else 0
    threshold = max(55, median + 18)

    def _dt(iso: str) -> datetime:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))

    spikes: list[dict] = []
    for stress, hr, hrv, iso in merged:
        if stress < threshold:
            continue
        t = _dt(iso)
        spikes.append(
            {
                "stress": stress,
                "heart_rate": hr,
                "hrv": round(hrv, 1),
                "logged_at": iso,
                "day": t.strftime("%a %d %b"),
                "iso_day": t.strftime("%Y-%m-%d"),
                "time": t.strftime("%H:%M"),
                "hour": t.hour,
                "weekday": t.strftime("%A"),
                "severity": "severe"
                if stress >= threshold + 25
                else "high"
                if stress >= threshold + 10
                else "moderate",
            }
        )

    # Collapse runs of adjacent readings into single spike episodes: keep the
    # peak of each cluster so a 2-hour sustained rise doesn't read as 8 spikes.
    episodes: list[dict] = []
    for s in spikes:
        if episodes:
            prev = _dt(episodes[-1]["logged_at"])
            cur = _dt(s["logged_at"])
            if (cur - prev) <= timedelta(hours=2):
                if s["stress"] > episodes[-1]["stress"]:
                    episodes[-1] = s
                continue
        episodes.append(s)

    by_hour = Counter(s["hour"] for s in episodes)
    by_weekday = Counter(s["weekday"] for s in episodes)
    worst = max(episodes, key=lambda s: s["stress"]) if episodes else None

    # Hour-of-day profile: average + peak stress per clock hour across the
    # window — feeds the rounded hourly curve on the insights page.
    hour_acc: dict[int, list[int]] = {}
    day_acc: dict[str, list[tuple[int, str]]] = {}
    for stress, _hr, _hrv, iso in merged:
        t = _dt(iso)
        hour_acc.setdefault(t.hour, []).append(stress)
        day_acc.setdefault(t.strftime("%Y-%m-%d"), []).append((stress, iso))

    hourly = []
    for h in range(24):
        vals = hour_acc.get(h) or []
        hourly.append(
            {
                "hour": h,
                "avg": round(sum(vals) / len(vals), 1) if vals else None,
                "max": max(vals) if vals else None,
                "n": len(vals),
            }
        )

    # Day-by-day summary: average, peak (with its time) and spike count.
    daily = []
    for iso_day in sorted(day_acc):
        vals = day_acc[iso_day]
        stresses = [v[0] for v in vals]
        peak_iso = max(vals, key=lambda v: v[0])[1]
        pt = _dt(peak_iso)
        daily.append(
            {
                "iso_day": iso_day,
                "day": pt.strftime("%a %d %b"),
                "avg": round(sum(stresses) / len(stresses), 1),
                "peak": max(stresses),
                "peak_time": pt.strftime("%H:%M"),
                "n": len(stresses),
                "spikes": sum(1 for s in episodes if s["iso_day"] == iso_day),
            }
        )

    return {
        "patient": username,
        "window_days": days,
        "reading_count": len(merged),
        "baseline": median,
        "threshold": threshold,
        "spikes": episodes,
        "by_hour": {str(h): c for h, c in sorted(by_hour.items())},
        "by_weekday": dict(by_weekday.most_common()),
        "worst": worst,
        "hourly": hourly,
        "daily": daily,
    }
