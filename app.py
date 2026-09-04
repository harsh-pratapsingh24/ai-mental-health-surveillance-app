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
from datetime import datetime, timedelta, timezone
from collections import deque
from functools import wraps
from flask import Flask, request, jsonify, render_template, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "aegismind-secret-2024-clinical-ai")

# ===========================================================================
# EXTERNAL API INTEGRATION SLOTS (Fill these with your production keys / env vars)
# ===========================================================================
OPENAI_API_KEY      = os.environ.get("OPENAI_API_KEY", "")        # e.g. "sk-proj-..."
ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")     # e.g. "sk-ant-..."
GEMINI_API_KEY      = os.environ.get("GEMINI_API_KEY", "")        # e.g. "AIzaSy..."
TELE_MANAS_API_URL  = os.environ.get("TELE_MANAS_API_URL", "")    # e.g. "https://telemanas.mohfw.gov.in/api/v1/escalation"
TWILIO_ACCOUNT_SID  = os.environ.get("TWILIO_ACCOUNT_SID", "")    # e.g. "AC..."
TWILIO_AUTH_TOKEN   = os.environ.get("TWILIO_AUTH_TOKEN", "")     # e.g. "..."
DATABASE_URL        = os.environ.get("DATABASE_URL", "")          # e.g. "postgresql://user:pass@localhost:5432/aegismind"

# ---------------------------------------------------------------------------
# In-Memory Data Stores (with clean schema for PostgreSQL/SQLite migration)
# ---------------------------------------------------------------------------
USER_PROFILES = {}          # token → profile dict
CHECK_IN_HISTORY = {}       # token → list of check-in records
FORUM_POSTS = []            # global anonymous forum
COUNSELOR_QUEUE = []        # flagged cases for HITL review
SEV1_CASES = []             # critical SEV-1 lockouts
CHAT_SESSIONS = {}          # token → list of chat messages

# Pre-seed forum with sample posts for demo
SEED_ALIASES = ["QuietWillow", "GentleRiver", "SteadyStone", "WarmEmber",
                "CalmHarbor", "SoftMeadow", "SereneDawn", "ClearLantern"]

def _seed_forum():
    sample_posts = [
        {"alias": "QuietWillow",  "text": "Today was heavy, but I reminded myself to take one breath at a time. Sending peaceful thoughts to anyone struggling.", "lang": "en", "reactions": {"heart": 14, "hug": 9,  "star": 4}},
        {"alias": "GentleRiver",  "text": "मैंने आज 10 मिनट के लिए फोन बंद करके सिर्फ गहरी सांस ली। मन काफी शांत लगा।",                                    "lang": "hi", "reactions": {"heart": 8,  "hug": 15, "star": 6}},
        {"alias": "SteadyStone",  "text": "The 5-4-3-2-1 grounding exercise helped pull me out of a spiraling thought loop this morning.",                     "lang": "en", "reactions": {"heart": 21, "hug": 7,  "star": 11}},
        {"alias": "WarmEmber",    "text": "It's okay not to have everything figured out right now. Just being here and trying is enough.",                       "lang": "en", "reactions": {"heart": 26, "hug": 12, "star": 8}},
        {"alias": "CalmHarbor",   "text": "आप अकेले नहीं हैं। कठिन समय भी धीरे-धीरे बीत जाता है।",                                                              "lang": "hi", "reactions": {"heart": 10, "hug": 18, "star": 5}},
    ]
    for p in sample_posts:
        FORUM_POSTS.append({
            "id": str(uuid.uuid4()),
            "alias": p["alias"],
            "text": p["text"],
            "lang": p["lang"],
            "reactions": p["reactions"],
            "flagged": False,
            "reports": 0,
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48))).isoformat(),
        })

_seed_forum()

# Pre-seed counselor queue for demo
def _seed_counselor_queue():
    for _ in range(3):
        token = f"DEMO-{uuid.uuid4().hex[:8].upper()}"
        USER_PROFILES[token] = {
            "token": token,
            "alias": random.choice(SEED_ALIASES),
            "consent": True,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(3, 14))).isoformat(),
        }
        dpi_val = round(random.uniform(0.52, 0.88), 2)
        delta_dpi = round(random.uniform(0.06, 0.22), 2)
        risk_level = "critical" if dpi_val > 0.75 else "moderate"
        triggers = random.sample(["pronoun_density", "absolutist_language", "low_valence", "voice_cadence"], k=2)
        COUNSELOR_QUEUE.append({
            "id": str(uuid.uuid4()),
            "token": token,
            "alias": USER_PROFILES[token]["alias"],
            "dpi": dpi_val,
            "delta_dpi": delta_dpi,
            "risk_level": risk_level,
            "triggers": triggers,
            "valence": round(random.uniform(1.0, 2.5), 1),
            "arousal": round(random.uniform(1.0, 2.5), 1),
            "flagged_at": (datetime.now(timezone.utc) - timedelta(minutes=random.randint(5, 120))).isoformat(),
            "jitsi_room": f"AegisMind-Case-{uuid.uuid4().hex[:6].upper()}",
            "reviewed": False,
        })

