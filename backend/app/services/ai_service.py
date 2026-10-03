import json
import logging
import re
import time
import urllib.request
from threading import Lock

from app.core.config import settings
from app.ml.emotion_classifier import EmotionClassifier
from app.ml.risk_engine import assess_risk_with_explainability

logger = logging.getLogger("sentinel.ai")

_ollama_lock = Lock()
_ollama_last_call = 0.0
_ollama_consecutive_failures = 0
_ollama_breaker_until = 0.0

OLLAMA_BREAKER_THRESHOLD = 2
OLLAMA_BREAKER_COOLDOWN = 30.0

_emotion_clf_lock = Lock()
_emotion_clf: EmotionClassifier | None = None


def _get_emotion_clf() -> EmotionClassifier:
    """Lazily build the sklearn classifier on first use so cold starts (and
    /health) stay fast — the model + libs are only loaded when actually needed."""
    global _emotion_clf
    if _emotion_clf is None:
        with _emotion_clf_lock:
            if _emotion_clf is None:
                _emotion_clf = EmotionClassifier()
    return _emotion_clf


CLINICAL_JOURNAL_SUMMARY_PROMPT_V1 = (
    "You are Sentinel, a clinical documentation AI. Read this journal entry "
    "and write a brief clinical summary (2-4 sentences)."
    "{emotion_hint}"
    " Use clinical tone, third person, past tense. Do not quote verbatim."
    ' Return valid JSON: {{"summary": "..."}}.'
    "\n\nJournal Entry:\n{text}"
)
FRIENDLY_JOURNAL_SUMMARY_PROMPT_V1 = (
    "You are Sentinel, a caring companion, not a therapist. "
    "Read this journal entry and reply like a warm, supportive friend "
    "sending a text message (2-4 short sentences)."
    "{emotion_hint}"
    " Be genuine and grounded, never dramatic. "
    "Acknowledge the feeling honestly and gently — name what they shared, "
    "show you read it, and reflect it back with compassion. "
    "Do NOT exaggerate: no 'so exciting!!', no 'amazing!!', no over-the-top praise, "
    "no big promises, no 'everything will be fine', no false hope. "
    "Match your energy to theirs: if they are happy, share quiet warmth — not hype. "
    "If they are hurting, be soft and steady: 'I hear you. That sounds really heavy. "
    "You didn't have to carry this alone — thank you for writing it down.' "
    "Never moralise, never lecture, never minimize their feelings. "
    "{crisis_guidance}"
    "Do not sound clinical or like a psychologist in the rest of the reply. "
    "No coping techniques, no self-help instructions — just warm, honest presence. "
    ' Return valid JSON: {{"summary": "..."}}.'
    "\n\nJournal Entry:\n{text}"
)
CRISIS_SAFETY_SENTENCE = (
    "If you are in danger right now, please reach out to emergency services "
    "or a crisis line immediately (U.S./Canada: call or text 988)."
)
CRISIS_SAFETY_GUIDANCE = (
    "Because this entry contains explicit self-harm or suicidal language, "
    "your very last sentence MUST be exactly (with no changes): "
    f'"{CRISIS_SAFETY_SENTENCE}" '
    "Keep the sentences before that supportive and non-clinical. "
)
NO_CRISIS_GUIDANCE = "Do not mention crisis lines, hotlines, or emergency services — this entry does not warrant it. "
NOTE_SYNTHESIS_PROMPT_V1 = (
    "You are Sentinel. Convert these session notes into a structured clinical note "
    "with Observations, Assessment, and Plan sections. Use precise emotion language "
    "in the Assessment. Keep it professional but not cold.\n\n"
    "Session Notes:\n{raw_notes}\n\nStructured Clinical Note:"
)


_azure_lock = Lock()


def _azure_configured() -> bool:
    return bool(settings.azure_ai_key) and bool(settings.azure_ai_endpoint)


