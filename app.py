"""
AegisMind — AI-Powered Mental Health Monitoring & Distress Prediction System
Principal Engineer: Full-Stack + Clinical AI Systems

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

# Flask app initialization
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
            "script-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
            "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            "font-src": ["'self'", "https://fonts.gstatic.com"],
            "img-src": ["'self'", "data:"],
            "connect-src": ["'self'", "https://api.groq.com", "https://*.supabase.co", "wss://*.supabase.co"],
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

# --------------------------------------------------------------
# Supabase & Database Integration
# --------------------------------------------------------------
import database as db

# Configure logging before initializing Supabase
def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("aegismind")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger


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


logger = configure_logging()

# Initialize Supabase client & persistent database
supabase_url = os.environ.get("SUPABASE_URL", "")
supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
supabase_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

db.init_database(supabase_url, supabase_service_role_key or supabase_anon_key)
supabase = db.get_supabase()

if supabase:
    logger.info("Supabase client initialized as primary backend")
else:
    logger.warning("Supabase URL or key not configured -- running in local persistent DB mode")


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------
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
            if len(self._requests) > 10_000:
                self._requests.pop(next(iter(self._requests)), None)
            return True, 0


rate_limiter = InMemoryRateLimiter()


def rate_limit(limit):
    """Limit write-heavy public routes by client IP and route."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
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


# ---------------------------------------------------------------------------
# Counselor access decorator
# ---------------------------------------------------------------------------
def counselor_access_required(view):
    """Protect counselor data; allow valid counselor key or authenticated session/token."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        counselor_key = request.headers.get("X-Counselor-Key")
        if counselor_key and counselor_key == Config.COUNSELOR_API_KEY:
            return view(*args, **kwargs)
        if getattr(g, "user_id", None) or session.get("user_id"):
            return view(*args, **kwargs)
        if Config.COUNSELOR_API_KEY:
            return jsonify({"error": "counselor_authorization_required"}), 401
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Supabase JWT verification
# ---------------------------------------------------------------------------
def verify_supabase_jwt():
    """Verify Supabase JWT from the Authorization header and set g.user_id / g.user_role."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    else:
        token = session.get("supabase_token", "")

    if not token:
        g.user_id = session.get("user_id")
        g.user_role = "user" if g.user_id else "anonymous"
        return

    try:
        if "." in token:
            if supabase:
                try:
                    res = supabase.auth.get_user(token)
                    user = res.user if res else None
                    if user:
                        g.user_id = user.id
                        g.user_role = "user"
                        return
                except Exception:
                    pass
            # Fallback decode
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            g.user_id = decoded.get("sub") or decoded.get("user_id") or session.get("user_id")
            g.user_role = "user" if g.user_id else "anonymous"
        else:
            # Token is an anonymous token or user UUID
            g.user_id = token
            g.user_role = "user"
    except Exception as e:
        g.user_id = token or session.get("user_id")
        g.user_role = "user" if g.user_id else "anonymous"


@app.before_request
def begin_request():
    """Attach a correlation id, verify JWT, and reject oversized/non-JSON API writes early."""
    g.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    g.request_started_at = time.perf_counter()
    verify_supabase_jwt()
    if request.method in {"POST", "PUT", "PATCH"} and request.path.startswith("/api/"):
        if request.content_length and not request.is_json:
            return jsonify({"error": "json_body_required"}), 415


def get_user_profile(user_id: str) -> dict:
    """Fetch user profile from Supabase profiles table or persistent DB."""
    return db.get_profile_by_id(user_id) or {}


# ---------------------------------------------------------------------------
# Validation helpers — DEFINED EARLY FOR ROUTE USAGE
# ---------------------------------------------------------------------------
class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


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
# CRISIS PATTERNS & AGENTS
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
    r"\bmarne\s+ki\b",
    r"\bjeena\s+nahi\b",
    r"\bzindagi+khatam\b",
]
_CRISIS_RE = re.compile("|".join(CRISIS_PATTERNS), re.IGNORECASE)

FIRST_PERSON_SINGULAR = {"i", "me", "my", "myself", "mine"}
ABSOLUTIST_WORDS = {
    "always", "never", "completely", "nothing", "everything", "everyone",
    "nobody", "impossible", "utterly", "absolutely", "totally", "forever",
    "no one", "all", "must", "only", "worst", "useless", "worthless",
    "hopeless", "pointless",
}


