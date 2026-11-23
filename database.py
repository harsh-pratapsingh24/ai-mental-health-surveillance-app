"""
AegisMind Database & Persistence Layer
Primary Backend: Supabase PostgreSQL (via Supabase Python Client & PostgREST)
Persistent Fallback: Disk-backed SQLite (data/aegismind_persistent.db) to guarantee 
persistence across server restarts even before cloud DDL migrations are executed.
"""

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
        conn.commit()


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
            profile = get_profile_by_id(user_id_or_token)
            supabase_user_id = profile.get("id") if profile else None
            insert_payload = {
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
            }
            if supabase_user_id:
                insert_payload["user_id"] = supabase_user_id
            _supabase_client.from_("check_ins").insert(insert_payload).execute()
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
            profile = get_profile_by_id(user_id_or_token)
            supabase_user_id = profile.get("id") if profile else None
            if supabase_user_id:
                res = _supabase_client.from_("check_ins").select("*").eq("user_id", supabase_user_id).order("created_at", desc=False).limit(limit).execute()
                if res.data is not None:
                    return res.data
            elif user_id_or_token:
                # Direct check if user_id_or_token was already a profile UUID
                try:
                    res = _supabase_client.from_("check_ins").select("*").eq("user_id", user_id_or_token).order("created_at", desc=False).limit(limit).execute()
                    if res.data:
                        return res.data
                except Exception:
                    pass
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
            profile = get_profile_by_id(user_id_or_token)
            supabase_user_id = profile.get("id") if profile else None
            insert_data = {
                "id": msg_id,
                "sender": sender,
                "message": message,
                "created_at": now_iso
            }
            if supabase_user_id:
                insert_data["user_id"] = supabase_user_id
            _supabase_client.from_("chat_messages").insert(insert_data).execute()
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
            profile = get_profile_by_id(user_id_or_token)
            supabase_user_id = profile.get("id") if profile else None
            if supabase_user_id:
                res = _supabase_client.from_("chat_messages").select("*").eq("user_id", supabase_user_id).order("created_at", desc=False).limit(limit).execute()
                if res.data is not None:
                    return res.data
            elif user_id_or_token:
                try:
                    res = _supabase_client.from_("chat_messages").select("*").eq("user_id", user_id_or_token).order("created_at", desc=False).limit(limit).execute()
                    if res.data:
                        return res.data
                except Exception:
                    pass
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
    reports = 1
    flagged = False
    if _supabase_client:
        try:
            res = _supabase_client.from_("forum_posts").select("reports").eq("id", post_id).limit(1).execute()
            if res.data:
                reports = (res.data[0].get("reports") or 0) + 1
                flagged = (reports >= 3)
                _supabase_client.from_("forum_posts").update({"reports": reports, "flagged": flagged}).eq("id", post_id).execute()
        except Exception as e:
            logger.warning(f"Supabase report_forum_post notice: {e}")

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
            elif _supabase_client:
                return {"status": "reported", "reports": reports, "flagged": bool(flagged)}
    except Exception as e:
        logger.error(f"SQLite report error: {e}")
    return {"status": "reported", "reports": reports, "flagged": bool(flagged)}


def delete_forum_post(post_id: str, user_id_or_token: Optional[str] = None) -> bool:
    """Delete a forum post from Supabase and SQLite."""
    deleted = False
    if _supabase_client:
        try:
            query = _supabase_client.from_("forum_posts").delete().eq("id", post_id)
            if user_id_or_token and user_id_or_token != "ADMIN":
                query = query.eq("user_id", user_id_or_token)
            query.execute()
            deleted = True
        except Exception as e:
            logger.warning(f"Supabase delete_forum_post notice: {e}")
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            if user_id_or_token and user_id_or_token != "ADMIN":
                cursor.execute("DELETE FROM forum_posts WHERE id = ? AND user_id = ?", (post_id, user_id_or_token))
            else:
                cursor.execute("DELETE FROM forum_posts WHERE id = ?", (post_id,))
            conn.commit()
            if cursor.rowcount > 0:
                deleted = True
    except Exception as e:
        logger.error(f"SQLite delete error: {e}")
    return deleted


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
                "flagged_at": now_iso
            }).execute()
        except Exception as e:
            logger.warning(f"Supabase save_counselor_case notice: {e}")

    # Persistent local store
    try:
        with get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO counselor_cases (id, user_id, alias, dpi, delta_dpi, risk_level, triggers, text_fragment, jitsi_room, reviewed, sev, flagged_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