def _azure_url_and_headers() -> tuple[str, dict, dict] | None:
    """Build (url, headers, body-overrides) for the configured Azure resource.

    Supports both endpoint styles:
      • Azure AI Foundry  https://<res>.services.ai.azure.com  → OpenAI-compatible
        route /models/chat/completions (model = MODEL name, e.g. gpt-5.4-mini)
      • Azure OpenAI      https://<res>.openai.azure.com       → classic
        route /openai/deployments/<deployment>/chat/completions (+ api-version)
    """
    if not _azure_configured():
        return None
    ep = settings.azure_ai_endpoint.strip().rstrip("/")
    if not ep.startswith(("http://", "https://")):
        ep = f"https://{ep}"
    headers = {"Content-Type": "application/json", "api-key": settings.azure_ai_key}
    if ".services.ai.azure.com" in ep:
        url = f"{ep}/models/chat/completions"
        body = {"model": settings.azure_deployment}
    else:
        # classic Azure OpenAI resource
        url = f"{ep}/openai/deployments/{settings.azure_deployment}/chat/completions?api-version={settings.azure_api_version}"
        body = {}
    return url, headers, body


def _query_azure(prompt: str, timeout: int = 20, prompt_version: str = "") -> str:
    """Azure AI Foundry / Azure OpenAI chat completions. Returns '' on any failure."""
    cfg = _azure_url_and_headers()
    if not cfg:
        return ""
    url, headers, body_extra = cfg
    start = time.perf_counter()
    try:
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            **body_extra,
        }
        # GPT-5-class models (Foundry route) reject `max_tokens` in favour of
        # `max_completion_tokens`; classic Azure OpenAI deployments use `max_tokens`.
        if ".services.ai.azure.com" in url:
            payload["max_completion_tokens"] = settings.azure_max_tokens
        else:
            payload["max_tokens"] = settings.azure_max_tokens
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read().decode())
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "ai_request provider=azure ok=true latency_ms=%s prompt_version=%s prompt_len=%s",
            latency_ms,
            prompt_version,
            len(prompt),
            extra={"extra_fields": {"provider": "azure", "ok": True, "latency_ms": latency_ms}},
        )
        return (result.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "ai_request provider=azure ok=false latency_ms=%s prompt_version=%s error=%s",
            latency_ms,
            prompt_version,
            e,
            extra={"extra_fields": {"provider": "azure", "ok": False, "latency_ms": latency_ms, "error": str(e)}},
        )
        return ""


def _query_ollama(prompt: str, timeout: int = 20, prompt_version: str = "") -> str | None:
    global _ollama_last_call
    global _ollama_consecutive_failures
    global _ollama_breaker_until
    now = time.time()
    if now < _ollama_breaker_until:
        logger.info(
            "ai_request provider=ollama ok=false skipped reason=circuit_open prompt_version=%s",
            prompt_version,
            extra={"extra_fields": {"provider": "ollama", "ok": False, "skipped": "circuit_open"}},
        )
        return None
    with _ollama_lock:
        now = time.time()
        if now - _ollama_last_call < 0.5:
            time.sleep(0.5 - (now - _ollama_last_call))
        _ollama_last_call = time.time()
    start = time.perf_counter()
    try:
        data = json.dumps({"model": settings.ollama_model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            f"{settings.ollama_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read().decode())
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        _ollama_consecutive_failures = 0
        logger.info(
            "ai_request provider=ollama ok=true latency_ms=%s prompt_version=%s prompt_len=%s",
            latency_ms,
            prompt_version,
            len(prompt),
            extra={"extra_fields": {"provider": "ollama", "ok": True, "latency_ms": latency_ms}},
        )
        return result.get("response", "")
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        _ollama_consecutive_failures += 1
        if _ollama_consecutive_failures >= OLLAMA_BREAKER_THRESHOLD:
            _ollama_breaker_until = time.time() + OLLAMA_BREAKER_COOLDOWN
            _ollama_consecutive_failures = 0
        logger.info(
            "ai_request provider=ollama ok=false latency_ms=%s prompt_version=%s error=%s",
            latency_ms,
            prompt_version,
            e,
            extra={"extra_fields": {"provider": "ollama", "ok": False, "latency_ms": latency_ms, "error": str(e)}},
        )
        return None


def _query_groq(prompt: str, timeout: int = 20, prompt_version: str = "") -> str:
    if not settings.allow_cloud_ai:
        logger.info(
            "ai_request provider=groq ok=false skipped reason=cloud_ai_disabled prompt_version=%s",
            prompt_version,
            extra={"extra_fields": {"provider": "groq", "ok": False, "skipped": "cloud_ai_disabled"}},
        )
        return ""
    key = settings.groq_api_key or ""
    if not key or key == "gsk_your_key_here":
        return ""
    start = time.perf_counter()
    try:
        data = json.dumps(
            {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 512,
            }
        ).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read().decode())
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "ai_request provider=groq ok=true latency_ms=%s prompt_version=%s prompt_len=%s",
            latency_ms,
            prompt_version,
            len(prompt),
            extra={"extra_fields": {"provider": "groq", "ok": True, "latency_ms": latency_ms}},
        )
        return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "ai_request provider=groq ok=false latency_ms=%s prompt_version=%s error=%s",
            latency_ms,
            prompt_version,
            e,
            extra={"extra_fields": {"provider": "groq", "ok": False, "latency_ms": latency_ms, "error": str(e)}},
        )
        return ""


