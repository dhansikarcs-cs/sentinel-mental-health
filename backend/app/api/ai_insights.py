"""AI insights: forecasting, reframing, early-warning, and goal coaching.

Four more endpoints following the house AI contract: try the model with a
versioned prompt, fall back to a deterministic rule-based result when the
model is unreachable. AI unavailability never breaks the feature, and every
response carries `source: ai|rule` so the UI can badge it honestly.

All clinical text here is SUPPORTIVE scaffolding, not diagnosis: forecasts
say "pattern suggests", reframes come with a disclaimer, and risk signals
explicitly tell the clinician to use their own judgment.
"""

import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.structured_errors import ErrorCode, err
from app.models.crisis import CrisisState
from app.models.followup import FollowupTask
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.user import User
from app.services.ai_service import _query_ai

router = APIRouter(prefix="/agents", tags=["agents"])

MOOD_FORECAST_PROMPT_V2 = """Daily mood labels for a patient, oldest first:
{history}

Forecast the NEXT 3 DAYS. Be honest about uncertainty; never promise.
Return ONLY valid JSON: {{"forecast": list of 3 {{"day": int (1-3),
"label": str, "confidence": "low"|"medium"}}, "summary": str (1-2
sentences), "tip": str (one concrete, small action)}}."""

REFRAME_PROMPT_V1 = """A journal entry from a person having a hard day:
"{text}"

Offer ONE CBT-style cognitive reframe: name the likely thought trap, then a
gentle alternative view. Warm, never preachy, no diagnosis. Return ONLY
valid JSON: {{"trap": str (short name), "reframe": str (1-3 sentences),
"affirmation": str (one line they could say to themselves)}}."""

EARLY_WARNING_PROMPT_V1 = """Two-week snapshot for patient "{patient}":
mood labels (oldest first): {moods}
journals written: {journals_14d}
pending follow-ups: {pending_followups} (overdue: {overdue})
crisis episodes: {crisis_14d}
recent crisis: {crisis_note}

List 0-4 early-warning signals a clinician should know before the next
session. Be specific and calibrated; empty list is a valid answer. Return
ONLY valid JSON: {{"signals": list of {{"level": "info"|"watch"|"urgent",
"signal": str, "evidence": str}}, "overall": "steady"|"watch"|"urgent"}}."""

GOAL_SUGGEST_PROMPT_V1 = """Patient's recent mood labels: {moods}
Recent journal excerpt: "{excerpt}"
Existing goals: {existing}

Suggest 3 small, concrete wellness goals (each doable in under 10 minutes,
no medical claims). Return ONLY valid JSON: {{"suggestions": list of 3
{{"title": str (max 6 words), "why": str (1 sentence)}}}}."""

POSITIVE_LABELS = {"good", "great", "okay"}


def _labels_for(db: Session, username: str, days: int) -> list[MoodLog]:
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    return (
        db.query(MoodLog)
        .filter(MoodLog.patient_username == username, MoodLog.timestamp >= cutoff)
        .order_by(MoodLog.timestamp.asc())
        .all()
    )


def _can_view_patient(db: Session, user: User, username: str) -> User:
    patient = db.query(User).filter(User.username == username, User.role == "patient").first()
    if not patient:
        raise err(404, ErrorCode.PATIENT_NOT_FOUND, "Patient not found")
    if user.role == "psychologist" and patient.assigned_psych != user.username:
        raise err(403, ErrorCode.NOT_ASSIGNED, "This client is not assigned to you")
    return patient


# ── 1. Mood forecast (patient, own data) ─────────────────────────


