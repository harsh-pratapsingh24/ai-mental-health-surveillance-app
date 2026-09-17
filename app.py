"""
AegisMind — AI-Powered Mental Health Monitoring & Distress Prediction System
Principal Engineer: Full-Stack + Clinical AI Systems
Architecture: Multi-Agent Pipeline (AGENTS.md specification) + Consoling AI Companion

Agents:
  guard_agent       — Safety & ingestion guard (consent + crisis regex)
  nlp_agent         — Linguistic profiling (pronoun density, absolutist scan)
  trajectory_agent  — DPI slope & trajectory velocity over 7-day window
  crisis_agent      — SEV-1 crisis intercept & UI lock
  hitl_agent        — Counselor HITL queue & Jitsi room management
"""

import os
import re
import uuid
import math
import random
import string
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import wraps
from threading import Lock
from urllib.parse import urlparse
from flask import Flask, g, request, jsonify, render_template, session, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

# Configuration reads the environment at import time, so load .env first.
from config import Config
from audit import log_audit_event, AuditEventType

try:
    from authlib.integrations.flask_client import OAuth
except ImportError:
    OAuth = None

class JsonFormatter(logging.Formatter):
    """Small structured logger that deliberately excludes request bodies/PHI."""

    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload)


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("aegismind")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = configure_logging()


class InMemoryRateLimiter:
    """A bounded local safety limiter; use Redis/Flask-Limiter when scaled out."""

    def __init__(self):
        self._requests = defaultdict(deque)
        self._lock = Lock()

    def check(self, bucket, limit, window_seconds):
        now = time.monotonic()
        with self._lock:
            entries = self._requests[bucket]
            while entries and entries[0] <= now - window_seconds:
                entries.popleft()
            if len(entries) >= limit:
                retry_after = max(1, int(window_seconds - (now - entries[0])) + 1)
                return False, retry_after
            entries.append(now)
            # Keep memory bounded even if a hostile client rotates identities.
            if len(self._requests) > 10_000:
                self._requests.pop(next(iter(self._requests)), None)
            return True, 0


rate_limiter = InMemoryRateLimiter()


def rate_limit(limit):
    """Limit write-heavy public routes by client IP and route."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            # Do not trust X-Forwarded-For here: it is client-controlled unless
            # a trusted proxy and ProxyFix are explicitly configured.
            client_ip = request.remote_addr or "unknown"
            allowed, retry_after = rate_limiter.check(
                f"{request.endpoint}:{client_ip}", limit, Config.RATE_LIMIT_WINDOW_SECONDS
            )
            if not allowed:
                response = jsonify({"error": "rate_limited", "message": "Please wait a moment before trying again."})
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                return response
            return view(*args, **kwargs)
        return wrapped
    return decorator


def counselor_access_required(view):
    """Protect counselor data in production once COUNSELOR_API_KEY is configured."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if Config.COUNSELOR_API_KEY and request.headers.get("X-Counselor-Key") != Config.COUNSELOR_API_KEY:
            return jsonify({"error": "counselor_authorization_required"}), 401
        return view(*args, **kwargs)
    return wrapped


app = Flask(__name__)
# Set FLASK_SECRET_KEY in the environment for every deployed instance. The
# generated fallback keeps local development safe but invalidates sessions after
# each server restart, so it must not be relied on in production.
app.secret_key = Config.SECRET_KEY or os.urandom(32)
app.config.update(
    MAX_CONTENT_LENGTH=Config.MAX_REQUEST_BYTES,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=Config.IS_PRODUCTION,
)

# ---------------------------------------------------------------------------
# flask-talisman: Security headers (CSP, HSTS, X-Frame-Options, etc.)
# Falls back gracefully if flask-talisman is not installed.
# ---------------------------------------------------------------------------
try:
    from flask_talisman import Talisman

    talisman = Talisman(
        app,
        content_security_policy={
            "default-src": "'self'",
            "script-src": ["'self'", "'unsafe-inline'"],
            "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            "font-src": ["'self'", "https://fonts.gstatic.com"],
            "img-src": ["'self'", "data:"],
            "connect-src": ["'self'", "https://api.groq.com"],
            "frame-src": ["https://meet.jit.si"],
            "base-uri": "'self'",
            "object-src": "'none'",
            "frame-ancestors": "'none'",
        },
        force_https=Config.FORCE_HTTPS,
        strict_transport_security=Config.FORCE_HTTPS,
        session_cookie_secure=Config.IS_PRODUCTION,
        referrer_policy="strict-origin-when-cross-origin",
    )
except ImportError:
    pass

GOOGLE_CLIENT_ID = Config.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = Config.GOOGLE_CLIENT_SECRET

oauth = OAuth(app) if OAuth else None
google = None
if oauth and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google = oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# ===========================================================================
# EXTERNAL API INTEGRATION SLOTS (Fill these with your production keys / env vars)
# ===========================================================================
OPENAI_API_KEY      = Config.OPENAI_API_KEY
ANTHROPIC_API_KEY   = Config.ANTHROPIC_API_KEY
GEMINI_API_KEY      = Config.GEMINI_API_KEY
GROQ_API_KEY        = Config.GROQ_API_KEY
TELE_MANAS_API_URL  = Config.TELE_MANAS_API_URL
TWILIO_ACCOUNT_SID  = Config.TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN   = Config.TWILIO_AUTH_TOKEN
DATABASE_URL        = Config.DATABASE_URL


def configured_api_origin():
    """Allow only a well-formed configured gateway origin in browser CSP."""
    parsed = urlparse(Config.API_BASE_URL)
    if parsed.scheme in {"https", "http"} and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return ""


