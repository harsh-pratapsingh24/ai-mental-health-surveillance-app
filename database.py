"""
AegisMind Database & Persistence Layer
Primary Backend: Supabase PostgreSQL (via Supabase Python Client & PostgREST)
Persistent Fallback: Disk-backed SQLite (data/aegismind_persistent.db) to guarantee 
persistence across server restarts even before cloud DDL migrations are executed.
"""

import hashlib
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aegismind.database")

# Ensure local data directory exists
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
SQLITE_PATH = os.path.join(DB_DIR, "aegismind_persistent.db")

# Global Supabase client
_supabase_client = None
_supabase_available_tables = set()


def get_sqlite_conn():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_tables():
    """Create local persistent tables matching Supabase PostgreSQL schema."""
    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT UNIQUE,
                email TEXT,
                full_name TEXT,
                alias TEXT,
                theme_preference TEXT DEFAULT 'dark',
                language_preference TEXT DEFAULT 'en',
                consent INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS check_ins (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                token TEXT,
                text TEXT NOT NULL,
                valence REAL NOT NULL,
                arousal REAL NOT NULL,
                voice_score REAL DEFAULT 0.7,
                nlp_json TEXT,
                dpi REAL,
                delta_dpi REAL,
                risk_level TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                token TEXT,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forum_posts (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                alias TEXT,
                text TEXT NOT NULL,
                lang TEXT DEFAULT 'en',
                reactions TEXT DEFAULT '{"heart": 0, "hug": 0, "star": 0}',
                flagged INTEGER DEFAULT 0,
                reports INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS counselor_cases (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                alias TEXT,
                dpi REAL NOT NULL,
                delta_dpi REAL NOT NULL,
                risk_level TEXT NOT NULL,
                triggers TEXT DEFAULT '[]',
                text_fragment TEXT,
                jitsi_room TEXT,
                reviewed INTEGER DEFAULT 0,
                reviewed_at TEXT,
                sev TEXT DEFAULT 'SEV-2',
                flagged_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                user_id TEXT,
                target_id TEXT,
                details TEXT DEFAULT '{}',
                ip_address TEXT,
                created_at TEXT
            )
        """)
        # Psychiatrist dashboard fields on cases created before this feature existed
        _add_missing_columns(cursor, "counselor_cases", {
            "source": "TEXT DEFAULT 'checkin'",
            "status": "TEXT DEFAULT 'new'",
            "notes": "TEXT DEFAULT ''",
            "acknowledged_at": "TEXT",
        })
        conn.commit()


def _add_missing_columns(cursor, table: str, columns: Dict[str, str]):
    """Add columns to an existing SQLite table when an older database file lacks them."""
    existing_columns = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()}
    for column_name, column_definition in columns.items():
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_definition}")


def init_database(supabase_url: str, supabase_key: str):
    """Initialize Supabase client and check table availability."""
    global _supabase_client, _supabase_available_tables
    init_sqlite_tables()

    if not supabase_url or not supabase_key:
        logger.warning("Supabase credentials missing. Running in local persistent storage mode.")
        return

    try:
        from supabase import create_client
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        _supabase_client = None


def get_supabase():
    return _supabase_client


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

def upsert_profile(user_id: str, email: str = "", alias: str = "", full_name: str = "", consent: bool = True) -> Dict[str, Any]:
    """Upsert profile into Supabase profiles table, also syncing to persistent store."""
    now_iso = datetime.now(timezone.utc).isoformat()
    profile_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "email": email or f"{alias.lower()}@aegismind.local",
        "alias": alias or "Member",
        "full_name": full_name or alias,
        "theme_preference": "dark",
        "language_preference": "en",
        "consent": bool(consent),
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    # Primary: Supabase
    if _supabase_client:
        try:
            res = _supabase_client.from_("profiles").upsert(
                {
                    "user_id": user_id,
                    "email": profile_data["email"],
                    "alias": profile_data["alias"],
                    "consent": profile_data["consent"],
                    "updated_at": now_iso,
                },
                on_conflict="user_id"
            ).execute()
            if res.data:
                profile_data.update(res.data[0])
        except Exception as e:
            logger.warning(f"Supabase upsert_profile notice: {e}")

    # Persistent local storage
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO profiles (id, user_id, email, full_name, alias, consent, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    email = excluded.email,
                    alias = excluded.alias,
                    consent = excluded.consent,
                    updated_at = excluded.updated_at
            """, (
                profile_data["id"],
                profile_data["user_id"],
                profile_data["email"],
                profile_data["full_name"],
                profile_data["alias"],
                1 if profile_data["consent"] else 0,
                profile_data["created_at"],
                profile_data["updated_at"]
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"SQLite upsert_profile error: {e}")

    return profile_data


def get_profile_by_id(user_id_or_token: str) -> Optional[Dict[str, Any]]:
    """Retrieve profile by user_id, token, or alias from Supabase or local persistent DB."""
    if not user_id_or_token:
        return None

    # Primary: Supabase
    if _supabase_client:
        try:
            # Try by user_id
            res = _supabase_client.from_("profiles").select("*").eq("user_id", user_id_or_token).execute()
            if res.data:
                return res.data[0]
            # Try by alias
            res = _supabase_client.from_("profiles").select("*").eq("alias", user_id_or_token).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase get_profile_by_id notice: {e}")

    # Persistent local store
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM profiles WHERE user_id = ? OR alias = ? OR id = ? LIMIT 1",
                (user_id_or_token, user_id_or_token, user_id_or_token)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.error(f"SQLite get_profile error: {e}")

    return None


# ---------------------------------------------------------------------------
# Check-Ins
# ---------------------------------------------------------------------------

def save_checkin(
    user_id_or_token: str,
    text: str,
    valence: float,
    arousal: float,
    voice_score: float,
    nlp_data: Dict[str, Any],
    dpi: float,
    delta_dpi: float,
    risk_level: str
) -> Dict[str, Any]:
    """Persist check-in to Supabase check_ins table and local persistent DB."""
    record_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "id": record_id,
        "user_id": user_id_or_token,
        "token": user_id_or_token,
        "text": text,
        "valence": float(valence),
        "arousal": float(arousal),
        "voice_score": float(voice_score),
        "nlp_json": json.dumps(nlp_data),
        "dpi": float(dpi),
        "delta_dpi": float(delta_dpi),
        "risk_level": risk_level,
        "created_at": now_iso,
        "timestamp": now_iso,
    }

    # Primary: Supabase
    if _supabase_client:
        try:
            _supabase_client.from_("check_ins").insert({
                "id": record_id,
                "text": text,
                "valence": float(valence),
                "arousal": float(arousal),
                "voice_score": float(voice_score),
                "nlp_json": nlp_data,
                "dpi": float(dpi),
                "delta_dpi": float(delta_dpi),
                "risk_level": risk_level,
                "created_at": now_iso
            }).execute()
        except Exception as e:
            logger.warning(f"Supabase save_checkin notice: {e}")

    # Persistent local store
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO check_ins (id, user_id, token, text, valence, arousal, voice_score, nlp_json, dpi, delta_dpi, risk_level, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["id"],
                record["user_id"],
                record["token"],
                record["text"],
                record["valence"],
                record["arousal"],
                record["voice_score"],
                record["nlp_json"],
                record["dpi"],
                record["delta_dpi"],
                record["risk_level"],
                record["created_at"]
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"SQLite save_checkin error: {e}")

    return record


def get_checkin_history(user_id_or_token: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieve check-in records for a given user or token."""
    # Primary: Supabase
    if _supabase_client:
        try:
            res = _supabase_client.from_("check_ins").select("*").order("created_at", desc=False).limit(limit).execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.warning(f"Supabase get_checkin_history notice: {e}")

    # Persistent local store
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM check_ins 
                WHERE user_id = ? OR token = ? 
                ORDER BY created_at ASC 
                LIMIT ?
            """, (user_id_or_token, user_id_or_token, limit))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["timestamp"] = d["created_at"]
                if d.get("nlp_json"):
                    try:
                        d["nlp"] = json.loads(d["nlp_json"])
                    except Exception:
                        d["nlp"] = {}
                results.append(d)
            return results
    except Exception as e:
        logger.error(f"SQLite get_checkin_history error: {e}")

    return []


# ---------------------------------------------------------------------------
# AI Companion Chat & Conversational Memory
# ---------------------------------------------------------------------------

def save_chat_message(user_id_or_token: str, sender: str, message: str) -> Dict[str, Any]:
    """Store AI companion message for persistent conversational memory."""
    msg_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "id": msg_id,
        "user_id": user_id_or_token,
        "token": user_id_or_token,
        "sender": sender,
        "message": message,
        "created_at": now_iso,
        "timestamp": now_iso,
    }

    # Primary: Supabase
    if _supabase_client:
        try:
            _supabase_client.from_("chat_messages").insert({
                "id": msg_id,
                "sender": sender,
                "message": message,
                "created_at": now_iso
            }).execute()
        except Exception as e:
            logger.warning(f"Supabase save_chat_message notice: {e}")

    # Persistent local store
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_messages (id, user_id, token, sender, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record["id"],
                record["user_id"],
                record["token"],
                record["sender"],
                record["message"],
                record["created_at"]
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"SQLite save_chat_message error: {e}")

    return record