@router.get("/mood-forecast")
def mood_forecast(user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    """A gentle 3-day outlook built from the last 14 days of check-ins.

    Rule fallback: per-day-of-week averages with a regression-to-normal
    pull, so a good streak doesn't produce overconfident sunshine.
    """
    history = _labels_for(db, user.username, days=14)
    if not history:
        return {
            "forecast": [],
            "summary": "Log a few check-ins and your personal outlook will appear here.",
            "tip": "Try a 10-second mood check-in today.",
            "basis": 0,
            "source": "rule",
            "prompt_version": "mood_forecast/v2",
        }

    # Per-day-of-week average mood score (0 bad .. 2 good)
    by_dow: dict[int, list[int]] = {}
    for m in history:
        try:
            d = datetime.fromisoformat(m.date).weekday()
        except ValueError:
            continue
        by_dow.setdefault(d, []).append(
            2 if m.label.lower() in ("good", "great") else 1 if m.label.lower() == "okay" else 0
        )

    recent7 = history[-7:]
    recent_avg = sum(
        2 if m.label.lower() in ("good", "great") else 1 if m.label.lower() == "okay" else 0 for m in recent7
    ) / len(recent7)
    overall_avg = sum(
        2 if m.label.lower() in ("good", "great") else 1 if m.label.lower() == "okay" else 0 for m in history
    ) / len(history)
    # Blend recent mood with the weekday pattern: recency matters, history anchors.
    blend = 0.6 * recent_avg + 0.4 * overall_avg

    forecast = []
    for i in range(1, 4):
        target = (datetime.now(UTC) + timedelta(days=i)).weekday()
        dow_scores = by_dow.get(target, [])
        dow_avg = sum(dow_scores) / len(dow_scores) if dow_scores else blend
        score = 0.7 * blend + 0.3 * dow_avg  # regression toward the recent mean
        label = "good" if score >= 1.35 else "okay" if score >= 0.75 else "rough"
        forecast.append({"day": i, "label": label, "confidence": "low" if len(dow_scores) < 2 else "medium"})

    spread = max(f["label"] for f in forecast) != min(f["label"] for f in forecast)
    if all(f["label"] != "rough" for f in forecast):
        summary = "Your recent pattern points to a steady-to-good few days — keep whatever's been working."
    elif spread:
        summary = "A mixed few days ahead — one day may feel heavier, and that's allowed."
    else:
        summary = "Your pattern suggests a heavier stretch — plan small wins and reach out early."

    tip = "Keep your next check-in — patterns get clearer with every data point."
    low_days = sum(1 for f in forecast if f["label"] == "rough")
    if low_days >= 2:
        tip = "Book the heavier day lightly: one small task, one comfort, early night."

    ai = _query_ai(
        MOOD_FORECAST_PROMPT_V2.format(history=", ".join(f"{m.date}:{m.label}" for m in history)),
        prompt_version="mood_forecast/v2",
    )
    source = "rule"
    try:
        data = json.loads(ai)
        if data.get("forecast"):
            forecast = data["forecast"][:3]
            summary = data.get("summary", summary)
            tip = data.get("tip", tip)
            source = "ai"
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    return {
        "forecast": forecast,
        "summary": summary,
        "tip": tip,
        "basis": len(history),
        "source": source,
        "prompt_version": "mood_forecast/v2",
    }


# ── 2. Cognitive reframe (patient, on a chosen journal entry) ────


@router.get("/journal-reframe/{entry_id}")
def journal_reframe(entry_id: int, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    """A CBT-flavoured reframe of one of the patient's own entries.

    Ownership enforced (entry must belong to the caller). Always pairs the
    reframe with a self-affirmation and a not-therapy disclaimer.
    """
    entry = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.id == entry_id,
            JournalEntry.patient_username == user.username,
            JournalEntry.deleted_at.is_(None),
        )
        .first()
    )
    if not entry:
        raise err(404, ErrorCode.JOURNAL_NOT_FOUND, "Entry not found")

    text = (entry.raw_content or "")[:800]
    lower = text.lower()

    # Rule fallback: detect classic thought traps by keyword.
    if any(k in lower for k in ["always", "never", "everyone", "no one", "nobody"]):
        trap, reframe = (
            "All-or-nothing thinking",
            "Words like 'always' and 'never' are doing a lot of heavy lifting here. Your week actually contains both kinds of moments — this entry is one frame, not the whole film.",
        )
        affirmation = "One hard moment is data, not a verdict."
    elif any(k in lower for k in ["should", "shouldn't", "must", "supposed to"]):
        trap, reframe = (
            "The 'shoulds'",
            "You're measuring yourself against a rulebook nobody handed you. What would you tell a friend in exactly this spot?",
        )
        affirmation = "I can set the bar I jump over."
    elif any(k in lower for k in ["ruin", "disaster", "worst", "awful", "terrible", "catastrophe"]):
        trap, reframe = (
            "Catastrophising",
            "Your mind is fast-forwarding to the worst case. It's allowed to — but the most likely tomorrow is usually far more ordinary, and more workable, than the movie in your head.",
        )
        affirmation = "I can handle the next hour. That's the only hour on the clock."
    else:
        trap, reframe = (
            "A heavy day",
            "There's real weight in this entry, and writing it down already did something: it moved the weight from your head onto paper. That's a skill, and you used it.",
        )
        affirmation = "Naming it is the first move — and I made it."

    ai = _query_ai(REFRAME_PROMPT_V1.format(text=text or "(very short entry)"), prompt_version="journal_reframe/v1")
    source = "rule"
    try:
        data = json.loads(ai)
        if data.get("reframe"):
            trap = data.get("trap", trap)
            reframe = data["reframe"]
            affirmation = data.get("affirmation", affirmation)
            source = "ai"
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    return {
        "entry_id": entry_id,
        "trap": trap,
        "reframe": reframe,
        "affirmation": affirmation,
        "disclaimer": "A thinking exercise, not therapy or medical advice.",
        "source": source,
        "prompt_version": "journal_reframe/v1",
    }