@app.before_request
def begin_request():
    """Attach a correlation id and reject oversized/non-JSON API writes early."""
    g.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    g.request_started_at = time.perf_counter()
    if request.method in {"POST", "PUT", "PATCH"} and request.path.startswith("/api/"):
        # Empty mutation requests remain valid for compatibility with the
        # report/review actions; supplied bodies must be JSON objects.
        if request.content_length and not request.is_json:
            return jsonify({"error": "json_body_required"}), 415


@app.after_request
def secure_and_log_response(response):
    """Set browser protections compatible with the current inline UI handlers."""
    response.headers["X-Request-ID"] = getattr(g, "request_id", "")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), payment=(), usb=()"
    connect_sources = "'self' https://api.groq.com"
    if configured_api_origin():
        connect_sources += f" {configured_api_origin()}"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "  # Existing UI uses inline click handlers.
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        f"connect-src {connect_sources}; "
        "frame-src https://meet.jit.si; "
        "base-uri 'self'; object-src 'none'; frame-ancestors 'none'"
    )
    if Config.FORCE_HTTPS:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    duration_ms = round((time.perf_counter() - getattr(g, "request_started_at", time.perf_counter())) * 1000, 1)
    logger.info(
        "http_request",
        extra={
            "request_id": getattr(g, "request_id", ""),
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "request_too_large", "message": "Request body is too large."}), 413


def json_payload():
    """Return a dictionary only; routes never trust another JSON top-level type."""
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def validated_score(data, field, default=5.0):
    """Parse clinical sliders and keep malformed client input out of the scoring pipeline."""
    try:
        value = float(data.get(field, default))
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number")
    if not 1.0 <= value <= 10.0:
        raise ValueError(f"{field} must be between 1 and 10")
    return value


def validated_voice_score(data):
    try:
        value = float(data.get("voice_score", 0.7))
    except (TypeError, ValueError):
        raise ValueError("voice_score must be a number")
    if not 0.0 <= value <= 1.0:
        raise ValueError("voice_score must be between 0 and 1")
    return value