def get_chat_history(user_id_or_token: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve previous chat turns to construct conversational context/memory for the companion."""
    # Primary: Supabase
    if _supabase_client:
        try:
            res = _supabase_client.from_("chat_messages").select("*").order("created_at", desc=False).limit(limit).execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.warning(f"Supabase get_chat_history notice: {e}")

    # Persistent local store
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM chat_messages 
                WHERE user_id = ? OR token = ? 
                ORDER BY created_at ASC 
                LIMIT ?
            """, (user_id_or_token, user_id_or_token, limit))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"SQLite get_chat_history error: {e}")

    return []


# ---------------------------------------------------------------------------
# Community Forum
# ---------------------------------------------------------------------------

def save_forum_post(post_id: str, user_id_or_token: str, alias: str, text: str, lang: str = "en") -> Dict[str, Any]:
    """Store forum post to Supabase forum_posts and persistent DB."""
    now_iso = datetime.now(timezone.utc).isoformat()
    post = {
        "id": post_id or str(uuid.uuid4()),
        "user_id": user_id_or_token,
        "alias": alias,
        "text": text,
        "lang": lang,
        "reactions": {"heart": 0, "hug": 0, "star": 0},
        "flagged": False,
        "reports": 0,
        "created_at": now_iso,
        "timestamp": now_iso,
    }

    # Primary: Supabase
    if _supabase_client:
        try:
            _supabase_client.from_("forum_posts").insert({
                "id": post["id"],
                "alias": alias,
                "text": text,
                "lang": lang,
                "reactions": post["reactions"],
                "flagged": False,
                "reports": 0,
                "created_at": now_iso
            }).execute()
        except Exception as e:
            logger.warning(f"Supabase save_forum_post notice: {e}")

    # Persistent local store
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO forum_posts (id, user_id, alias, text, lang, reactions, flagged, reports, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post["id"],
                post["user_id"],
                post["alias"],
                post["text"],
                post["lang"],
                json.dumps(post["reactions"]),
                0,
                0,
                post["created_at"]
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"SQLite save_forum_post error: {e}")

    return post