# ── 3. Early-warning signals (clinician) ─────────────────────────


@router.get("/early-warning/{username}")
def early_warning(
    username: str,
    user: User = Depends(require_role("patient", "psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """Pre-session risk scan: 0-4 calibrated signals from 14 days of data.

    Signals are levelled (info/watch/urgent), always carry their evidence,
    and explicitly defer to clinical judgment. Patients may read their OWN
    signals only (self-insight); clinicians follow the usual assignment
    rules (admin sees all; psychologists only their own clients).
    """
    if user.role == "patient":
        if username != user.username:
            raise err(403, ErrorCode.OWNER_ONLY, "You can only view your own signals")
        username = user.username
    _can_view_patient(db, user, username)

    cutoff = (datetime.now(UTC) - timedelta(days=14)).isoformat()
    moods = (
        db.query(MoodLog)
        .filter(MoodLog.patient_username == username, MoodLog.timestamp >= cutoff)
        .order_by(MoodLog.timestamp.asc())
        .all()
    )
    labels = [m.label.lower() for m in moods]
    neg = lambda l: l not in POSITIVE_LABELS  # noqa: E731

    signals: list[dict] = []
    low14 = sum(1 for l in labels if neg(l))
    if len(labels) >= 5 and low14 / len(labels) >= 0.6:
        signals.append(
            {
                "level": "watch",
                "signal": "Sustained low mood",
                "evidence": f"{low14} of {len(labels)} check-ins in the last 14 days were below 'okay'.",
            }
        )

    recent = [neg(l) for l in labels[-5:]]
    older = [neg(l) for l in labels[:-5]]
    older_rate = (sum(older) / len(older)) if older else 0
    if len(recent) == 5 and older and all(recent) and older_rate < 0.6:
        signals.append(
            {
                "level": "urgent",
                "signal": "Mood trending down sharply",
                "evidence": "Last 5 check-ins are all low after a mixed previous week.",
            }
        )

    journals = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.patient_username == username,
            JournalEntry.timestamp >= cutoff,
            JournalEntry.deleted_at.is_(None),
        )
        .count()
    )
    if journals == 0:
        signals.append(
            {
                "level": "watch",
                "signal": "Journaling stopped",
                "evidence": "No entries in 14 days — disengagement often precedes a dip.",
            }
        )
    else:
        heavy_keywords = ["hopeless", "can't", "cant", "worthless", "giving up", "numb", "alone"]
        heavy_hits = []
        for e in (
            db.query(JournalEntry)
            .filter(
                JournalEntry.patient_username == username,
                JournalEntry.timestamp >= cutoff,
                JournalEntry.deleted_at.is_(None),
            )
            .order_by(JournalEntry.timestamp.desc())
            .limit(8)
            .all()
        ):
            body = (e.raw_content or "").lower()
            hit = [k for k in heavy_keywords if k in body]
            if hit:
                heavy_hits.append((e, hit))
        if heavy_hits:
            e, hit = heavy_hits[0]
            signals.append(
                {
                    "level": "urgent",
                    "signal": "Language of concern in a recent entry",
                    "evidence": f"Contains '{hit[0]}' — read the entry before the session.",
                }
            )

    pending = (
        db.query(FollowupTask)
        .filter(FollowupTask.patient_username == username, FollowupTask.status == "pending")
        .count()
    )
    overdue = (
        db.query(FollowupTask)
        .filter(
            FollowupTask.patient_username == username,
            FollowupTask.status == "pending",
            FollowupTask.due_date != "",
            FollowupTask.due_date < datetime.now(UTC).date().isoformat(),
        )
        .count()
    )
    if overdue >= 2:
        signals.append(
            {
                "level": "info",
                "signal": "Follow-up tasks slipping",
                "evidence": f"{overdue} tasks past their due date ({pending} pending overall).",
            }
        )

    crisis_recent = (
        db.query(CrisisState)
        .filter(CrisisState.patient_username == username, CrisisState.triggered_at >= cutoff)
        .count()
    )
    crisis_active = (
        db.query(CrisisState).filter(CrisisState.patient_username == username, CrisisState.active == 1).first()
    )
    if crisis_active:
        signals.insert(
            0,
            {
                "level": "urgent",
                "signal": "Active crisis right now",
                "evidence": f"Triggered {crisis_active.triggered_at} — check the crisis page first.",
            },
        )
    elif crisis_recent:
        signals.append(
            {
                "level": "watch",
                "signal": "Crisis episode in the last 14 days",
                "evidence": f"{crisis_recent} episode(s) — worth a gentle aftermath check-in.",
            }
        )

    if not signals:
        signals.append(
            {
                "level": "info",
                "signal": "No automated flags",
                "evidence": "Nothing in check-ins, journals, tasks or crises tripped a threshold in the last 14 days.",
            }
        )

    overall = (
        "urgent"
        if any(s["level"] == "urgent" for s in signals)
        else "watch"
        if any(s["level"] == "watch" for s in signals)
        else "steady"
    )

    crisis_note = (
        "ACTIVE crisis right now" if crisis_active else (f"{crisis_recent} in last 14d" if crisis_recent else "none")
    )
    ai = _query_ai(
        EARLY_WARNING_PROMPT_V1.format(
            patient=username,
            moods=", ".join(labels[-14:]) or "none",
            journals_14d=journals,
            pending_followups=pending,
            overdue=overdue,
            crisis_14d=crisis_recent,
            crisis_note=crisis_note,
        ),
        prompt_version="early_warning/v1",
    )
    source = "rule"
    try:
        data = json.loads(ai)
        if isinstance(data.get("signals"), list):
            signals = data["signals"][:4] or signals
            overall = data.get("overall", overall)
            source = "ai"
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    return {
        "patient": username,
        "signals": signals,
        "overall": overall,
        "disclaimer": "Automated signals — support, not a diagnosis. Clinical judgment leads.",
        "source": source,
        "prompt_version": "early_warning/v1",
    }


# ── 4. Smart goal suggestions (patient) ──────────────────────────


@router.get("/goal-suggestions")
def goal_suggestions(user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    """Three tiny, personalised wellness goals based on the last 2 weeks."""
    moods = _labels_for(db, user.username, days=14)
    labels = [m.label.lower() for m in moods]
    recent_entry = (
        db.query(JournalEntry)
        .filter(JournalEntry.patient_username == user.username, JournalEntry.deleted_at.is_(None))
        .order_by(JournalEntry.timestamp.desc())
        .first()
    )
    excerpt = (recent_entry.raw_content or "")[:300] if recent_entry else ""

    anxious = any(k in " ".join(labels) for k in ["anxious", "stressed"]) or any(
        k in excerpt.lower() for k in ["anxious", "stress", "overwhelmed", "panic"]
    )
    low = labels and sum(1 for l in labels if l not in POSITIVE_LABELS) / len(labels) >= 0.5
    no_journals = recent_entry is None

    suggestions = [
        {"title": "Step outside for 5 minutes", "why": "Light and movement are the most reliable tiny mood lever."},
        {"title": "Text one person tonight", "why": "Connection beats rumination, and one text is an easy win."},
        {"title": "Write one line before bed", "why": "A one-line journal keeps the habit alive without pressure."},
    ]
    if anxious:
        suggestions[0] = {
            "title": "Try 4-7-8 breathing once",
            "why": "Your recent entries mention stress — one slow breath cycle is a proven reset.",
        }
        suggestions[2] = {
            "title": "Note one worry, then park it",
            "why": "Writing the worry down helps your brain put it down.",
        }
    if low:
        suggestions[1] = {
            "title": "Do one 10-minute tidy",
            "why": "A visible, finished task nudges momentum on flat days.",
        }
    if no_journals:
        suggestions[2] = {
            "title": "Log today's mood",
            "why": "One check-in unlocks your personal patterns and forecast.",
        }

    existing_names = []
    ai = _query_ai(
        GOAL_SUGGEST_PROMPT_V1.format(
            moods=", ".join(labels[-10:]) or "none yet",
            excerpt=excerpt or "(no journal yet)",
            existing=", ".join(existing_names) or "none",
        ),
        prompt_version="goal_suggest/v1",
    )
    source = "rule"
    try:
        data = json.loads(ai)
        if isinstance(data.get("suggestions"), list) and data["suggestions"]:
            cleaned = [s for s in data["suggestions"] if isinstance(s, dict) and s.get("title")][:3]
            if cleaned:
                suggestions = cleaned
                source = "ai"
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    return {
        "suggestions": suggestions,
        "note": "Small is the point — pick one and shrink it until it's almost too easy.",
        "source": source,
        "prompt_version": "goal_suggest/v1",
    }
