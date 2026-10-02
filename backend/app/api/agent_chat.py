"""Agent chat over the Azure AI Foundry hosted agent ("Sentinelagent").

Endpoints:
  POST   /agent/chat         — one chat turn (history from DB, reply persisted)
  GET    /agent/history      — recent turns for the signed-in user
  DELETE /agent/history      — clear the user's chat history
  POST   /agent/weekly-plan  — AI-generated supportive weekly plan (rule fallback)
  GET    /agent/status       — provider availability for UI badges

Privacy: on-prem-first. The Foundry agent is reached with DefaultAzureCredential
(managed identity on App Service); chat content is stored encrypted at rest.
Availability never breaks the feature — deterministic fallbacks everywhere.
"""

import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.agent_message import AgentMessage
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.user import User
from app.services.ai_service import (
    AGENT_SCOPE_RULES,
    _azure_agent_configured,
    _query_ai_with_agent,
)

router = APIRouter(prefix="/agent", tags=["agent"])

HISTORY_WINDOW = 40  # turns kept in the user-visible history
MODEL_CONTEXT_TURNS = 8  # turns sent back to the agent as context


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


class WeeklyPlanRequest(BaseModel):
    focus: str = ""


def _turns_for_context(db: Session, username: str, thread_id: str) -> list[dict]:
    rows = (
        db.query(AgentMessage)
        .filter(AgentMessage.username == username, AgentMessage.thread_id == thread_id)
        .order_by(AgentMessage.id.desc())
        .limit(MODEL_CONTEXT_TURNS)
        .all()
    )
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


def _rule_reply(message: str, mood: str | None, recent_excerpts: list[str]) -> str:
    """Deterministic supportive fallback when no AI provider is reachable."""
    text_lower = message.lower()
    crisis_words = ("kill myself", "end it", "suicide", "self harm", "hurt myself", "want to die")
    if any(w in text_lower for w in crisis_words):
        return (
            "I'm really glad you told me. Your safety matters most right now — please tap the "
            "Emergency button in the app so your care team and trusted contact are alerted "
            "immediately. If you're outside the app, call or text your local crisis line "
            "(for example 988 in the US). You don't have to carry this alone."
        )
    low = mood is not None and mood.lower() in ("bad", "awful", "terrible", "sad", "anxious")
    if low:
        opener = "That sounds like a heavy day. Thank you for putting it into words."
    elif mood:
        opener = f"Good to hear today feels {mood.lower()}. "
    else:
        opener = "Thanks for checking in."
    if recent_excerpts:
        opener += " I've been keeping your recent entries in mind."
    return (
        f"{opener} I'm currently running in offline mode, so I can't reflect deeply right now — "
        "but writing this down already helps. If you want, add a line to your journal about "
        "what would make tomorrow 1% lighter."
    )


def _save_turn(db: Session, username: str, thread_id: str, role: str, content: str, provider: str) -> None:
    db.add(
        AgentMessage(
            username=username,
            thread_id=thread_id,
            role=role,
            content=content,
            provider=provider,
            created_at=datetime.now(UTC).isoformat(),
        )
    )
    db.commit()


@router.post("/chat")
def chat(
    body: ChatRequest,
    user: User = Depends(require_role("patient", "psychologist", "admin")),
    db: Session = Depends(get_db),
):
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="message is required")
    if len(message) > 4000:
        raise HTTPException(status_code=422, detail="message too long (max 4000 chars)")

    thread_id = body.thread_id or "default"
    today = datetime.now(UTC).date()
    mood_row = (
        db.query(MoodLog).filter(MoodLog.patient_username == user.username, MoodLog.date == today.isoformat()).first()
    )
    mood = mood_row.label if mood_row else None
    week_ago = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    excerpts = [
        (j.summary or j.raw_content or "")[:200]
        for j in db.query(JournalEntry)
        .filter(
            JournalEntry.patient_username == user.username,
            JournalEntry.timestamp >= week_ago,
            JournalEntry.deleted_at.is_(None),
        )
        .order_by(JournalEntry.timestamp.desc())
        .limit(2)
        .all()
    ]

    history = _turns_for_context(db, user.username, thread_id)
    context_note = ""
    if mood or excerpts:
        parts = []
        if mood:
            parts.append(f"Today's logged mood: {mood}.")
        if excerpts:
            parts.append("Recent journal themes (do not quote verbatim): " + " | ".join(excerpts))
        context_note = "\n\n[Context — use only if relevant]\n" + " ".join(parts)

    prompt = f"{AGENT_SCOPE_RULES}\n{message}{context_note}"

    _save_turn(db, user.username, thread_id, "user", message, "user")
    reply = ""
    provider = "rule"
    try:
        reply, provider = _query_ai_with_agent(prompt, timeout=30, prompt_version="agent_chat/v1", history=history)
    except Exception:
        reply, provider = "", "rule"
    if not reply:
        reply, provider = _rule_reply(message, mood, excerpts), "rule"

    _save_turn(db, user.username, thread_id, "assistant", reply, provider)

    return {
        "reply": reply,
        "provider": provider,
        "thread_id": thread_id,
        "crisis_resources_shown": any(
            w in message.lower()
            for w in ("kill myself", "end it", "suicide", "self harm", "hurt myself", "want to die")
        ),
    }


