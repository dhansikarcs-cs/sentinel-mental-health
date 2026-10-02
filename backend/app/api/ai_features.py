"""AI features for patients and clinicians.

Three endpoints, all following the house contract: try the AI with a
versioned prompt, fall back to a deterministic rule-based result when no
model is reachable (AI unavailability never breaks the feature).
"""

import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.structured_errors import ErrorCode, err
from app.models.crisis import CrisisState
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.user import User
from app.services.ai_service import _query_ai

router = APIRouter(prefix="/agents", tags=["agents"])

REFLECT_PROMPT_V1 = """Patient journal excerpt: "{excerpt}"
Today's mood: {mood}

Pick ONE gentle, specific journaling prompt for today. It must be open
(not answerable with yes/no), warm, and forward-looking. Return ONLY valid
JSON: {{"prompt": str, "why": str}} where "why" explains the choice in one
short sentence."""

WEEKLY_THEME_PROMPT_V1 = """Journal excerpts from the past week:
{excerpts}

Dominant emotions detected: {emotions}

Identify the week's emotional throughline for this person. Return ONLY
valid JSON: {{"theme": str (3-6 words), "detail": str (2 sentences),
"tone": "positive"|"mixed"|"heavy"}}."""

SESSION_PREP_PROMPT_V1 = """Pre-session prep for patient "{patient}".
Mood trend: {mood_trend} ({recent_moods})
Journals this week: {journals_count}
Pending follow-ups: {pending_followups}
Recent crisis: {crisis_note}
Excerpts: "{excerpts}"

Draft a session agenda: 3-4 bullet points the clinician can adapt. Return
ONLY valid JSON: {{"agenda": list of str, "opening_question": str,
"watch_for": str}}."""


def _positive(label: str) -> bool:
    return label.lower() in ("good", "great", "okay")


@router.get("/reflect-prompt")
def reflect_prompt(user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    """A personalized writing nudge for today's journal entry.

    Context-aware: reacts to today's logged mood and whether the patient
    already wrote today. Deterministic fallback when AI is unreachable.
    """
    today = datetime.now(UTC).date()
    week_ago = (datetime.now(UTC) - timedelta(days=7)).isoformat()

    todays_mood = (
        db.query(MoodLog).filter(MoodLog.patient_username == user.username, MoodLog.date == today.isoformat()).first()
    )
    wrote_today = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.patient_username == user.username,
            JournalEntry.timestamp >= today.isoformat(),
            JournalEntry.deleted_at.is_(None),
        )
        .count()
        > 0
    )
    recent_journals = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.patient_username == user.username,
            JournalEntry.timestamp >= week_ago,
            JournalEntry.deleted_at.is_(None),
        )
        .order_by(JournalEntry.timestamp.desc())
        .limit(3)
        .all()
    )

    mood_label = todays_mood.label if todays_mood else ""
    low_mood = mood_label.lower() in ("bad", "awful", "terrible", "sad", "anxious")

    # Rule-based baseline
    if low_mood:
        prompt = "What made today heavy — and what's one small thing that could make tomorrow lighter?"
        why = "You logged a rough day; this prompt helps you put it down and look forward."
    elif wrote_today:
        prompt = (
            "Reading back on what you wrote today — what's the one sentence you'd want your future self to remember?"
        )
        why = "You already wrote today, so this builds on it instead of starting fresh."
    elif recent_journals:
        prompt = "What's changed since your last entry — even something tiny?"
        why = "Building on your recent entries keeps the thread going."
    else:
        prompt = "What's taking up the most space in your head right now?"
        why = "A gentle opener for a fresh week of journaling."

    source = "rule"
    excerpt = recent_journals[0].raw_content[:400] if recent_journals else ""
    if excerpt or mood_label:
        ai = _query_ai(
            REFLECT_PROMPT_V1.format(excerpt=excerpt or "(no journal yet)", mood=mood_label or "(not logged yet)"),
            prompt_version="reflect_prompt/v1",
        )
        try:
            data = json.loads(ai)
            if data.get("prompt"):
                prompt, why, source = data["prompt"], data.get("why", ""), "ai"
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

    return {
        "prompt": prompt,
        "why": why,
        "wrote_today": wrote_today,
        "mood": mood_label,
        "source": source,
        "prompt_version": "reflect_prompt/v1",
    }