def get_forum_posts(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve non-flagged forum posts ordered by newest first."""
    # Primary: Supabase
    if _supabase_client:
        try:
            res = _supabase_client.from_("forum_posts").select("*").eq("flagged", False).order("created_at", desc=True).limit(limit).execute()
            if res.data:
                posts = []
                for p in res.data:
                    p["timestamp"] = p.get("created_at")
                    posts.append(p)
                return posts
        except Exception as e:
            logger.warning(f"Supabase get_forum_posts notice: {e}")

    # Persistent local store
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM forum_posts 
                WHERE flagged = 0 AND reports < 5 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            posts = []
            for r in rows:
                d = dict(r)
                d["timestamp"] = d["created_at"]
                if isinstance(d.get("reactions"), str):
                    try:
                        d["reactions"] = json.loads(d["reactions"])
                    except Exception:
                        d["reactions"] = {"heart": 0, "hug": 0, "star": 0}
                posts.append(d)
            return posts
    except Exception as e:
        logger.error(f"SQLite get_forum_posts error: {e}")

    return []


def react_to_forum_post(post_id: str, reaction: str) -> Optional[Dict[str, int]]:
    """Increment reaction counter on a forum post."""
    # Local update
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT reactions FROM forum_posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            if row:
                reactions = json.loads(row["reactions"]) if isinstance(row["reactions"], str) else (row["reactions"] or {})
                reactions[reaction] = reactions.get(reaction, 0) + 1
                cursor.execute(
                    "UPDATE forum_posts SET reactions = ? WHERE id = ?",
                    (json.dumps(reactions), post_id)
                )
                conn.commit()
                return reactions
    except Exception as e:
        logger.error(f"SQLite react error: {e}")
    return None


def report_forum_post(post_id: str) -> Optional[Dict[str, Any]]:
    """Increment reports count and flag if reports >= 3."""
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT reports FROM forum_posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            if row:
                reports = (row["reports"] or 0) + 1
                flagged = 1 if reports >= 3 else 0
                cursor.execute(
                    "UPDATE forum_posts SET reports = ?, flagged = ? WHERE id = ?",
                    (reports, flagged, post_id)
                )
                conn.commit()
                return {"status": "reported", "reports": reports, "flagged": bool(flagged)}
    except Exception as e:
        logger.error(f"SQLite report error: {e}")
    return None


# ---------------------------------------------------------------------------
# Counselor Queue (HITL)
# ---------------------------------------------------------------------------

def save_counselor_case(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store case into counselor_cases."""
    case_id = case_data.get("id") or str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "id": case_id,
        "user_id": case_data.get("token") or case_data.get("user_id", "ANON"),
        "alias": case_data.get("alias", "Anonymous"),
        "dpi": float(case_data.get("dpi", 0.0)),
        "delta_dpi": float(case_data.get("delta_dpi", 0.0)),
        "risk_level": case_data.get("risk_level", "moderate"),
        "triggers": json.dumps(case_data.get("triggers", [])),
        "text_fragment": case_data.get("text_fragment", ""),
        "jitsi_room": case_data.get("jitsi_room", f"AegisMind-Case-{case_id}"),
        "reviewed": 1 if case_data.get("reviewed") else 0,
        "sev": case_data.get("sev", "SEV-2"),
        "source": case_data.get("source", "checkin"),
        "flagged_at": now_iso,
    }

    # Primary: Supabase
    if _supabase_client:
        try:
            _supabase_client.from_("counselor_cases").insert({
                "id": record["id"],
                "alias": record["alias"],
                "dpi": record["dpi"],
                "delta_dpi": record["delta_dpi"],
                "risk_level": record["risk_level"],
                "triggers": case_data.get("triggers", []),
                "text_fragment": record["text_fragment"],
                "jitsi_room": record["jitsi_room"],
                "reviewed": bool(record["reviewed"]),
                "sev": record["sev"],
                "source": record["source"],
                "flagged_at": now_iso
            }).execute()
        except Exception as e:
            logger.warning(f"Supabase save_counselor_case notice: {e}")

    # Persistent local store
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO counselor_cases (id, user_id, alias, dpi, delta_dpi, risk_level, triggers, text_fragment, jitsi_room, reviewed, sev, source, flagged_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["id"],
                record["user_id"],
                record["alias"],
                record["dpi"],
                record["delta_dpi"],
                record["risk_level"],
                record["triggers"],
                record["text_fragment"],
                record["jitsi_room"],
                record["reviewed"],
                record["sev"],
                record["source"],
                record["flagged_at"]
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"SQLite save_counselor_case error: {e}")

    return record