def _query_ai(prompt: str, timeout: int = 20, prompt_version: str = "") -> str:
    result = _query_ollama(prompt, timeout=timeout, prompt_version=prompt_version)
    if result:
        return result
    result = _query_azure(prompt, timeout=timeout, prompt_version=prompt_version)
    if result:
        return result
    result = _query_groq(prompt, timeout=timeout, prompt_version=prompt_version)
    if result:
        return result
    return ""


# ── Azure AI Foundry hosted agent (Responses API + agent_reference) ─────────

_agent_client_cache: dict = {}

AGENT_SCOPE_RULES = """You are Sentinel's AI agent embedded in a clinical mental-health platform.
Rules you must always follow:
- You are a supportive companion, NOT a therapist and NOT an emergency service.
- Never provide medical diagnoses, medication advice, or replace professional care.
- If a user expresses intent to harm themselves or others, respond with empathy and
  immediately direct them to the in-app Emergency button and local crisis services.
- Keep replies warm, brief (under 180 words unless asked for depth), and concrete.
- Never ask the user to resend sensitive identifiers (full name, address, ID numbers).
"""


def _azure_agent_configured() -> bool:
    return bool(settings.azure_agent_endpoint) and bool(settings.azure_agent_name)


def _get_agent_openai_client():
    """Build (and cache) the Foundry project's OpenAI-compatible client."""
    if not _azure_agent_configured():
        return None
    cached = _agent_client_cache.get("client")
    if cached is not None:
        return cached
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential

        # The Foundry project SDK requires Entra-token credentials: managed
        # identity on App Service, `az login` locally. API keys are NOT
        # accepted for agent_reference calls.
        credential = DefaultAzureCredential()
        project_client = AIProjectClient(
            endpoint=settings.azure_agent_endpoint.strip().rstrip("/"),
            credential=credential,
        )
        client = project_client.get_openai_client()
        _agent_client_cache["client"] = client
        return client
    except Exception as e:  # import errors, bad endpoint, auth failures
        logger.warning("azure_agent client init failed: %s", e)
        return None


def _query_azure_agent(
    prompt: str,
    timeout: int = 30,
    prompt_version: str = "",
    history: list[dict] | None = None,
) -> str:
    """Call the hosted Foundry agent via the Responses API. Returns '' on failure."""
    if not _azure_agent_configured():
        return ""
    mode = settings.azure_agent_mode.lower()
    if mode == "off":
        return ""
    client = _get_agent_openai_client()
    if client is None:
        return ""
    start = time.perf_counter()
    try:
        agent_ref = {"name": settings.azure_agent_name, "type": "agent_reference"}
        if settings.azure_agent_version:
            agent_ref["version"] = settings.azure_agent_version
        input_items: list[dict] = []
        for item in (history or [])[-8:]:
            role = item.get("role", "user")
            if role in ("user", "assistant") and item.get("content"):
                input_items.append({"role": role, "content": str(item["content"])[:4000]})
        input_items.append({"role": "user", "content": prompt})
        response = client.responses.create(
            input=input_items,
            extra_body={"agent_reference": agent_ref},
            timeout=timeout,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        text = (getattr(response, "output_text", "") or "").strip()
        logger.info(
            "ai_request provider=azure_agent ok=true latency_ms=%s prompt_version=%s prompt_len=%s",
            latency_ms,
            prompt_version,
            len(prompt),
            extra={"extra_fields": {"provider": "azure_agent", "ok": True, "latency_ms": latency_ms}},
        )
        return text
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "ai_request provider=azure_agent ok=false latency_ms=%s prompt_version=%s error=%s",
            latency_ms,
            prompt_version,
            e,
            extra={"extra_fields": {"provider": "azure_agent", "ok": False, "latency_ms": latency_ms, "error": str(e)}},
        )
        # One failed attempt shouldn't leave a broken client cached (e.g. expired creds).
        _agent_client_cache.pop("client", None)
        return ""