def guard_agent(text: str, token: str) -> dict:
    profile = db.get_profile_by_id(token) or {}
    has_consent = profile.get("consent", False) or session.get("consent", False) or bool(profile)
    if not has_consent and token == "ANON":
        return {"route": "reject", "reason": "no_consent"}
    if _CRISIS_RE.search(text):
        return {"route": "crisis", "matched_pattern": True}
    return {"route": "standard"}


def nlp_agent(text: str, valence: float, arousal: float, voice_score: float) -> dict:
    words = re.findall(r"\b\w+\b", text.lower())
    total_words = max(len(words), 1)
    fp_count = sum(1 for w in words if w in FIRST_PERSON_SINGULAR)
    fp_density = round(fp_count / total_words, 3)
    abs_count = sum(1 for w in words if w in ABSOLUTIST_WORDS)
    if "no one" in text.lower():
        abs_count += text.lower().count("no one")
    abs_density = round(abs_count / total_words, 3)
    valence_distress = round((10.0 - valence) / 9.0, 3)
    arousal_distress = round(abs(arousal - 5.5) / 4.5, 3)
    voice_distress = round(max(0.0, min(1.0, 1.0 - voice_score)), 3)
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


def trajectory_agent(token: str, current_nlp_score: float) -> dict:
    history = db.get_checkin_history(token, limit=7)
    recent_scores = [r.get("dpi", 0.5) for r in history if isinstance(r.get("dpi"), (int, float))] if history else []
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


def crisis_agent(token: str, text: str, trajectory: dict) -> dict:
    case_id = uuid.uuid4().hex[:8].upper()
    profile = db.get_profile_by_id(token) or {}
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
        "triggers": ["crisis_phrase_detected"],
    }
    db.save_counselor_case(sev1_record)
    if Config.TELE_MANAS_API_URL:
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


def hitl_agent(token: str, trajectory: dict, nlp_result: dict, profile: dict) -> dict:
    case_id = uuid.uuid4().hex[:8].upper()
    jitsi_room = f"AegisMind-Case-{case_id}"
    triggers = []
    if nlp_result.get("fp_density", 0) > 0.15:
        triggers.append("pronoun_density")
    if nlp_result.get("abs_density", 0) > 0.08:
        triggers.append("absolutist_language")
    if nlp_result.get("valence_distress", 0) > 0.60:
        triggers.append("low_valence")
    if nlp_result.get("voice_distress", 0) > 0.60:
        triggers.append("voice_cadence")
    queue_entry = {
        "id": case_id,
        "token": token,
        "alias": profile.get("alias", "Anonymous"),
        "dpi": trajectory["dpi"],
        "delta_dpi": trajectory["delta_dpi"],
        "risk_level": trajectory["risk_level"],
        "triggers": triggers if triggers else ["low_valence"],
        "valence_distress": nlp_result.get("valence_distress", 0.5),
        "nlp_score": nlp_result.get("nlp_score", 0.5),
        "flagged_at": datetime.now(timezone.utc).isoformat(),
        "jitsi_room": jitsi_room,
        "reviewed": False,
        "sev": "SEV-2",
    }
    db.save_counselor_case(queue_entry)
    return {
        "action": "HITL_QUEUED",
        "case_id": case_id,
        "jitsi_room": jitsi_room,
    }


# ---------------------------------------------------------------------------
# CONSOLING COMPANION AI ENGINE
# ---------------------------------------------------------------------------
def generate_companion_reply(user_msg: str, lang: str = "en", history: list = None) -> dict:
    msg_lower = user_msg.lower().strip()
    if _CRISIS_RE.search(user_msg):
        if lang == "hi":
            return {"reply": "मैं समझता हूँ कि आप इस समय बहुत गहरे दर्द में हैं। कृपया याद रखें कि आप अकेले नहीं हैं और आपकी जान बेहद कीमती है। मैं चाहता हूँ कि आप तुरंत 14416 (टेली-मानस) या 1800-599-0019 पर कॉल करें। प्रशिक्षित परामर्शदाता 24/7 आपकी मदद के लिए तैयार हैं।", "is_crisis": True}
        return {"reply": "I hear how much pain you are carrying right now, and I want you to know you are not alone. Your life has immense value. Please reach out to someone who can support you right now — call or text 14416 (Tele-MANAS) or 988. There are caring professionals available 24/7.", "is_crisis": True}
    if Config.GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=Config.GROQ_API_KEY, timeout=Config.GROQ_TIMEOUT_SECONDS)
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
• Conversational Memory: You remember recent messages in this session and maintain continuity.

