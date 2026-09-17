"""
AegisMind — SQLAlchemy Models for PostgreSQL Migration

This module defines the database schema mapping for when the application
migrates from in-memory dicts to a persistent PostgreSQL backend.

Current in-memory stores → SQLAlchemy models:
  USER_PROFILES    → UserProfile
  CHECK_IN_HISTORY → CheckIn
  FORUM_POSTS      → ForumPost
  COUNSELOR_QUEUE  → CounselorQueue
  SEV1_CASES       → Sev1Case
  CHAT_SESSIONS    → ChatSession

Usage:
  1. Set DATABASE_URL in .env to a PostgreSQL connection string
  2. pip install flask-sqlalchemy alembic
  3. Uncomment the SQLAlchemy initialization in app.py
  4. Run: flask db init && flask db migrate && flask db upgrade

The in-memory stores remain active as fallback when DATABASE_URL is empty.
"""

# Placeholder for SQLAlchemy models — uncomment after installing flask-sqlalchemy
#
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class UserProfile(db.Model):
    """Anonymous user session profile with consent record."""
    __tablename__ = "user_profiles"

    token = db.Column(db.String(32), primary_key=True)
    alias = db.Column(db.String(64), nullable=False)
    consent = db.Column(db.Boolean, default=False, nullable=False)
    google_sub = db.Column(db.String(128), unique=True, nullable=True)
    email = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    checkins = db.relationship("CheckIn", backref="user", lazy="dynamic")
    chat_messages = db.relationship("ChatSession", backref="user", lazy="dynamic")

    __table_args__ = (
        db.Index("idx_user_profiles_token", "token"),
    )


class CheckIn(db.Model):
    """Wellness check-in record with NLP analysis results."""
    __tablename__ = "check_ins"

    id = db.Column(db.String(36), primary_key=True)  # UUID
    token = db.Column(db.String(32), db.ForeignKey("user_profiles.token"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    valence = db.Column(db.Float, nullable=False)
    arousal = db.Column(db.Float, nullable=False)
    voice_score = db.Column(db.Float, default=0.7)
    nlp_json = db.Column(db.JSON, nullable=True)  # Full NLP analysis result
    dpi = db.Column(db.Float, nullable=True)
    delta_dpi = db.Column(db.Float, nullable=True)
    risk_level = db.Column(db.String(16), nullable=True)  # low / moderate / critical
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("idx_checkins_token", "token"),
        db.Index("idx_checkins_timestamp", "timestamp"),
        db.Index("idx_checkins_risk_level", "risk_level"),
    )


class ForumPost(db.Model):
    """Anonymous community forum post with moderation state."""
    __tablename__ = "forum_posts"

    id = db.Column(db.String(36), primary_key=True)
    alias = db.Column(db.String(64), nullable=False)
    text = db.Column(db.Text, nullable=False)
    lang = db.Column(db.String(4), default="en")
    reactions = db.Column(db.JSON, default={"heart": 0, "hug": 0, "star": 0})
    flagged = db.Column(db.Boolean, default=False)
    reports = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("idx_forum_posts_timestamp", "timestamp"),
        db.Index("idx_forum_posts_flagged", "flagged"),
    )


class CounselorQueue(db.Model):
    """HITL counselor review queue entry."""
    __tablename__ = "counselor_queue"

    id = db.Column(db.String(36), primary_key=True)
    token = db.Column(db.String(32), db.ForeignKey("user_profiles.token"), nullable=False)
    alias = db.Column(db.String(64), nullable=False)
    dpi = db.Column(db.Float, nullable=False)
    delta_dpi = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(16), nullable=False)
    triggers = db.Column(db.JSON, default=list)
    jitsi_room = db.Column(db.String(128), nullable=True)
    reviewed = db.Column(db.Boolean, default=False)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    sev = db.Column(db.String(8), default="SEV-2")
    flagged_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("idx_counselor_queue_token", "token"),
        db.Index("idx_counselor_queue_reviewed", "reviewed"),
        db.Index("idx_counselor_queue_flagged_at", "flagged_at"),
    )


class Sev1Case(db.Model):
    """Critical SEV-1 crisis case record."""
    __tablename__ = "sev1_cases"

    id = db.Column(db.String(36), primary_key=True)
    token = db.Column(db.String(32), db.ForeignKey("user_profiles.token"), nullable=False)
    alias = db.Column(db.String(64), nullable=False)
    text_fragment = db.Column(db.Text, nullable=True)
    dpi = db.Column(db.Float, default=1.0)
    delta_dpi = db.Column(db.Float, default=0.0)
    jitsi_room = db.Column(db.String(128), nullable=True)
    reviewed = db.Column(db.Boolean, default=False)
    flagged_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("idx_sev1_cases_token", "token"),
        db.Index("idx_sev1_cases_flagged_at", "flagged_at"),
    )


class ChatSession(db.Model):
    """Companion chat message history."""
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(32), db.ForeignKey("user_profiles.token"), nullable=False)
    sender = db.Column(db.String(16), nullable=False)  # "user" or "companion"
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("idx_chat_sessions_token", "token"),
        db.Index("idx_chat_sessions_timestamp", "timestamp"),
    )


class AuditLog(db.Model):
    """Immutable audit trail for compliance (HIPAA/India DPDP Act)."""
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(db.String(64), nullable=False)
    actor_token = db.Column(db.String(32), nullable=True)
    target_id = db.Column(db.String(64), nullable=True)
    details = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("idx_audit_logs_event_type", "event_type"),
        db.Index("idx_audit_logs_timestamp", "timestamp"),
        db.Index("idx_audit_logs_actor_token", "actor_token"),
    )