def _query_ai_with_agent(
    prompt: str, timeout: int = 30, prompt_version: str = "", history: list[dict] | None = None
) -> tuple[str, str]:
    """Chain: local Ollama → Foundry agent (mode auto) → keyed Azure → Groq.

    Returns ``(text, provider_name)`` so callers can badge the answer
    honestly. provider is one of: azure_agent | ollama | azure | groq | rule.
    ``history`` (list of {role, content}) is only used by the agent provider,
    which supports multi-turn input via the Responses API.
    """
    mode = settings.azure_agent_mode.lower()
    if mode == "on":
        result = _query_azure_agent(prompt, timeout=timeout, prompt_version=prompt_version, history=history)
        if result:
            return result, "azure_agent"
        text = _query_ai(prompt, timeout=timeout, prompt_version=prompt_version)
        return (text, "") if not text else (text, "cloud")
    if mode == "off":
        text = _query_ai(prompt, timeout=timeout, prompt_version=prompt_version)
        return (text, "") if not text else (text, "cloud")
    # auto: keep local-first privacy default, agent as strong cloud fallback
    result = _query_ollama(prompt, timeout=timeout, prompt_version=prompt_version)
    if result:
        return result, "ollama"
    result = _query_azure_agent(prompt, timeout=timeout, prompt_version=prompt_version, history=history)
    if result:
        return result, "azure_agent"
    text = _query_ai(prompt, timeout=timeout, prompt_version=prompt_version)
    return (text, "") if not text else (text, "cloud")


def _is_raw_echo(output: str, original: str) -> bool:
    cleaned = output.strip().lower()
    orig_clean = original.strip().lower()
    if not cleaned or not orig_clean:
        return False
    if cleaned == orig_clean:
        return True
    if cleaned in orig_clean:
        return True
    if orig_clean in cleaned:
        return True
    out_words = set(re.findall(r"\w+", cleaned))
    orig_words = set(re.findall(r"\w+", orig_clean))
    if not orig_words:
        return False
    overlap = len(out_words & orig_words) / len(orig_words)
    return overlap > 0.85


def _explicit_crisis_language(text: str) -> bool:
    """True only for clear self-harm or suicidal language (same list as the risk engine)."""
    from app.ml.risk_engine import CRISIS_KW

    lower = text.lower()
    return any(kw in lower for kw in CRISIS_KW)


def classify_emotions(text: str) -> str:
    top = _get_emotion_clf().predict_top(text, threshold=0.15)
    labels = [e for e, p in top if e != "neutral"]
    if not labels:
        return ""
    return ", ".join(labels[:5])


def classify_emotions_with_probs(text: str) -> tuple[list[tuple[str, float]], dict[str, float]]:
    clf = _get_emotion_clf()
    probs = clf.predict_proba(text)
    top = clf.predict_top(text, threshold=0.15)
    return top, probs


def assess_crisis_risk(text: str) -> dict:
    return assess_risk_with_explainability(text)