EVERY RESPONSE must be safe for someone in acute distress.
If unsure, err toward: "I'm here. You're not alone. Help is available 24/7: 14416 (Tele-MANAS), 988, 1800-599-0019 (KIRAN)."
"""
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                for h in history[-6:]:
                    r = "assistant" if h.get("sender") == "companion" else "user"
                    txt = h.get("message", "").strip()
                    if txt:
                        messages.append({"role": r, "content": txt})
            messages.append({"role": "user", "content": user_msg})

            response = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=messages,
                temperature=0.7,
                max_tokens=200,
            )
            reply_text = response.choices[0].message.content.strip()
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
    if Config.OPENAI_API_KEY:
        try:
            pass
        except Exception:
            pass
    if lang == "hi":
        if any(w in msg_lower for w in ["तनाव", "घबराहट", "चिंता", "डर", "डर लग रहा", "anxious", "panic"]):
            replies = ["चिंता महसूस होना स्वाभाविक है। आइए एक पल के लिए रुकें। अपनी पीठ सीधी करें, एक लंबी गहरी सांस लें और 4 सेकंड तक रोकें। आप सुरक्षित हैं।", "जब मन अशांत हो, तो वर्तमान में लौटना सबसे अच्छा होता है। अपने आसपास देखें और 3 ऐसी चीजें ढूंढें जिनका रंग हरा या नीला हो."]
        elif any(w in msg_lower for w in ["अकेला", "अकेलापन", "lonely", "alone"]):
            replies = ["अकेलापन बहुत भारी लग सकता है। मैं यहाँ आपके साथ हूँ और आपकी बात सुन रहा हूँ। आप जो महसूस कर रहे हैं, वह साझा करने के लिए धन्यवाद।", "याद रखें कि अकेलापन एक भावना है, आपकी पूरी सच्चाई नहीं। आप महत्वपूर्ण हैं और आपकी भावनाएं मायने रखती हैं."]
        elif any(w in msg_lower for w in ["थकान", "थक गया", "मन नहीं", "उदास", "sad", "tired"]):
            replies = ["आज का दिन कठिन रहा लगता है। कभी-कभी सिर्फ आराम करना और खुद पर कोई दबाव न डालना ही सबसे अच्छी देखभाल है।", "खुद के प्रति थोड़ा दयालु बनें। आपको सब कुछ आज ही ठीक करने की ज़रूरत नहीं है। एक घूंट पानी पिएं और गहरी सांस लें."]
        else:
            replies = ["मैं आपकी बात ध्यान से सुन रहा हूँ। जो कुछ भी आपके मन पर बोझ बना हुआ है, उसे यहाँ स्वतंत्र रूप से कह सकते हैं।", "अपने विचारों को व्यक्त करने के लिए धन्यवाद। आप बहुत हिम्मत के साथ आगे बढ़ रहे हैं। मैं हर कदम पर आपके साथ हूँ."]
    else:
        if any(w in msg_lower for w in ["anxious", "anxiety", "panic", "overwhelmed", "stressed", "scared", "nervous"]):
            replies = ["It is completely okay to feel overwhelmed. Let's take a pause together. Relax your shoulders, unclamp your jaw, and take one slow, deep breath in... and out.", "Anxiety makes everything feel urgent, but right now, you are safe in this moment. Try feeling your feet firmly on the ground. I'm right here with you."]
        elif any(w in msg_lower for w in ["lonely", "alone", "nobody", "isolated"]):
            replies = ["Feeling lonely is such a heavy weight to carry. Thank you for reaching out and sharing this space with me. You matter, and I am here listening to you.", "Loneliness can make us forget our connection to the world, but your presence is meaningful. Take it gently today."]
        elif any(w in msg_lower for w in ["sad", "depressed", "down", "crying", "tired", "exhausted", "hopeless"]):
            replies = ["I hear you, and it's okay to not be okay today. You don't have to carry the whole world on your shoulders right now. Give yourself permission to just rest.", "You have been carrying a lot lately. Be gentle with yourself today. Even the smallest step — like drinking a glass of water — is a win."]
        elif any(w in msg_lower for w in ["thank", "thanks", "helpful", "good", "better"]):
            replies = ["I am so glad to hear that. You are doing wonderful work checking in with yourself today.", "You're very welcome. Remember, your resilience comes from within you. I'm always here whenever you need a calm ear."]
        else:
            replies = ["Thank you for sharing that with me. What you're feeling is valid, and I'm here to support you through it. Would you like to tell me more, or try a quick calming exercise?", "I'm listening without any judgment. Take all the time you need. How is your body feeling right now as you write this?"]
    return {"reply": random.choice(replies), "is_crisis": False}


def generate_alias() -> str:
    adjectives = ["Quiet", "Gentle", "Steady", "Calm", "Warm", "Clear", "Soft", "Bright", "Still", "Kind", "Serene", "Hopeful"]
    nouns = ["Willow", "River", "Stone", "Ember", "Harbor", "Dawn", "Meadow", "Lantern", "Compass", "Anchor", "Candle", "Shore"]
    return f"{random.choice(adjectives)}{random.choice(nouns)}{random.randint(10, 99)}"


# ---------------------------------------------------------------------------
# Flask Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template(
        "index.html",
        api_base_url=Config.API_BASE_URL,
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
    )


@app.route("/health")
def health():
    components = {"application": "ok"}
    status = "ok"
    if supabase:
        components["storage"] = "supabase_postgresql"
    elif Config.DATABASE_URL:
        components["storage"] = "configured"
    else:
        components["storage"] = "persistent_sqlite"
    if Config.GROQ_API_KEY:
        components["llm"] = "configured"
    else:
        components["llm"] = "rule_based_only"
    return jsonify({"status": status, "components": components}), 200


@app.route("/login")
def login():
    if session.get("google_user") or session.get("user_id"):
        return redirect(url_for("index"))
    return render_template(
        "login.html",
        api_base_url=Config.API_BASE_URL,
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
        google_client_id=GOOGLE_CLIENT_ID,
    )


@app.route("/auth/callback")
def auth_callback():
    return render_template(
        "auth_callback.html",
        api_base_url=Config.API_BASE_URL,
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
    )


@app.route("/api/auth/session", methods=["POST"])
def sync_auth_session():
    data = json_payload()
    token = str(data.get("access_token", "")).strip()
    user_id = str(data.get("user_id", "")).strip()
    email = str(data.get("email", "")).strip()
    alias = str(data.get("alias", "")).strip()
    if user_id:
        session["supabase_token"] = token
        session["user_id"] = user_id
        session["user_email"] = email
        session["user_alias"] = alias
        profile = db.upsert_profile(user_id=user_id, email=email, alias=alias, consent=True)
        log_audit_event(AuditEventType.AUTH_LOGIN, details={"user_id": user_id, "provider": "supabase"}, ip_address=request.remote_addr)
        return jsonify({"status": "ok", "profile": profile})
    return jsonify({"error": "user_id_required"}), 400


@app.route("/auth/google")
def google_login():
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
    if google is None:
        return redirect(url_for("index"))
    token = google.authorize_access_token()
    user = token.get("userinfo", {})
    if not user.get("sub") or not user.get("email"):
        return jsonify({"error": "google_identity_unavailable"}), 400
    session["google_user"] = {
        "google_sub": user["sub"],
        "email": user["email"],
        "name": user.get("name", ""),
        "picture": user.get("picture", ""),
    }
    user_id = f"google_{user['sub']}"
    session["user_id"] = user_id
    session["user_alias"] = user.get("name") or user["email"].split("@")[0]
    db.upsert_profile(user_id=user_id, email=user["email"], alias=session["user_alias"], consent=True)
    log_audit_event(
        AuditEventType.AUTH_LOGIN,
        details={"provider": "google", "email_domain": user["email"].split("@")[-1]},
        ip_address=request.remote_addr,
    )
    return redirect(url_for("index"))


@app.route("/auth/logout", methods=["GET", "POST"])
def logout():
    log_audit_event(AuditEventType.AUTH_LOGOUT, ip_address=request.remote_addr)
    session.pop("google_user", None)
    session.pop("supabase_token", None)
    session.pop("user_id", None)
    session.pop("user_email", None)
    session.pop("user_alias", None)
    if request.headers.get("Accept", "").startswith("application/json") or request.method == "POST":
        return jsonify({"status": "logged_out"})
    return redirect(url_for("login"))


@app.route("/api/register", methods=["POST"])
@rate_limit(Config.FORUM_RATE_LIMIT)
def register():
    data = json_payload()
    consent = data.get("consent", False)
    if not consent:
        return jsonify({"error": "Consent required"}), 400
    alias = str(data.get("alias", "")).strip() or generate_alias()
    email = str(data.get("email", "")).strip().lower() or None
    password = str(data.get("password", "")).strip()

    if email and supabase and password:
        try:
            # Use admin create_user if service role key is configured to auto-confirm email
            user = None
            access_token = None
            try:
                admin_res = supabase.auth.admin.create_user({
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"alias": alias, "consent": True},
                })
                user = admin_res.user if admin_res else None
            except Exception as admin_err:
                # Fallback to standard sign_up
                res = supabase.auth.sign_up({
                    "email": email,
                    "password": password,
                    "options": {"data": {"alias": alias, "consent": True}},
                })
                user = res.user if res else None

            # Attempt password sign-in to obtain live JWT access_token
            try:
                sign_in_res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if sign_in_res and sign_in_res.session:
                    access_token = sign_in_res.session.access_token
                    if sign_in_res.user:
                        user = sign_in_res.user
            except Exception:
                pass

            if user:
                profile = db.upsert_profile(user_id=user.id, email=email, alias=alias, consent=True)
                session["supabase_token"] = access_token
                session["user_id"] = user.id
                session["user_alias"] = alias
                log_audit_event(AuditEventType.AUTH_LOGIN, details={"user_id": user.id, "email": email}, ip_address=request.remote_addr)
                return jsonify({
                    "status": "ok",
                    "user_id": user.id,
                    "email": user.email,
                    "alias": alias,
                    "token": user.id,
                    "access_token": access_token,
                    "message": "Registered successfully with Supabase",
                    "supabase_auth": True,
                })
        except Exception as e:
            logger.error(f"Supabase registration error: {e}")
            return jsonify({"error": "registration_failed", "message": str(e)}), 400

    token = uuid.uuid4().hex[:16].upper()
    profile = db.upsert_profile(user_id=token, email=email or f"{alias.lower()}@aegismind.local", alias=alias, consent=True)
    log_audit_event(AuditEventType.SESSION_CREATED, actor_token=token, details={"alias": alias}, ip_address=request.remote_addr)
    return jsonify({
        "status": "ok",
        "token": token,
        "alias": alias,
        "message": "Registered successfully",
    })


@app.route("/api/login", methods=["POST"])
@rate_limit(Config.FORUM_RATE_LIMIT)
def api_login():
    data = json_payload()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()
    token = str(data.get("token", "")).strip().upper()
    alias = str(data.get("alias", "")).strip()

    # Case 1: Email + Password via Supabase Auth
    if email and password and supabase:
        try:
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            except Exception as sign_in_err:
                if "Email not confirmed" in str(sign_in_err):
                    # Auto-confirm with admin key
                    try:
                        users_list = supabase.auth.admin.list_users()
                        matched_user = next((u for u in users_list if getattr(u, "email", "") == email), None)
                        if matched_user:
                            supabase.auth.admin.update_user_by_id(matched_user.id, {"email_confirm": True})
                            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        else:
                            raise sign_in_err
                    except Exception:
                        raise sign_in_err
                else:
                    raise sign_in_err
            user = res.user if res else None
            if user and res.session:
                user_alias = user.user_metadata.get("alias") or email.split("@")[0]
                session["supabase_token"] = res.session.access_token
                session["user_id"] = user.id
                session["user_alias"] = user_alias
                db.upsert_profile(user_id=user.id, email=email, alias=user_alias, consent=True)
                history = db.get_checkin_history(user.id)
                log_audit_event(AuditEventType.AUTH_LOGIN, details={"user_id": user.id, "email": email}, ip_address=request.remote_addr)
                return jsonify({
                    "status": "ok",
                    "user_id": user.id,
                    "token": user.id,
                    "access_token": res.session.access_token,
                    "alias": user_alias,
                    "checkin_count": len(history),
                    "message": "Signed in successfully with Supabase",
                    "supabase_auth": True,
                })
        except Exception as e:
            return jsonify({"error": "auth_failed", "message": str(e)}), 401

    # Case 2: Active JWT session
    effective_id = g.user_id or session.get("user_id")
    if effective_id and not token and not alias:
        profile = db.get_profile_by_id(effective_id)
        if profile:
            history = db.get_checkin_history(effective_id)
            return jsonify({
                "status": "ok",
                "user_id": effective_id,
                "token": effective_id,
                "alias": profile.get("alias", "Anonymous"),
                "checkin_count": len(history),
                "message": "Session restored successfully via Supabase",
                "supabase_auth": True,
            })

    # Case 3: Token or Alias login
    search_key = token or alias
    if not search_key:
        return jsonify({"error": "token_or_alias_required", "message": "Please provide your session token or alias to sign in."}), 400

    profile = db.get_profile_by_id(search_key)
    if profile:
        history = db.get_checkin_history(profile.get("user_id") or search_key)
        session["user_id"] = profile.get("user_id") or search_key
        session["user_alias"] = profile.get("alias")
        log_audit_event(AuditEventType.AUTH_LOGIN, actor_token=search_key, details={"method": "token_restore", "alias": profile.get("alias")}, ip_address=request.remote_addr)
        return jsonify({
            "status": "ok",
            "token": profile.get("user_id") or search_key,
            "alias": profile.get("alias", "Anonymous"),
            "checkin_count": len(history),
            "message": "Session restored successfully",
        })

    # If 8+ chars token not found, register it
    if token and len(token) >= 8:
        new_alias = alias or generate_alias()
        profile = db.upsert_profile(user_id=token, alias=new_alias, consent=True)
        session["user_id"] = token
        session["user_alias"] = new_alias
        return jsonify({
            "status": "ok",
            "token": token,
            "alias": new_alias,
            "checkin_count": 0,
            "message": "New session created with token",
        })

    return jsonify({"error": "not_found", "message": "No account or session found with that identifier."}), 404


@app.route("/api/checkin", methods=["POST"])
@rate_limit(Config.CHECKIN_RATE_LIMIT)
def checkin():
    data = json_payload()
    user_id = getattr(g, "user_id", None) or session.get("user_id")
    token = str(data.get("token", "")).strip().upper() if data else ""
    text = str(data.get("text", "")).strip() if data else ""
    if not text:
        return jsonify({"error": "text_required", "message": "Journal text is required"}), 400
    if len(text) > 800:
        return jsonify({"error": "text_too_long", "message": "Check-in text must be 800 characters or fewer."}), 400
    try:
        valence = validated_score(data, "valence")
        arousal = validated_score(data, "arousal")
        voice_score = validated_voice_score(data)
    except ValueError as error:
        return jsonify({"error": "invalid_checkin", "message": str(error)}), 400

    effective_token = user_id or token or "ANON"
    guard_result = guard_agent(text, effective_token)
    if guard_result["route"] == "reject":
        return jsonify({"error": "Consent required before submitting check-ins"}), 403

    profile = db.get_profile_by_id(effective_token) or {}
    alias = profile.get("alias", "Anonymous")

    if guard_result["route"] == "crisis":
        timestamp = datetime.now(timezone.utc).isoformat()
        prev_history = db.get_checkin_history(effective_token, limit=7)
        trajectory = {
            "dpi": 1.0,
            "delta_dpi": 0.0,
            "slope": 0.0,
            "risk_level": "critical",
            "sparkline": [None] * 6 + [1.0],
            "history_count": len(prev_history),
        }
        db.save_checkin(
            user_id_or_token=effective_token,
            text=text,
            valence=valence,
            arousal=arousal,
            voice_score=voice_score,
            nlp_data={},
            dpi=1.0,
            delta_dpi=0.0,
            risk_level="critical"
        )
        agent_action = crisis_agent(effective_token, text, trajectory)
        agent_action["agent"] = "crisis_agent"
        log_audit_event(AuditEventType.CRISIS_ESCALATED, actor_token=effective_token, target_id=agent_action.get("case_id"), details={"source": "guard_agent", "risk_level": "critical"}, ip_address=request.remote_addr)
        resp_token = token or effective_token
        return jsonify({
            "status": "crisis",
            "token": resp_token,
            "alias": alias,
            "nlp": None,
            "trajectory": trajectory,
            "agent_action": agent_action,
            "timestamp": timestamp,
        })

    nlp_result = nlp_agent(text, valence, arousal, voice_score)
    trajectory = trajectory_agent(effective_token, nlp_result["nlp_score"])

    record = db.save_checkin(
        user_id_or_token=effective_token,
        text=text,
        valence=valence,
        arousal=arousal,
        voice_score=voice_score,
        nlp_data=nlp_result,
        dpi=trajectory["dpi"],
        delta_dpi=trajectory["delta_dpi"],
        risk_level=trajectory["risk_level"]
    )

    agent_action = None
    if guard_result["route"] == "crisis" or trajectory["risk_level"] == "critical":
        agent_action = crisis_agent(effective_token, text, trajectory)
        agent_action["agent"] = "crisis_agent"
        log_audit_event(AuditEventType.CRISIS_ESCALATED, actor_token=effective_token, target_id=agent_action.get("case_id"), details={"source": "trajectory_agent", "risk_level": trajectory["risk_level"]}, ip_address=request.remote_addr)
    elif trajectory["risk_level"] == "moderate":
        agent_action = hitl_agent(effective_token, trajectory, nlp_result, profile)
        agent_action["agent"] = "hitl_agent"
        log_audit_event(AuditEventType.CASE_REVIEWED, actor_token=effective_token, target_id=agent_action.get("case_id"), details={"risk_level": "moderate", "triggers": agent_action.get("triggers", [])}, ip_address=request.remote_addr)

    log_audit_event(AuditEventType.CHECKIN_SUBMITTED, actor_token=effective_token, details={"risk_level": trajectory["risk_level"], "dpi": trajectory["dpi"]}, ip_address=request.remote_addr)

    return jsonify({
        "status": "ok",
        "token": effective_token,
        "alias": alias,
        "nlp": nlp_result,
        "trajectory": trajectory,
        "agent_action": agent_action,
        "timestamp": record["created_at"],
    })


@app.route("/api/chat", methods=["POST"])
@rate_limit(Config.CHAT_RATE_LIMIT)
def chat():
    data = json_payload()
    token = str(data.get("token", "")).strip() or getattr(g, "user_id", None) or session.get("user_id") or "ANON"
    message = str(data.get("message", "")).strip()
    lang = str(data.get("lang", "en")).lower()
    if not message:
        return jsonify({"error": "Message required"}), 400
    if len(message) > 1200:
        return jsonify({"error": "message_too_long", "message": "Message must be 1200 characters or fewer."}), 400
    if lang not in {"en", "hi"}:
        return jsonify({"error": "invalid_language"}), 400

    # Retrieve prior conversation memory for real contextual awareness
    history = db.get_chat_history(token, limit=6)
    response_data = generate_companion_reply(message, lang, history=history)

    # Persist both user and companion conversation turns
    db.save_chat_message(token, "user", message)
    db.save_chat_message(token, "companion", response_data["reply"])

    return jsonify({
        "reply": response_data["reply"],
        "is_crisis": response_data.get("is_crisis", False),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/history/<token>", methods=["GET"])
def get_history(token):
    records = db.get_checkin_history(token, limit=30)
    return jsonify({"token": token, "count": len(records), "records": records})


@app.route("/api/forum", methods=["GET"])
def get_forum():
    posts = db.get_forum_posts(limit=50)
    return jsonify({"posts": posts})


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
        return jsonify({"error": "crisis_detected", "message": "We noticed you may be in distress. Please use the 'I Need Help Now' button."}), 422
    alias = generate_alias()
    post_id = str(uuid.uuid4())
    user_id = getattr(g, "user_id", None) or session.get("user_id") or "ANON"
    post = db.save_forum_post(post_id, user_id, alias, text, lang)
    log_audit_event(AuditEventType.FORUM_POST_CREATED, details={"post_id": post["id"], "lang": lang}, ip_address=request.remote_addr)
    return jsonify(post), 201


@app.route("/api/forum/<post_id>/react", methods=["POST"])
@rate_limit(Config.FORUM_RATE_LIMIT)
def react_to_post(post_id):
    data = json_payload()
    reaction = data.get("reaction", "heart")
    if reaction not in ("heart", "hug", "star"):
        return jsonify({"error": "Invalid reaction"}), 400
    reactions = db.react_to_forum_post(post_id, reaction)
    if reactions is not None:
        return jsonify({"reactions": reactions})
    return jsonify({"error": "Post not found"}), 404


@app.route("/api/forum/<post_id>/report", methods=["POST"])
@rate_limit(Config.FORUM_RATE_LIMIT)
def report_post(post_id):
    result = db.report_forum_post(post_id)
    if result:
        log_audit_event(AuditEventType.FORUM_POST_REPORTED, target_id=post_id, details=result, ip_address=request.remote_addr)
        return jsonify(result)
    return jsonify({"error": "Post not found"}), 404


@app.route("/api/counselor/queue", methods=["GET"])
@counselor_access_required
def get_counselor_queue():
    queue = db.get_counselor_queue()
    return jsonify({"queue": queue[:20], "total": len(queue)})


@app.route("/api/counselor/review/<case_id>", methods=["POST"])
@counselor_access_required
def mark_reviewed(case_id):
    success = db.mark_counselor_case_reviewed(case_id)
    if success:
        return jsonify({"status": "reviewed", "case_id": case_id})
    return jsonify({"error": "Case not found"}), 404


@app.route("/api/counselor/jitsi/<case_id>", methods=["GET"])
@counselor_access_required
def get_jitsi_room(case_id):
    room = f"AegisMind-Case-{case_id}"
    return jsonify({"jitsi_url": f"https://meet.jit.si/{room}", "room": room})


@app.route("/api/profile/<token>", methods=["GET"])
def get_profile(token):
    profile = db.get_profile_by_id(token)
    if not profile:
        profile = {"user_id": token, "alias": "Anonymous", "consent": True}
    history = db.get_checkin_history(profile.get("user_id") or token, limit=30)
    avg_dpi = round(sum(r.get("dpi", 0.0) for r in history) / len(history), 3) if history else 0.0
    return jsonify({
        **profile,
        "checkin_count": len(history),
        "avg_dpi": avg_dpi,
        "last_checkin": history[-1].get("created_at") or history[-1].get("timestamp") if history else None,
    })


@app.route("/api/dashboard/stats", methods=["GET"])
def dashboard_stats():
    """Return live stats for the authenticated user's dashboard."""
    user_id = getattr(g, "user_id", None) or session.get("user_id")
    token_param = request.args.get("token", "")
    effective_id = user_id or token_param
    if not effective_id:
        return jsonify({"checkin_count": 0, "avg_dpi": None, "streak": 0, "risk_level": "low", "sparkline": [], "last_risk": "low"})

    history = db.get_checkin_history(effective_id, limit=30)
    if not history:
        return jsonify({"checkin_count": 0, "avg_dpi": None, "streak": 0, "risk_level": "low", "sparkline": [], "last_risk": "low"})

    count = len(history)
    avg_dpi = round(sum(r.get("dpi", 0.0) for r in history) / count, 3) if count else 0.0
    last_risk = history[-1].get("risk_level", "low") if history else "low"

    # Calculate streak: consecutive days with at least one check-in ending today
    from collections import OrderedDict
    days_seen = set()
    today = datetime.now(timezone.utc).date()
    for r in history:
        ts = r.get("created_at") or r.get("timestamp")
        if ts:
            try:
                d = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
                days_seen.add(d)
            except Exception:
                pass
    streak = 0
    check_day = today
    while check_day in days_seen:
        streak += 1
        check_day = check_day - timedelta(days=1)

    # 7-day sparkline
    sparkline_map = {}
    for r in history:
        ts = r.get("created_at") or r.get("timestamp")
        dpi = r.get("dpi")
        if ts and dpi is not None:
            try:
                d = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
                sparkline_map[d] = round(float(dpi), 3)
            except Exception:
                pass
    sparkline = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        sparkline.append(sparkline_map.get(d))  # None for days with no data

    return jsonify({
        "checkin_count": count,
        "avg_dpi": avg_dpi,
        "streak": streak,
        "risk_level": last_risk,
        "last_risk": last_risk,
        "sparkline": sparkline,
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  AegisMind — Mental Health Monitoring System")
    print("  Multi-Agent Pipeline + Consoling Companion: Active")
    print("=" * 60)
    app.run(debug=False, host="0.0.0.0", port=5000)