def get_counselor_queue() -> List[Dict[str, Any]]:
    """Retrieve pending cases for the counselor review queue."""
    # Primary: Supabase
    if _supabase_client:
        try:
            res = _supabase_client.from_("counselor_cases").select("*").eq("reviewed", False).order("flagged_at", desc=True).execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.warning(f"Supabase get_counselor_queue notice: {e}")

    # Persistent local store
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM counselor_cases 
                WHERE reviewed = 0 
                ORDER BY flagged_at DESC
            """)
            rows = cursor.fetchall()
            cases = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("triggers"), str):
                    try:
                        d["triggers"] = json.loads(d["triggers"])
                    except Exception:
                        d["triggers"] = []
                d["jitsi_url"] = f"https://meet.jit.si/{d.get('jitsi_room', 'AegisMind')}"
                cases.append(d)
            return cases
    except Exception as e:
        logger.error(f"SQLite get_counselor_queue error: {e}")

    return []


def mark_counselor_case_reviewed(case_id: str) -> bool:
    """Mark a counselor queue case as reviewed."""
    now_iso = datetime.now(timezone.utc).isoformat()
    # Supabase
    if _supabase_client:
        try:
            _supabase_client.from_("counselor_cases").update({
                "reviewed": True,
                "reviewed_at": now_iso
            }).eq("id", case_id).execute()
        except Exception as e:
            logger.warning(f"Supabase mark_counselor_case_reviewed notice: {e}")

    # Local store
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE counselor_cases SET reviewed = 1, reviewed_at = ? WHERE id = ?",
                (now_iso, case_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"SQLite review error: {e}")
    return False


# ---------------------------------------------------------------------------
# Psychiatrist Dashboard
# ---------------------------------------------------------------------------
# These read the local persistent store. Patient flows always write there (even
# when Supabase is configured), so the dashboard sees the same data either way.
# Clinicians identify a patient by an opaque patient_ref, never by the real user
# id, because for anonymous users that id is also their login token.

CASE_STATUSES = ("new", "acknowledged", "in_contact", "resolved")

_CASE_PRIORITY_ORDER = """
    CASE sev WHEN 'SEV-1' THEN 0 ELSE 1 END,
    CASE risk_level WHEN 'critical' THEN 0 WHEN 'moderate' THEN 1 ELSE 2 END,
    flagged_at DESC