# ---------------------------------------------------------------------------
# Request Validation (Pydantic-style without dependency)
# ---------------------------------------------------------------------------
class ValidationError(Exception):
    """Raised when request validation fails."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def validate_checkin_payload(data: dict) -> dict:
    """Validate and sanitize check-in submission payload."""
    errors = []

    token = str(data.get("token", "")).strip()
    if not token:
        errors.append(("token", "Token is required"))

    text = str(data.get("text", "")).strip()
    if not text:
        errors.append(("text", "Journal text is required"))
    elif len(text) > 800:
        errors.append(("text", "Text must be 800 characters or fewer"))

    try:
        valence = float(data.get("valence", 5.0))
        if not 1.0 <= valence <= 10.0:
            errors.append(("valence", "Must be between 1 and 10"))
    except (TypeError, ValueError):
        errors.append(("valence", "Must be a number"))

    try:
        arousal = float(data.get("arousal", 5.0))
        if not 1.0 <= arousal <= 10.0:
            errors.append(("arousal", "Must be between 1 and 10"))
    except (TypeError, ValueError):
        errors.append(("arousal", "Must be a number"))

    try:
        voice_score = float(data.get("voice_score", 0.7))
        if not 0.0 <= voice_score <= 1.0:
            errors.append(("voice_score", "Must be between 0 and 1"))
    except (TypeError, ValueError):
        errors.append(("voice_score", "Must be a number"))

    if errors:
        raise ValidationError(errors[0][0], errors[0][1])

    return {
        "token": token,
        "text": text,
        "valence": valence,
        "arousal": arousal,
        "voice_score": voice_score,
    }


def validate_chat_payload(data: dict) -> dict:
    """Validate and sanitize chat message payload."""
    token = str(data.get("token", "ANON")).strip() or "ANON"
    message = str(data.get("message", "")).strip()
    lang = str(data.get("lang", "en")).lower()

    if not message:
        raise ValidationError("message", "Message is required")
    if len(message) > 1200:
        raise ValidationError("message", "Message must be 1200 characters or fewer")
    if lang not in {"en", "hi"}:
        raise ValidationError("lang", "Language must be 'en' or 'hi'")

    return {"token": token, "message": message, "lang": lang}


def validate_forum_payload(data: dict) -> dict:
    """Validate and sanitize forum post payload."""
    text = str(data.get("text", "")).strip()
    lang = str(data.get("lang", "en")).lower()

    if not text or len(text) > 800:
        raise ValidationError("text", "Text must be 1-800 characters")
    if lang not in {"en", "hi"}:
        raise ValidationError("lang", "Language must be 'en' or 'hi'")

    return {"text": text, "lang": lang}

# ---------------------------------------------------------------------------
# In-Memory Data Stores (with clean schema for PostgreSQL/SQLite migration)
# ---------------------------------------------------------------------------
USER_PROFILES = {}          # token → profile dict
CHECK_IN_HISTORY = {}       # token → list of check-in records
FORUM_POSTS = []            # global anonymous forum
COUNSELOR_QUEUE = []        # flagged cases for HITL review
SEV1_CASES = []             # critical SEV-1 lockouts
CHAT_SESSIONS = {}          # token → list of chat messages

# No seed data — everything starts empty. Users create their own sessions,
# posts, and counselor entries through the API.

# ---------------------------------------------------------------------------
# AGENT 1: guard_agent — Safety & Ingestion Guard
# ---------------------------------------------------------------------------
CRISIS_PATTERNS = [
    r"\bwant\s+to\s+die\b",
    r"\bkill\s+myself\b",
    r"\bend\s+it\s+all\b",
    r"\bbetter\s+off\s+dead\b",
    r"\bcan'?t\s+go\s+on\b",
    r"\bno\s+reason\s+to\s+live\b",
    r"\bwish\s+i\s+was\s+dead\b",
    r"\bsuicide\b",
    r"\bself.?harm\b",
    r"\bmarne\s+ki\b",          # Hindi
    r"\bjeena\s+nahi\b",        # Hindi
    r"\bzindagi\s+khatam\b",    # Hindi
]
_CRISIS_RE = re.compile("|".join(CRISIS_PATTERNS), re.IGNORECASE)

def guard_agent(text: str, token: str) -> dict:
    """Verifies client consent and scans raw text for acute crisis keywords."""
    profile = USER_PROFILES.get(token, {})
    if not profile.get("consent", False):
        return {"route": "reject", "reason": "no_consent"}

    if _CRISIS_RE.search(text):
        return {"route": "crisis", "matched_pattern": True}

    return {"route": "standard"}


# ---------------------------------------------------------------------------
# AGENT 2: nlp_agent — Linguistic Profiling Agent
# ---------------------------------------------------------------------------
FIRST_PERSON_SINGULAR = {"i", "me", "my", "myself", "mine"}
ABSOLUTIST_WORDS = {
    "always", "never", "completely", "nothing", "everything", "everyone",
    "nobody", "impossible", "utterly", "absolutely", "totally", "forever",
    "no one", "all", "must", "only", "worst", "useless", "worthless",
    "hopeless", "pointless",
}

def nlp_agent(text: str, valence: float, arousal: float, voice_score: float) -> dict:
    """Calculates first-person pronoun density, absolutist score, and distress composites."""
    words = re.findall(r"\b\w+\b", text.lower())
    total_words = max(len(words), 1)

    # First-person pronoun density
    fp_count = sum(1 for w in words if w in FIRST_PERSON_SINGULAR)
    fp_density = round(fp_count / total_words, 3)

    # Absolutist vocabulary scanner
    abs_count = sum(1 for w in words if w in ABSOLUTIST_WORDS)
    if "no one" in text.lower():
        abs_count += text.lower().count("no one")
    abs_density = round(abs_count / total_words, 3)

    # Inversion scores (1 to 10 scale)
    valence_distress = round((10.0 - valence) / 9.0, 3)
    arousal_distress = round(abs(arousal - 5.5) / 4.5, 3)
    voice_distress = round(max(0.0, min(1.0, 1.0 - voice_score)), 3)

    # Composite NLP score
    nlp_score = round(
        (fp_density * 0.25) +
        (abs_density * 0.25) +
        (valence_distress * 0.30) +
        (arousal_distress * 0.10) +
        (voice_distress * 0.10),
        4
    )

    return {
        "total_words": total_words,
        "fp_count": fp_count,
        "fp_density": fp_density,
        "abs_count": abs_count,
        "abs_density": abs_density,
        "valence_distress": valence_distress,
        "arousal_distress": arousal_distress,
        "voice_distress": voice_distress,
        "nlp_score": nlp_score,
    }


# ---------------------------------------------------------------------------
# AGENT 3: trajectory_agent — Trajectory Velocity Agent
# ---------------------------------------------------------------------------
def trajectory_agent(token: str, current_nlp_score: float) -> dict:
    """Calculates rolling DPI (Distress Prediction Index) and trajectory velocity slope (ΔDPI)."""
    history = CHECK_IN_HISTORY.get(token, [])
    recent_scores = [r.get("nlp_score") for r in history[-7:] if isinstance(r.get("nlp_score"), (int, float))] if history else []
    recent_scores.append(current_nlp_score)

    if len(recent_scores) == 1:
        dpi = round(current_nlp_score, 4)
        delta_dpi = 0.0
        slope = 0.0
    else:
        weights = list(range(1, len(recent_scores) + 1))
        weighted_sum = sum(s * w for s, w in zip(recent_scores, weights))
        dpi = round(weighted_sum / sum(weights), 4)

        n = len(recent_scores)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(recent_scores) / n
        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, recent_scores))
        denominator = sum((xi - x_mean) ** 2 for xi in x) or 1e-9
        slope = numerator / denominator
        delta_dpi = round(slope, 4)

    dpi = max(0.0, min(1.0, dpi))

    if dpi >= 0.70 or delta_dpi >= 0.15:
        risk_level = "critical"
    elif dpi >= 0.40 or delta_dpi >= 0.05:
        risk_level = "moderate"
    else:
        risk_level = "low"

    sparkline = [round(s, 3) for s in recent_scores[-7:]]
    while len(sparkline) < 7:
        sparkline.insert(0, None)

    return {
        "dpi": dpi,
        "delta_dpi": delta_dpi,
        "slope": round(slope, 4) if "slope" in dir() else 0.0,
        "risk_level": risk_level,
        "sparkline": sparkline,
        "history_count": len(history),
    }


# ---------------------------------------------------------------------------
# AGENT 4: crisis_agent — Crisis Intercept Agent
# ---------------------------------------------------------------------------
def crisis_agent(token: str, text: str, trajectory: dict) -> dict:
    """Locks UI into SEV-1 emergency mode and alerts counselor queue."""
    case_id = uuid.uuid4().hex[:8].upper()
    profile = USER_PROFILES.get(token, {})

    sev1_record = {
        "id": case_id,
        "token": token,
        "alias": profile.get("alias", "Anonymous"),
        "text_fragment": text[:120] + "…" if len(text) > 120 else text,
        "dpi": trajectory.get("dpi", 1.0),
        "delta_dpi": trajectory.get("delta_dpi", 0.0),
        "risk_level": "critical",
        "sev": "SEV-1",
        "flagged_at": datetime.now(timezone.utc).isoformat(),
        "jitsi_room": f"AegisMind-Case-{case_id}",
        "reviewed": False,
    }
    SEV1_CASES.append(sev1_record)
    COUNSELOR_QUEUE.insert(0, {**sev1_record, "triggers": ["crisis_phrase_detected"]})

    # Optional: Webhook dispatch placeholder for Tele-MANAS emergency integration
    if TELE_MANAS_API_URL:
        # requests.post(TELE_MANAS_API_URL, json=sev1_record, timeout=5)
        pass

    return {
        "action": "CRISIS_LOCK",
        "case_id": case_id,
        "jitsi_room": sev1_record["jitsi_room"],
        "helplines": {
            "tele_manas": "14416",
            "kiran": "1800-599-0019",
            "us_988": "988",
        },
    }


# ---------------------------------------------------------------------------
# AGENT 5: hitl_agent — HITL Coordinator Agent
# ---------------------------------------------------------------------------
def hitl_agent(token: str, trajectory: dict, nlp_result: dict, profile: dict) -> dict:
    """Enqueues moderate distress cases into counselor review queue."""
    case_id = uuid.uuid4().hex[:8].upper()
    jitsi_room = f"AegisMind-Case-{case_id}"

    triggers = []
    if nlp_result["fp_density"] > 0.15:
        triggers.append("pronoun_density")
    if nlp_result["abs_density"] > 0.08:
        triggers.append("absolutist_language")
    if nlp_result["valence_distress"] > 0.60:
        triggers.append("low_valence")
    if nlp_result["voice_distress"] > 0.60:
        triggers.append("voice_cadence")

    queue_entry = {
        "id": case_id,
        "token": token,
        "alias": profile.get("alias", "Anonymous"),
        "dpi": trajectory["dpi"],
        "delta_dpi": trajectory["delta_dpi"],
        "risk_level": trajectory["risk_level"],
        "triggers": triggers if triggers else ["low_valence"],
        "valence_distress": nlp_result["valence_distress"],
        "nlp_score": nlp_result["nlp_score"],
        "flagged_at": datetime.now(timezone.utc).isoformat(),
        "jitsi_room": jitsi_room,
        "reviewed": False,
        "sev": "SEV-2",
    }
    COUNSELOR_QUEUE.insert(0, queue_entry)

    return {
        "action": "HITL_QUEUED",
        "case_id": case_id,
        "jitsi_room": jitsi_room,
    }


# ---------------------------------------------------------------------------
# CONSOLING COMPANION AI ENGINE (Rule-Based Empathy + LLM API Plugs)
# ---------------------------------------------------------------------------
def generate_companion_reply(user_msg: str, lang: str = "en") -> dict:
    """
    Empathetic, soothing conversational response generator.
    Includes clinical CBT validation, grounding prompts, and LLM plug-in architecture.
    """
    msg_lower = user_msg.lower().strip()

    # 1. Safety Intercept
    if _CRISIS_RE.search(user_msg):
        if lang == "hi":
            return {
                "reply": "मैं समझता हूँ कि आप इस समय बहुत गहरे दर्द में हैं। कृपया याद रखें कि आप अकेले नहीं हैं और आपकी जान बेहद कीमती है। मैं चाहता हूँ कि आप तुरंत 14416 (टेली-मानस) या 1800-599-0019 पर कॉल करें। प्रशिक्षित परामर्शदाता 24/7 आपकी मदद के लिए तैयार हैं।",
                "is_crisis": True
            }
        return {
            "reply": "I hear how much pain you are carrying right now, and I want you to know you are not alone. Your life has immense value. Please reach out to someone who can support you right now — call or text 14416 (Tele-MANAS) or 988. There are caring professionals available 24/7.",
            "is_crisis": True
        }

    # 2. External LLM API Hook (Groq API - Primary, then OpenAI/Anthropic/Gemini fallbacks)
    if GROQ_API_KEY:
        try:
            from groq import Groq
            # The bounded timeout prevents an upstream model outage from tying
            # up every Flask worker.  Move this call to Celery/Redis when a
            # broker is configured for production scale.
            client = Groq(api_key=GROQ_API_KEY, timeout=Config.GROQ_TIMEOUT_SECONDS)
            
            system_prompt = """You are Aegis Companion — a supportive AI listener for mental wellness.