def summarize_journal(text: str, mode: str = "patient") -> dict:
    if not text.strip():
        return {
            "summary": text[:200],
            "ai_source": "rule",
            "emotions": "",
            "emotion_probabilities": "{}",
            "source": "rule",
            "prompt_version": "rule",
        }

    top_emotions, emotion_probs = classify_emotions_with_probs(text)
    emotions_str = ", ".join(e for e, p in top_emotions if e != "neutral") or "neutral"
    emotion_probs_json = json.dumps(emotion_probs)

    crisis = _explicit_crisis_language(text)

    emotion_hint = f"\nEmotions detected: {emotions_str}." if emotions_str else ""

    # The classifier (GoEmotions) can mislabel crisis text (e.g. "relief" for a
    # suicidal entry). Keep its output out of the clinical note: a clinician must
    # read what the patient actually wrote, not a possibly-wrong emotion guess.
    if mode == "clinical":
        prompt = CLINICAL_JOURNAL_SUMMARY_PROMPT_V1.format(emotion_hint="", text=text)
        prompt_version = "clinical_journal_summary/v1"
    else:
        crisis_guidance = CRISIS_SAFETY_GUIDANCE if crisis else NO_CRISIS_GUIDANCE
        prompt = FRIENDLY_JOURNAL_SUMMARY_PROMPT_V1.format(
            emotion_hint=emotion_hint, crisis_guidance=crisis_guidance, text=text
        )
        prompt_version = "friendly_journal_summary/v2"

    raw = _query_ollama(prompt, timeout=15, prompt_version=prompt_version)
    source = "ollama"
    if not raw or _is_raw_echo(raw, text):
        raw = _query_azure(prompt, prompt_version=prompt_version)
        source = "azure"
    if not raw or _is_raw_echo(raw, text):
        raw = _query_groq(prompt, prompt_version=prompt_version)
        source = "groq"
    if raw and not _is_raw_echo(raw, text):
        match = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                summary = result.get("summary", text[:200])
                if mode == "patient" and crisis and "988" not in summary:
                    summary = f"{summary.rstrip()} {CRISIS_SAFETY_SENTENCE}"
                return {
                    "summary": summary,
                    "ai_source": source,
                    "emotions": emotions_str,
                    "emotion_probabilities": emotion_probs_json,
                    "source": "ai",
                    "prompt_version": prompt_version,
                }
            except Exception:
                pass

    return _fallback_summary(text, emotions_str, emotion_probs_json, mode)


def _fallback_summary(text: str, emotions: str = "", emotion_probs_json: str = "{}", mode: str = "patient") -> dict:
    if not text.strip():
        return {
            "summary": "No content to summarize.",
            "ai_source": "rule",
            "emotions": "",
            "emotion_probabilities": "{}",
            "source": "rule",
            "prompt_version": "rule",
        }
    if mode == "clinical":
        prompt_version = "clinical_journal_summary/v1"
        summary = (
            f"Observations: Patient reports emotional experiences "
            f"consistent with {emotions if emotions else 'mixed affect'}.\n\n"
            f"Assessment: Emotional awareness present. Continue monitoring.\n\n"
            f"Plan: Follow-up within standard interval."
        )
    else:
        prompt_version = "friendly_journal_summary/v1"
        if emotions:
            summary = f"You're feeling {emotions}. That's completely valid — thanks for sharing how you feel."
        else:
            summary = "Thanks for writing this entry. Your feelings matter and tracking them is a positive step."
        if _explicit_crisis_language(text):
            summary = f"{summary} {CRISIS_SAFETY_SENTENCE}"

    return {
        "summary": summary,
        "ai_source": "rule",
        "emotions": emotions,
        "emotion_probabilities": emotion_probs_json,
        "source": "rule",
        "prompt_version": prompt_version,
    }


def synthesize_clinical_notes(raw_notes: str) -> str:
    if not raw_notes.strip():
        return "No notes to synthesize."

    prompt = NOTE_SYNTHESIS_PROMPT_V1.format(raw_notes=raw_notes)
    prompt_version = "note_synthesis/v1"

    result = _query_ai(prompt, prompt_version=prompt_version)
    if result:
        return result

    return (
        f"**Observations**: {raw_notes[:200]}{'...' if len(raw_notes) > 200 else ''}\n\n"
        f"**Assessment**: Patient appears engaged in therapeutic process. "
        f"Continue monitoring emotional trajectory.\n\n"
        f"**Plan**: Follow-up session recommended within standard interval."
    )