"""
_RISK_RANK = {"critical": 0, "moderate": 1, "low": 2}


def patient_ref_for(user_id: str) -> str:
    """Stable one-way reference a clinician can use in URLs instead of the real user id."""
    return hashlib.sha256(f"aegismind-patient:{user_id}".encode("utf-8")).hexdigest()[:16]


def _case_for_clinician(row) -> Dict[str, Any]:
    """Shape a counselor_cases row for the dashboard, without the real user id."""
    case = dict(row)
    try:
        triggers = json.loads(case.get("triggers") or "[]")
    except (TypeError, ValueError):
        triggers = []
    return {
        "id": case["id"],
        "patient_ref": patient_ref_for(case.get("user_id") or ""),
        "alias": case.get("alias") or "Anonymous",
        "sev": case.get("sev") or "SEV-2",
        "risk_level": case.get("risk_level") or "moderate",
        "dpi": case.get("dpi") or 0.0,
        "delta_dpi": case.get("delta_dpi") or 0.0,
        "triggers": triggers,
        "text_fragment": case.get("text_fragment") or "",
        "source": case.get("source") or "checkin",
        "status": case.get("status") or "new",
        "notes": case.get("notes") or "",
        "reviewed": bool(case.get("reviewed")),
        "flagged_at": case.get("flagged_at"),
        "acknowledged_at": case.get("acknowledged_at"),
        "reviewed_at": case.get("reviewed_at"),
        "jitsi_room": case.get("jitsi_room"),
        "jitsi_url": f"https://meet.jit.si/{case.get('jitsi_room') or 'AegisMind'}",
    }


def _patient_summary(user_id: str, alias: str, checkins: list, open_cases: list, last_chat_at: Optional[str]) -> Dict[str, Any]:
    """One patient's headline numbers; checkins must be oldest-first."""
    last_checkin = checkins[-1] if checkins else None
    has_open_sev1 = any(case["sev"] == "SEV-1" for case in open_cases)
    if has_open_sev1:
        risk_level = "critical"
    elif last_checkin and last_checkin["risk_level"]:
        risk_level = last_checkin["risk_level"]
    else:
        risk_level = "moderate" if open_cases else "low"
    dpi_values = [c["dpi"] for c in checkins if c["dpi"] is not None]
    return {
        "patient_ref": patient_ref_for(user_id),
        "alias": alias or "Anonymous",
        "risk_level": risk_level,
        "dpi": round(last_checkin["dpi"], 3) if last_checkin and last_checkin["dpi"] is not None else None,
        "delta_dpi": round(last_checkin["delta_dpi"], 3) if last_checkin and last_checkin["delta_dpi"] is not None else None,
        "avg_dpi": round(sum(dpi_values) / len(dpi_values), 3) if dpi_values else None,
        "sparkline": [round(value, 3) for value in dpi_values[-7:]],
        "checkin_count": len(checkins),
        "last_checkin_at": last_checkin["created_at"] if last_checkin else None,
        "last_chat_at": last_chat_at,
        "open_cases": len(open_cases),
        "open_sev1": has_open_sev1,
    }