_seed_counselor_queue()

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

    # Inversion scores
    valence_distress = round((5.0 - valence) / 4.0, 3)
    arousal_distress = round(abs(arousal - 3.0) / 2.0, 3)
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
    recent_scores = [r["nlp_score"] for r in history[-7:]] if history else []
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

    # 2. External LLM API Hook (If OPENAI_API_KEY, ANTHROPIC_API_KEY or GEMINI_API_KEY configured)
    if OPENAI_API_KEY:
        try:
            # Placeholder for OpenAI / Claude / Gemini API call
            # response = openai.ChatCompletion.create(
            #     model="gpt-4o-mini",
            #     messages=[
            #         {"role": "system", "content": "You are Aegis Companion, a warm, comforting mental health supportive chatbot. Validate feelings, offer gentle grounding, never diagnose."},
            #         {"role": "user", "content": user_msg}
            #     ]
            # )
            # return {"reply": response.choices[0].message.content, "is_crisis": False}
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
    return render_template("index.html")


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
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

    return jsonify({
        "token": token,
        "alias": alias,
        "message": "Registered successfully",
    })


@app.route("/api/checkin", methods=["POST"])
def checkin():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")
    text = data.get("text", "").strip()
    valence = float(data.get("valence", 3.0))
    arousal = float(data.get("arousal", 3.0))
    voice_score = float(data.get("voice_score", 0.7))

    if token not in USER_PROFILES:
        USER_PROFILES[token] = {
            "token": token,
            "alias": generate_alias(),
            "consent": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        CHECK_IN_HISTORY[token] = []

    guard_result = guard_agent(text, token)
    if guard_result["route"] == "reject":
        return jsonify({"error": "Consent required before submitting check-ins"}), 403

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
    elif trajectory["risk_level"] == "moderate":
        agent_action = hitl_agent(token, trajectory, nlp_result, profile)
        agent_action["agent"] = "hitl_agent"

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
def chat():
    """Consoling AI Companion Endpoint."""
    data = request.get_json(silent=True) or {}
    token = data.get("token", "ANON")
    message = data.get("message", "").strip()
    lang = data.get("lang", "en")

    if not message:
        return jsonify({"error": "Message required"}), 400

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
def create_forum_post():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    lang = data.get("lang", "en")

    if not text or len(text) > 800:
        return jsonify({"error": "Text must be 1–800 characters"}), 400

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
    return jsonify(post), 201


@app.route("/api/forum/<post_id>/react", methods=["POST"])
def react_to_post(post_id):
    data = request.get_json(silent=True) or {}
    reaction = data.get("reaction", "heart")
    if reaction not in ("heart", "hug", "star"):
        return jsonify({"error": "Invalid reaction"}), 400

    for post in FORUM_POSTS:
        if post["id"] == post_id:
            post["reactions"][reaction] = post["reactions"].get(reaction, 0) + 1
            return jsonify({"reactions": post["reactions"]})

    return jsonify({"error": "Post not found"}), 404


@app.route("/api/forum/<post_id>/report", methods=["POST"])
def report_post(post_id):
    for post in FORUM_POSTS:
        if post["id"] == post_id:
            post["reports"] = post.get("reports", 0) + 1
            if post["reports"] >= 3:
                post["flagged"] = True
            return jsonify({"status": "reported", "reports": post["reports"]})
    return jsonify({"error": "Post not found"}), 404


@app.route("/api/counselor/queue", methods=["GET"])
def get_counselor_queue():
    queue = sorted(COUNSELOR_QUEUE, key=lambda x: x.get("flagged_at", ""), reverse=True)
    return jsonify({"queue": queue[:20], "total": len(COUNSELOR_QUEUE)})


@app.route("/api/counselor/review/<case_id>", methods=["POST"])
def mark_reviewed(case_id):
    for entry in COUNSELOR_QUEUE:
        if entry.get("id") == case_id:
            entry["reviewed"] = True
            entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            return jsonify({"status": "reviewed", "case_id": case_id})
    return jsonify({"error": "Case not found"}), 404


@app.route("/api/counselor/jitsi/<case_id>", methods=["GET"])
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