def _excerpts(db: Session, username: str, days: int, limit: int) -> list[JournalEntry]:
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    return (
        db.query(JournalEntry)
        .filter(
            JournalEntry.patient_username == username,
            JournalEntry.timestamp >= cutoff,
            JournalEntry.deleted_at.is_(None),
        )
        .order_by(JournalEntry.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.get("/weekly-theme/{username}")
def weekly_theme(
    username: str,
    user: User = Depends(require_role("patient", "psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """What the past week's journals were emotionally about.

    Patients can only ever read their own theme — the username parameter is
    ignored for them (ownership clamp, same as crisis resolve).
    """
    if user.role == "patient":
        if username != user.username:
            raise err(403, ErrorCode.OWNER_ONLY, "You can only view your own weekly theme")
        username = user.username
    else:
        patient = db.query(User).filter(User.username == username, User.role == "patient").first()
        if not patient:
            raise err(404, ErrorCode.PATIENT_NOT_FOUND, "Patient not found")
        if user.role == "psychologist" and patient.assigned_psych != user.username:
            raise err(403, ErrorCode.NOT_ASSIGNED, "This client is not assigned to you")

    entries = _excerpts(db, username, days=7, limit=12)
    if not entries:
        return {
            "theme": "",
            "detail": "No journal entries this week yet.",
            "tone": "neutral",
            "entries": 0,
            "source": "rule",
        }

    excerpts = " | ".join((e.summary or e.raw_content or "")[:150] for e in entries[:5])
    emotions = " ".join((e.emotions or "") for e in entries[:5])

    theme = "A week of small moments"
    detail = f"{len(entries)} entries this week. The common thread is still forming — more writing will reveal it."
    tone = "mixed"

    text = " ".join((e.raw_content or "").lower() for e in entries)
    if any(k in text for k in ["happy", "good day", "grateful", "proud", "excited"]):
        tone = "positive"
        theme = "Looking for the good"
        detail = "Positive notes ran through this week's entries despite everyday ups and downs."
    if any(k in text for k in ["anxious", "panic", "stress", "overwhelmed", "hopeless", "awful"]):
        tone = "heavy" if tone != "positive" else "mixed"
        theme = "Carrying a lot"
        detail = "Several entries touched on anxiety or pressure — worth a gentle check-in."

    ai = _query_ai(
        WEEKLY_THEME_PROMPT_V1.format(excerpts=excerpts, emotions=emotions[:200] or "(none detected)"),
        prompt_version="weekly_theme/v1",
    )
    try:
        data = json.loads(ai)
        if data.get("theme"):
            theme, detail, tone = data["theme"], data.get("detail", detail), data.get("tone", tone)
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    return {
        "theme": theme,
        "detail": detail,
        "tone": tone,
        "entries": len(entries),
        "source": "ai" if theme != "A week of small moments" or detail != detail else "rule",
        "prompt_version": "weekly_theme/v1",
    }


@router.get("/next-session-prep/{username}")
def next_session_prep(
    username: str,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """AI-drafted agenda for the client's next session.

    Composes mood trend, engagement, pending follow-ups and crisis recency
    into a suggested agenda, opening question, and one thing to watch for.
    """
    patient = db.query(User).filter(User.username == username, User.role == "patient").first()
    if not patient:
        raise err(404, ErrorCode.PATIENT_NOT_FOUND, "Patient not found")
    if user.role == "psychologist" and patient.assigned_psych != user.username:
        raise err(403, ErrorCode.NOT_ASSIGNED, "This client is not assigned to you")

    journals = _excerpts(db, username, days=7, limit=10)
    journals_count = len(journals)

    moods = (
        db.query(MoodLog)
        .filter(
            MoodLog.patient_username == username,
            MoodLog.timestamp >= (datetime.now(UTC) - timedelta(days=14)).isoformat(),
        )
        .order_by(MoodLog.timestamp.desc())
        .limit(14)
        .all()
    )
    recent_pos = sum(1 for m in moods[:7] if _positive(m.label))
    older_pos = sum(1 for m in moods[7:14] if _positive(m.label))
    mood_trend = (
        "unknown"
        if not moods
        else ("improving" if recent_pos > older_pos else "declining" if recent_pos < older_pos else "stable")
    )
    recent_moods = ", ".join(m.label for m in moods[:5]) or "none logged"

    from app.models.followup import FollowupTask

    pending_followups = (
        db.query(FollowupTask)
        .filter(FollowupTask.patient_username == username, FollowupTask.status == "pending")
        .count()
    )

    crisis_row = db.query(CrisisState).filter(CrisisState.patient_username == username, CrisisState.active == 1).first()
    crisis_note = "ACTIVE crisis right now" if crisis_row else "none this window"

    excerpts = " | ".join((j.summary or j.raw_content or "")[:120] for j in journals[:3]) or "(no journals this week)"

    # Rule-based agenda baseline
    agenda = []
    if crisis_note.startswith("ACTIVE"):
        agenda.append("Check safety and aftermath of the current crisis first")
    if mood_trend == "declining":
        agenda.append("Explore the mood dip — what changed in the last two weeks")
    elif mood_trend == "improving":
        agenda.append("Reinforce what's been working lately")
    else:
        agenda.append("Open check-in on mood and week overall")
    if pending_followups:
        agenda.append(f"Review {pending_followups} pending follow-up task(s)")
    if journals_count == 0:
        agenda.append("Re-engage: set one small journaling commitment")
    else:
        agenda.append("Reflect on this week's entries together")
    if len(agenda) < 3:
        agenda.append("Set one small goal for the coming week")

    opening = "How has the week really been?"
    watch_for = "Engagement signals" if journals_count == 0 else "Anything avoided in the journals"

    ai = _query_ai(
        SESSION_PREP_PROMPT_V1.format(
            patient=username,
            mood_trend=mood_trend,
            recent_moods=recent_moods,
            journals_count=journals_count,
            pending_followups=pending_followups,
            crisis_note=crisis_note,
            excerpts=excerpts,
        ),
        prompt_version="session_prep/v1",
    )
    source = "rule"
    try:
        data = json.loads(ai)
        if data.get("agenda"):
            agenda, source = data["agenda"][:4], "ai"
            opening = data.get("opening_question", opening)
            watch_for = data.get("watch_for", watch_for)
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    return {
        "patient": username,
        "agenda": agenda,
        "opening_question": opening,
        "watch_for": watch_for,
        "context": {
            "journals_7d": journals_count,
            "mood_trend": mood_trend,
            "pending_followups": pending_followups,
            "crisis": bool(crisis_row),
        },
        "source": source,
        "prompt_version": "session_prep/v1",
    }