def get_psychiatrist_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    """Open cases, most urgent first: SEV-1, then critical, then moderate, newest first."""
    try:
        with get_sqlite_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM counselor_cases WHERE reviewed = 0 ORDER BY {_CASE_PRIORITY_ORDER} LIMIT ?",
                (limit,),
            ).fetchall()
            return [_case_for_clinician(row) for row in rows]
    except Exception as e:
        logger.error(f"SQLite get_psychiatrist_alerts error: {e}")
        return []


def get_psychiatrist_counts() -> Dict[str, int]:
    """Headline numbers for the dashboard banner and insights tab."""
    start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    counts = {"open_sev1": 0, "open_sev2": 0, "unacknowledged": 0, "resolved_today": 0}
    queries = {
        "open_sev1": ("reviewed = 0 AND sev = 'SEV-1'", ()),
        "open_sev2": ("reviewed = 0 AND sev != 'SEV-1'", ()),
        "unacknowledged": ("reviewed = 0 AND COALESCE(status, 'new') = 'new'", ()),
        "resolved_today": ("reviewed = 1 AND reviewed_at >= ?", (start_of_today,)),
    }
    try:
        with get_sqlite_conn() as conn:
            for name, (where_clause, params) in queries.items():
                counts[name] = conn.execute(
                    f"SELECT COUNT(*) FROM counselor_cases WHERE {where_clause}", params
                ).fetchone()[0]
    except Exception as e:
        logger.error(f"SQLite get_psychiatrist_counts error: {e}")
    return counts


def get_psychiatrist_patients() -> List[Dict[str, Any]]:
    """Every patient with activity, emergency patients first."""
    try:
        with get_sqlite_conn() as conn:
            # Step 1: load the raw rows once instead of querying per patient
            aliases = {row["user_id"]: row["alias"] for row in conn.execute("SELECT user_id, alias FROM profiles")}
            checkins_by_patient: Dict[str, list] = {}
            for row in conn.execute(
                "SELECT user_id, dpi, delta_dpi, risk_level, created_at FROM check_ins ORDER BY created_at ASC"
            ):
                checkins_by_patient.setdefault(row["user_id"], []).append(row)
            open_cases_by_patient: Dict[str, list] = {}
            for row in conn.execute("SELECT user_id, sev, alias FROM counselor_cases WHERE reviewed = 0"):
                open_cases_by_patient.setdefault(row["user_id"], []).append(row)
            last_chat_by_patient = {
                row["user_id"]: row["last_at"]
                for row in conn.execute("SELECT user_id, MAX(created_at) AS last_at FROM chat_messages GROUP BY user_id")
            }
    except Exception as e:
        logger.error(f"SQLite get_psychiatrist_patients error: {e}")
        return []

    # Step 2: build one summary per patient who has any activity
    patient_ids = set(checkins_by_patient) | set(open_cases_by_patient) | set(last_chat_by_patient)
    patient_ids.discard(None)
    patients = []
    for user_id in patient_ids:
        open_cases = open_cases_by_patient.get(user_id, [])
        alias = aliases.get(user_id) or (open_cases[0]["alias"] if open_cases else None)
        patients.append(_patient_summary(
            user_id, alias, checkins_by_patient.get(user_id, []), open_cases, last_chat_by_patient.get(user_id)
        ))

    # Step 3: emergencies first, then by risk, then by how high the DPI is
    patients.sort(key=lambda p: (not p["open_sev1"], _RISK_RANK.get(p["risk_level"], 2), -(p["dpi"] or 0)))
    return patients


def _find_user_id_by_patient_ref(conn, patient_ref: str) -> Optional[str]:
    rows = conn.execute(
        "SELECT user_id FROM profiles UNION SELECT user_id FROM check_ins "
        "UNION SELECT user_id FROM counselor_cases UNION SELECT user_id FROM chat_messages"
    ).fetchall()
    for row in rows:
        if row["user_id"] and patient_ref_for(row["user_id"]) == patient_ref:
            return row["user_id"]
    return None