@router.get("/history")
def history(
    limit: int = 40,
    thread_id: str = "default",
    user: User = Depends(require_role("patient", "psychologist", "admin")),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, HISTORY_WINDOW))
    rows = (
        db.query(AgentMessage)
        .filter(AgentMessage.username == user.username, AgentMessage.thread_id == thread_id)
        .order_by(AgentMessage.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return {
        "messages": [
            {"id": r.id, "role": r.role, "content": r.content, "provider": r.provider, "created_at": r.created_at}
            for r in rows
        ],
        "thread_id": thread_id,
    }


@router.delete("/history")
def clear_history(
    thread_id: str = "default",
    user: User = Depends(require_role("patient", "psychologist", "admin")),
    db: Session = Depends(get_db),
):
    deleted = (
        db.query(AgentMessage)
        .filter(AgentMessage.username == user.username, AgentMessage.thread_id == thread_id)
        .delete()
    )
    db.commit()
    return {"deleted": deleted, "thread_id": thread_id}


WEEKLY_PLAN_PROMPT_V1 = """You are Sentinel's weekly planning assistant for a mental-health app.
Patient context:
- Recent mood labels: {moods}
- Journals written in the last 7 days: {journal_count}
- Patient's requested focus: {focus}

Create a gentle, realistic week plan. Return ONLY valid JSON:
{{"theme": str (2-5 words), "days": list of 5-7 items, each a short supportive micro-task (<= 90 chars)}}."""


@router.post("/weekly-plan")
def weekly_plan(
    body: WeeklyPlanRequest,
    user: User = Depends(require_role("patient", "psychologist", "admin")),
    db: Session = Depends(get_db),
):
    week_ago = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    moods = (
        db.query(MoodLog)
        .filter(MoodLog.patient_username == user.username, MoodLog.timestamp >= week_ago)
        .order_by(MoodLog.timestamp.desc())
        .limit(7)
        .all()
    )
    mood_labels = [m.label for m in reversed(moods)]
    journal_count = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.patient_username == user.username,
            JournalEntry.timestamp >= week_ago,
            JournalEntry.deleted_at.is_(None),
        )
        .count()
    )

    focus = (body.focus or "").strip()
    if not mood_labels and journal_count == 0:
        theme = "A gentle restart"
        days = [
            "Write one sentence about how today felt",
            "Step outside for five minutes of daylight",
            "Note one thing that went okay today",
            "Log your mood before bed",
            "Pick one small thing to look forward to this weekend",
        ]
        provider = "rule"
    else:
        theme = "Small steady steps"
        base = [
            "Reflect on one moment that stood out this week",
            "Take a 10-minute walk without your phone",
            "Write about something you avoided saying",
            "Name one feeling you noticed today",
            "Plan one enjoyable activity for the weekend",
            "Check in with your mood before bed",
        ]
        if focus:
            base.insert(0, f"Focus: {focus} — pick the smallest first step")
        days, provider = base[:6], "rule"

    ai, ai_provider = _query_ai_with_agent(
        WEEKLY_PLAN_PROMPT_V1.format(
            moods=", ".join(mood_labels) or "none", journal_count=journal_count, focus=focus or "not specified"
        ),
        timeout=30,
        prompt_version="weekly_plan/v1",
    )
    try:
        data = json.loads(ai)
        if data.get("days"):
            theme, days, provider = data["theme"], data["days"][:7], (ai_provider or "ai")
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    return {
        "theme": theme,
        "days": days,
        "context": {"moods_7d": mood_labels, "journals_7d": journal_count},
        "source": provider,
        "prompt_version": "weekly_plan/v1",
    }


@router.get("/status")
def status(user: User = Depends(require_role("patient", "psychologist", "admin"))):
    from app.services.ai_service import _get_agent_openai_client

    client_ready = False
    if _azure_agent_configured() and settings_safe_agent_mode():
        client_ready = _get_agent_openai_client() is not None
    return {
        "agent_configured": _azure_agent_configured(),
        "agent_client_ready": client_ready,
        "agent_name": __import__("app.core.config", fromlist=["settings"]).settings.azure_agent_name,
        "mode": __import__("app.core.config", fromlist=["settings"]).settings.azure_agent_mode,
    }


def settings_safe_agent_mode() -> bool:
    from app.core.config import settings

    return settings.azure_agent_mode.lower() in ("auto", "on")