You are NOT a therapist, counselor, or crisis line. You do not diagnose, treat, or replace professional care.

CORE PRINCIPLES:
• Validate first: "That sounds really hard" / "It makes sense you'd feel that way"
• No toxic positivity: Avoid "just think positive," "it could be worse," "you'll be fine"
• No fixing: Don't problem-solve unless asked. Ask "Would it help to talk through it, or would you prefer a grounding exercise?"
• Gentle boundaries: "I'm here to listen. For clinical support, a therapist can help with that."
• Crisis-aware: If ANY self-harm/suicide language → immediate helpline + "Your life matters"

RESPONSE STYLE:
• 2-3 sentences max. One gentle question or invitation.
• Warm, calm, non-clinical. Use "I hear you" not "I understand" (you don't).
• Offer ONE grounding technique if distress signals present (4-7-8 breath, 5-4-3-2-1, box breathing).
• Hindi responses: Natural Hinglish ok. Avoid overly formal "shuddh" Hindi.

EVERY RESPONSE must be safe for someone in acute distress.
If unsure, err toward: "I'm here. You're not alone. Help is available 24/7: 14416 (Tele-MANAS), 988, 1800-599-0019 (KIRAN)."
"""
            
            response = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.7,
                max_tokens=200,
            )
            reply_text = response.choices[0].message.content.strip()
            
            # Proactive helpline injection for moderate-high distress (non-crisis)
            high_distress_signals = [
                "hopeless", "overwhelmed", "can't cope", "breaking down", "drowning",
                "giving up", "no point", "worthless", "burden", "ending it",
                "निराश", "टूट", "सहन नहीं", "खत्म", "बेकार", "बोझ"
            ]
            if any(signal in msg_lower for signal in high_distress_signals):
                if lang == "hi":
                    reply_text += "\n\nअगर यह बहुत भारी लगे, तो 14416 (टेली-मानस) और 1800-599-0019 (किरण) मुफ़्त हैं, 24/7। आपको अकेले नहीं सहना पड़ेगा।"
                else:
                    reply_text += "\n\nIf it gets too heavy, 14416 (Tele-MANAS) and 988 are free, 24/7. You don't have to carry this alone."
            
            return {"reply": reply_text, "is_crisis": False}
        except Exception:
            logger.warning("companion_provider_unavailable", extra={"request_id": getattr(g, "request_id", None)})
            pass

    if OPENAI_API_KEY:
        try:
            # Placeholder for OpenAI / Claude / Gemini API call
            pass
        except Exception:
            pass

    # 3. Empathetic Psychological Response Matrix (Deterministic & Instant)
    if lang == "hi":
        if any(w in msg_lower for w in ["तनाव", "घबराहट", "चिंता", "डर", "डर लग रहा", "anxious", "panic"]):
            replies = [
                "चिंता महसूस होना स्वाभाविक है। आइए एक पल के लिए रुकें। अपनी पीठ सीधी करें, एक लंबी गहरी सांस लें और 4 सेकंड तक रोकें। आप सुरक्षित हैं।",
                "जब मन अशांत हो, तो वर्तमान में लौटना सबसे अच्छा होता है। अपने आसपास देखें और 3 ऐसी चीजें ढूंढें जिनका रंग हरा या नीला हो।"
            ]
        elif any(w in msg_lower for w in ["अकेला", "अकेलापन", "lonely", "alone"]):
            replies = [
                "अकेलापन बहुत भारी लग सकता है। मैं यहाँ आपके साथ हूँ और आपकी बात सुन रहा हूँ। आप जो महसूस कर रहे हैं, वह साझा करने के लिए धन्यवाद।",
                "याद रखें कि अकेलापन एक भावना है, आपकी पूरी सच्चाई नहीं। आप महत्वपूर्ण हैं और आपकी भावनाएं मायने रखती हैं।"
            ]
        elif any(w in msg_lower for w in ["थकान", "थक गया", "मन नहीं", "उदास", "sad", "tired"]):
            replies = [
                "आज का दिन कठिन रहा लगता है। कभी-कभी सिर्फ आराम करना और खुद पर कोई दबाव न डालना ही सबसे अच्छी देखभाल है।",
                "खुद के प्रति थोड़ा दयालु बनें। आपको सब कुछ आज ही ठीक करने की ज़रूरत नहीं है। एक घूंट पानी पिएं और गहरी सांस लें।"
            ]
        else:
            replies = [
                "मैं आपकी बात ध्यान से सुन रहा हूँ। जो कुछ भी आपके मन पर बोझ बना हुआ है, उसे यहाँ स्वतंत्र रूप से कह सकते हैं।",
                "अपने विचारों को व्यक्त करने के लिए धन्यवाद। आप बहुत हिम्मत के साथ आगे बढ़ रहे हैं। मैं हर कदम पर आपके साथ हूँ।"
            ]
    else:
        if any(w in msg_lower for w in ["anxious", "anxiety", "panic", "overwhelmed", "stressed", "scared", "nervous"]):
            replies = [
                "It is completely okay to feel overwhelmed. Let's take a pause together. Relax your shoulders, unclamp your jaw, and take one slow, deep breath in... and out.",
                "Anxiety makes everything feel urgent, but right now, you are safe in this moment. Try feeling your feet firmly on the ground. I'm right here with you."
            ]
        elif any(w in msg_lower for w in ["lonely", "alone", "nobody", "isolated"]):
            replies = [
                "Feeling lonely is such a heavy weight to carry. Thank you for reaching out and sharing this space with me. You matter, and I am here listening to you.",
                "Loneliness can make us forget our connection to the world, but your presence is meaningful. Take it gently today."
            ]
        elif any(w in msg_lower for w in ["sad", "depressed", "down", "crying", "tired", "exhausted", "hopeless"]):
            replies = [
                "I hear you, and it's okay to not be okay today. You don't have to carry the whole world on your shoulders right now. Give yourself permission to just rest.",
                "You have been carrying a lot lately. Be gentle with yourself today. Even the smallest step — like drinking a glass of water — is a win."
            ]
        elif any(w in msg_lower for w in ["thank", "thanks", "helpful", "good", "better"]):
            replies = [
                "I am so glad to hear that. You are doing wonderful work checking in with yourself today.",
                "You're very welcome. Remember, your resilience comes from within you. I'm always here whenever you need a calm ear."
            ]
        else:
            replies = [
                "Thank you for sharing that with me. What you're feeling is valid, and I'm here to support you through it. Would you like to tell me more, or try a quick calming exercise?",
                "I'm listening without any judgment. Take all the time you need. How is your body feeling right now as you write this?"
            ]

    return {
        "reply": random.choice(replies),
        "is_crisis": False
    }


def generate_alias() -> str:
    adjectives = ["Quiet", "Gentle", "Steady", "Calm", "Warm", "Clear", "Soft", "Bright", "Still", "Kind", "Serene", "Hopeful"]
    nouns = ["Willow", "River", "Stone", "Ember", "Harbor", "Dawn", "Meadow", "Lantern", "Compass", "Anchor", "Candle", "Shore"]
    return f"{random.choice(adjectives)}{random.choice(nouns)}{random.randint(10, 99)}"


# ---------------------------------------------------------------------------
# Flask Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", api_base_url=Config.API_BASE_URL)


@app.route("/health")
def health():
    """Liveness/readiness signal without exposing secrets or user data."""
    components = {"application": "ok"}
    status = "ok"

    if Config.DATABASE_URL:
        components["storage"] = "configured"
    else:
        components["storage"] = "in_memory"
        if Config.IS_PRODUCTION:
            status = "degraded"

    if Config.REDIS_URL or Config.CELERY_BROKER_URL:
        components["async_worker"] = "configured"
    else:
        components["async_worker"] = "not_configured"

    if Config.GROQ_API_KEY:
        components["llm"] = "configured"
    else:
        components["llm"] = "rule_based_only"
        if Config.IS_PRODUCTION:
            status = "degraded"

    return jsonify({"status": status, "components": components}), (200 if status == "ok" else 503)


@app.route("/login")
def login():
    """Render the shared Google sign-in/sign-up entry point."""
    if session.get("google_user"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/auth/google")
def google_login():
    """Start a Google OpenID Connect sign-in flow."""
    if google is None:
        if request.headers.get("Accept", "").startswith("application/json"):
            return jsonify({
                "error": "google_oauth_not_configured",
                "message": "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file to enable Google sign-in.",
            }), 501
        return redirect(url_for("login") + "?error=google_not_configured")

    return google.authorize_redirect(url_for("google_callback", _external=True))


@app.route("/auth/google/callback")
def google_callback():
    """Finish Google sign-in and retain only minimal identity in the session."""
    if google is None:
        return redirect(url_for("index"))

    token = google.authorize_access_token()
    user = token.get("userinfo", {})
    if not user.get("sub") or not user.get("email"):
        return jsonify({"error": "google_identity_unavailable"}), 400

    # Keep Google account identity separate from anonymous wellness records.
    session["google_user"] = {
        "google_sub": user["sub"],
        "email": user["email"],
        "name": user.get("name", ""),
        "picture": user.get("picture", ""),
    }

    log_audit_event(
        AuditEventType.AUTH_LOGIN,
        details={"provider": "google", "email_domain": user["email"].split("@")[-1]},
        ip_address=request.remote_addr,
    )

    return redirect(url_for("index"))


@app.route("/auth/logout")
def google_logout():
    """Sign out of this app without signing the user out of Google globally."""
    log_audit_event(
        AuditEventType.AUTH_LOGOUT,
        ip_address=request.remote_addr,
    )
    session.pop("google_user", None)
    return redirect(url_for("index"))


@app.route("/api/register", methods=["POST"])
@rate_limit(Config.FORUM_RATE_LIMIT)
def register():
    data = json_payload()
    consent = data.get("consent", False)
    if not consent:
        return jsonify({"error": "Consent required"}), 400

    token = uuid.uuid4().hex[:16].upper()
    alias = generate_alias()
    USER_PROFILES[token] = {
        "token": token,
        "alias": alias,
        "consent": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    CHECK_IN_HISTORY[token] = []
    CHAT_SESSIONS[token] = []

    log_audit_event(
        AuditEventType.SESSION_CREATED,
        actor_token=token,
        details={"alias": alias},
        ip_address=request.remote_addr,
    )

    return jsonify({
        "token": token,
        "alias": alias,
        "message": "Registered successfully",
    })


@app.route("/api/login", methods=["POST"])
@rate_limit(Config.FORUM_RATE_LIMIT)
def api_login():
    """Sign in or restore session by anonymous token or alias."""
    data = json_payload()
    token = str(data.get("token", "")).strip().upper()
    alias = str(data.get("alias", "")).strip()

    if not token and not alias:
        return jsonify({"error": "token_or_alias_required", "message": "Please provide your session token or alias to sign in."}), 400

    # Match by token
    if token and token in USER_PROFILES:
        profile = USER_PROFILES[token]
        history = CHECK_IN_HISTORY.get(token, [])
        log_audit_event(
            AuditEventType.AUTH_LOGIN,
            actor_token=token,
            details={"method": "token_restore", "alias": profile.get("alias")},
            ip_address=request.remote_addr,
        )
        return jsonify({
            "status": "ok",
            "token": token,
            "alias": profile.get("alias", "Anonymous"),
            "checkin_count": len(history),
            "message": "Session restored successfully",
        })

    # Match by alias
    if alias:
        for t, prof in USER_PROFILES.items():
            if prof.get("alias", "").lower() == alias.lower():
                history = CHECK_IN_HISTORY.get(t, [])
                return jsonify({
                    "status": "ok",
                    "token": t,
                    "alias": prof.get("alias"),
                    "checkin_count": len(history),
                    "message": "Session restored successfully",
                })

    # If token format is reasonable (8+ chars), initialize/restore session profile
    if token and len(token) >= 8:
        new_alias = alias or generate_alias()
        USER_PROFILES[token] = {
            "token": token,
            "alias": new_alias,
            "consent": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        CHECK_IN_HISTORY.setdefault(token, [])
        CHAT_SESSIONS.setdefault(token, [])
        return jsonify({
            "status": "ok",
            "token": token,
            "alias": new_alias,
            "checkin_count": 0,
            "message": "Session activated successfully",
        })

    return jsonify({"error": "session_not_found", "message": "Session token or alias not found. Check the spelling or create a new session."}), 404


@app.route("/api/checkin", methods=["POST"])
@rate_limit(Config.CHECKIN_RATE_LIMIT)
def checkin():
    data = json_payload()
    token = str(data.get("token", "")).strip()
    text = str(data.get("text", "")).strip()
    if not token or token not in USER_PROFILES:
        return jsonify({"error": "invalid_session", "message": "Please accept consent again to create a secure session."}), 401
    if len(text) > 800:
        return jsonify({"error": "text_too_long", "message": "Check-in text must be 800 characters or fewer."}), 400
    try:
        valence = validated_score(data, "valence")
        arousal = validated_score(data, "arousal")
        voice_score = validated_voice_score(data)
    except ValueError as error:
        return jsonify({"error": "invalid_checkin", "message": str(error)}), 400

    guard_result = guard_agent(text, token)
    if guard_result["route"] == "reject":
        return jsonify({"error": "Consent required before submitting check-ins"}), 403

    # Acute language must bypass the standard scoring pipeline.  This mirrors
    # the Safety & Ingestion Guard contract in AGENTS.md.
    if guard_result["route"] == "crisis":
        timestamp = datetime.now(timezone.utc).isoformat()
        trajectory = {
            "dpi": 1.0,
            "delta_dpi": 0.0,
            "slope": 0.0,
            "risk_level": "critical",
            "sparkline": [None] * 6 + [1.0],
            "history_count": len(CHECK_IN_HISTORY.get(token, [])),
        }
        CHECK_IN_HISTORY.setdefault(token, []).append({
            "id": str(uuid.uuid4()), "timestamp": timestamp, "text": text,
            "valence": valence, "arousal": arousal, "voice_score": voice_score,
            "nlp_score": None, "dpi": 1.0, "delta_dpi": 0.0, "risk_level": "critical",
        })
        agent_action = crisis_agent(token, text, trajectory)
        agent_action["agent"] = "crisis_agent"

        log_audit_event(
            AuditEventType.CRISIS_ESCALATED,
            actor_token=token,
            target_id=agent_action.get("case_id"),
            details={"source": "guard_agent", "risk_level": "critical"},
            ip_address=request.remote_addr,
        )

        return jsonify({
            "status": "crisis", "token": token,
            "alias": USER_PROFILES[token].get("alias", "Anonymous"),
            "nlp": None, "trajectory": trajectory, "agent_action": agent_action,
            "timestamp": timestamp,
        })

    nlp_result = nlp_agent(text, valence, arousal, voice_score)
    trajectory = trajectory_agent(token, nlp_result["nlp_score"])

    record = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "text": text,
        "valence": valence,
        "arousal": arousal,
        "voice_score": voice_score,
        **nlp_result,
        "dpi": trajectory["dpi"],
        "delta_dpi": trajectory["delta_dpi"],
        "risk_level": trajectory["risk_level"],
    }
    if token not in CHECK_IN_HISTORY:
        CHECK_IN_HISTORY[token] = []
    CHECK_IN_HISTORY[token].append(record)

    profile = USER_PROFILES.get(token, {})
    agent_action = None

    if guard_result["route"] == "crisis" or trajectory["risk_level"] == "critical":
        agent_action = crisis_agent(token, text, trajectory)
        agent_action["agent"] = "crisis_agent"
        log_audit_event(
            AuditEventType.CRISIS_ESCALATED,
            actor_token=token,
            target_id=agent_action.get("case_id"),
            details={"source": "trajectory_agent", "risk_level": trajectory["risk_level"]},
            ip_address=request.remote_addr,
        )
    elif trajectory["risk_level"] == "moderate":
        agent_action = hitl_agent(token, trajectory, nlp_result, profile)
        agent_action["agent"] = "hitl_agent"
        log_audit_event(
            AuditEventType.CASE_REVIEWED,
            actor_token=token,
            target_id=agent_action.get("case_id"),
            details={"risk_level": "moderate", "triggers": agent_action.get("triggers", [])},
            ip_address=request.remote_addr,
        )

    log_audit_event(
        AuditEventType.CHECKIN_SUBMITTED,
        actor_token=token,
        details={
            "risk_level": trajectory["risk_level"],
            "dpi": trajectory["dpi"],
        },
        ip_address=request.remote_addr,
    )

    return jsonify({
        "status": "ok",
        "token": token,
        "alias": profile.get("alias", "Anonymous"),
        "nlp": nlp_result,
        "trajectory": trajectory,
        "agent_action": agent_action,
        "timestamp": record["timestamp"],
    })


@app.route("/api/chat", methods=["POST"])
@rate_limit(Config.CHAT_RATE_LIMIT)
def chat():
    """Consoling AI Companion Endpoint."""
    data = json_payload()
    token = str(data.get("token", "ANON")).strip() or "ANON"
    message = str(data.get("message", "")).strip()
    lang = str(data.get("lang", "en")).lower()

    if not message:
        return jsonify({"error": "Message required"}), 400
    if len(message) > 1200:
        return jsonify({"error": "message_too_long", "message": "Message must be 1200 characters or fewer."}), 400
    if lang not in {"en", "hi"}:
        return jsonify({"error": "invalid_language"}), 400

    response_data = generate_companion_reply(message, lang)

    if token not in CHAT_SESSIONS:
        CHAT_SESSIONS[token] = []

    CHAT_SESSIONS[token].append({
        "sender": "user",
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    CHAT_SESSIONS[token].append({
        "sender": "companion",
        "message": response_data["reply"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return jsonify({
        "reply": response_data["reply"],
        "is_crisis": response_data.get("is_crisis", False),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.route("/api/history/<token>", methods=["GET"])
def get_history(token):
    history = CHECK_IN_HISTORY.get(token, [])
    return jsonify({
        "token": token,
        "count": len(history),
        "records": history[-30:],
    })


@app.route("/api/forum", methods=["GET"])
def get_forum():
    posts = [p for p in FORUM_POSTS if p.get("reports", 0) < 5]
    posts_sorted = sorted(posts, key=lambda x: x["timestamp"], reverse=True)
    return jsonify({"posts": posts_sorted[:50]})


@app.route("/api/forum", methods=["POST"])
@rate_limit(Config.FORUM_RATE_LIMIT)
def create_forum_post():
    data = json_payload()
    text = str(data.get("text", "")).strip()
    lang = str(data.get("lang", "en")).lower()

    if not text or len(text) > 800:
        return jsonify({"error": "Text must be 1–800 characters"}), 400
    if lang not in {"en", "hi"}:
        return jsonify({"error": "invalid_language"}), 400

    if _CRISIS_RE.search(text):
        return jsonify({
            "error": "crisis_detected",
            "message": "We noticed you may be in distress. Please use the 'I Need Help Now' button.",
        }), 422

    alias = generate_alias()
    post = {
        "id": str(uuid.uuid4()),
        "alias": alias,
        "text": text,
        "lang": lang,
        "reactions": {"heart": 0, "hug": 0, "star": 0},
        "flagged": False,
        "reports": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    FORUM_POSTS.append(post)

    log_audit_event(
        AuditEventType.FORUM_POST_CREATED,
        details={"post_id": post["id"], "lang": lang},
        ip_address=request.remote_addr,
    )

    return jsonify(post), 201


@app.route("/api/forum/<post_id>/react", methods=["POST"])
@rate_limit(Config.FORUM_RATE_LIMIT)
def react_to_post(post_id):
    data = json_payload()
    reaction = data.get("reaction", "heart")
    if reaction not in ("heart", "hug", "star"):
        return jsonify({"error": "Invalid reaction"}), 400

    for post in FORUM_POSTS:
        if post["id"] == post_id:
            post["reactions"][reaction] = post["reactions"].get(reaction, 0) + 1
            return jsonify({"reactions": post["reactions"]})

    return jsonify({"error": "Post not found"}), 404


@app.route("/api/forum/<post_id>/report", methods=["POST"])
@rate_limit(Config.FORUM_RATE_LIMIT)
def report_post(post_id):
    for post in FORUM_POSTS:
        if post["id"] == post_id:
            post["reports"] = post.get("reports", 0) + 1
            if post["reports"] >= 3:
                post["flagged"] = True

            log_audit_event(
                AuditEventType.FORUM_POST_REPORTED,
                target_id=post_id,
                details={"reports": post["reports"], "flagged": post["flagged"]},
                ip_address=request.remote_addr,
            )

            return jsonify({"status": "reported", "reports": post["reports"]})
    return jsonify({"error": "Post not found"}), 404


@app.route("/api/counselor/queue", methods=["GET"])
@counselor_access_required
def get_counselor_queue():
    queue = sorted(COUNSELOR_QUEUE, key=lambda x: x.get("flagged_at", ""), reverse=True)
    return jsonify({"queue": queue[:20], "total": len(COUNSELOR_QUEUE)})


@app.route("/api/counselor/review/<case_id>", methods=["POST"])
@counselor_access_required
def mark_reviewed(case_id):
    for entry in COUNSELOR_QUEUE:
        if entry.get("id") == case_id:
            entry["reviewed"] = True
            entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            return jsonify({"status": "reviewed", "case_id": case_id})
    return jsonify({"error": "Case not found"}), 404


@app.route("/api/counselor/jitsi/<case_id>", methods=["GET"])
@counselor_access_required
def get_jitsi_room(case_id):
    for entry in COUNSELOR_QUEUE:
        if entry.get("id") == case_id:
            room = entry.get("jitsi_room", f"AegisMind-Case-{case_id}")
            return jsonify({
                "jitsi_url": f"https://meet.jit.si/{room}",
                "room": room,
            })
    room = f"AegisMind-Case-{case_id}"
    return jsonify({"jitsi_url": f"https://meet.jit.si/{room}", "room": room})


@app.route("/api/profile/<token>", methods=["GET"])
def get_profile(token):
    profile = USER_PROFILES.get(token)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    history = CHECK_IN_HISTORY.get(token, [])
    avg_dpi = 0.0
    if history:
        avg_dpi = round(sum(r.get("dpi", 0) for r in history) / len(history), 3)

    return jsonify({
        **profile,
        "checkin_count": len(history),
        "avg_dpi": avg_dpi,
        "last_checkin": history[-1]["timestamp"] if history else None,
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  AegisMind — Mental Health Monitoring System")
    print("  Multi-Agent Pipeline + Consoling Companion: Active")
    print("=" * 60)
    app.run(debug=False, host="0.0.0.0", port=5000)