def get_psychiatrist_patient_detail(patient_ref: str) -> Optional[Dict[str, Any]]:
    """Full history for one patient: check-ins, chat transcript and every case."""
    try:
        with get_sqlite_conn() as conn:
            # Step 1: resolve the opaque reference back to the real user id
            user_id = _find_user_id_by_patient_ref(conn, patient_ref)
            if not user_id:
                return None

            # Step 2: load profile, latest check-ins, latest chat turns and all cases
            profile = conn.execute("SELECT alias, created_at FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
            checkin_total = conn.execute(
                "SELECT COUNT(*) FROM check_ins WHERE user_id = ? OR token = ?", (user_id, user_id)
            ).fetchone()[0]
            checkin_rows = conn.execute(
                """SELECT * FROM (
                       SELECT id, text, valence, arousal, voice_score, nlp_json, dpi, delta_dpi, risk_level, created_at
                       FROM check_ins WHERE user_id = ? OR token = ?
                       ORDER BY created_at DESC LIMIT 60
                   ) ORDER BY created_at ASC""",
                (user_id, user_id),
            ).fetchall()
            chat_rows = conn.execute(
                """SELECT * FROM (
                       SELECT sender, message, created_at
                       FROM chat_messages WHERE user_id = ? OR token = ?
                       ORDER BY created_at DESC LIMIT 100
                   ) ORDER BY created_at ASC""",
                (user_id, user_id),
            ).fetchall()
            case_rows = conn.execute(
                "SELECT * FROM counselor_cases WHERE user_id = ? ORDER BY flagged_at DESC", (user_id,)
            ).fetchall()
    except Exception as e:
        logger.error(f"SQLite get_psychiatrist_patient_detail error: {e}")
        return None

    # Step 3: build the response from those rows
    cases = [_case_for_clinician(row) for row in case_rows]
    open_cases = [row for row in case_rows if not row["reviewed"]]
    last_chat_at = chat_rows[-1]["created_at"] if chat_rows else None
    alias = profile["alias"] if profile else (case_rows[0]["alias"] if case_rows else None)

    checkins = []
    for row in checkin_rows:
        checkin = dict(row)
        try:
            checkin["nlp"] = json.loads(checkin.pop("nlp_json") or "{}")
        except (TypeError, ValueError):
            checkin["nlp"] = {}
        checkins.append(checkin)

    summary = _patient_summary(user_id, alias, checkin_rows, open_cases, last_chat_at)
    summary["checkin_count"] = checkin_total
    summary["first_seen"] = (profile["created_at"] if profile else None) or (checkins[0]["created_at"] if checkins else None)
    summary["checkins"] = checkins
    summary["chat"] = [dict(row) for row in chat_rows]
    summary["cases"] = cases
    return summary


def update_psychiatrist_case(case_id: str, status: Optional[str] = None, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Move a case through its status steps and/or save the clinician's note."""
    now_iso = datetime.now(timezone.utc).isoformat()

    if status == "resolved":
        # Marks the case reviewed in Supabase and the local store so it leaves the queue everywhere
        mark_counselor_case_reviewed(case_id)

    changes: List[str] = []
    values: List[Any] = []
    if status is not None:
        changes.append("status = ?")
        values.append(status)
        if status in ("acknowledged", "in_contact", "resolved"):
            changes.append("acknowledged_at = COALESCE(acknowledged_at, ?)")
            values.append(now_iso)
    if notes is not None:
        changes.append("notes = ?")
        values.append(notes)

    try:
        with get_sqlite_conn() as conn:
            if changes:
                cursor = conn.execute(
                    f"UPDATE counselor_cases SET {', '.join(changes)} WHERE id = ?", (*values, case_id)
                )
                if cursor.rowcount == 0:
                    return None
                conn.commit()
            row = conn.execute("SELECT * FROM counselor_cases WHERE id = ?", (case_id,)).fetchone()
            if row and changes and _supabase_client:
                _push_case_progress_to_supabase(case_id, row)
            return _case_for_clinician(row) if row else None
    except Exception as e:
        logger.error(f"SQLite update_psychiatrist_case error: {e}")
        return None


def _push_case_progress_to_supabase(case_id: str, local_row) -> None:
    """Copy the case's status, note and first-acknowledged time to Supabase (needs the 02 psychiatrist migration)."""
    try:
        _supabase_client.from_("counselor_cases").update({
            "status": local_row["status"],
            "notes": local_row["notes"],
            "acknowledged_at": local_row["acknowledged_at"],
        }).eq("id", case_id).execute()
    except Exception as e:
        logger.warning(f"Supabase update_psychiatrist_case notice: {e}")
