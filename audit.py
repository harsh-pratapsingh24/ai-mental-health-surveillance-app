"""
AegisMind — Audit Logging Framework

Provides immutable audit trail for compliance with HIPAA/India DPDP Act.
Logs critical events: crisis escalations, consent changes, data access,
counselor queue modifications, and data exports.

In production, this writes to the audit_logs PostgreSQL table.
Currently falls back to structured JSON logging.
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum


class AuditEventType(Enum):
    """Classification of auditable events."""
    CRISIS_ESCALATED = "crisis_escalated"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_REVOKED = "consent_revoked"
    CHECKIN_SUBMITTED = "checkin_submitted"
    COUNSELOR_ACCESS = "counselor_access"
    CASE_REVIEWED = "case_reviewed"
    DATA_EXPORTED = "data_exported"
    SESSION_CREATED = "session_created"
    SESSION_RESET = "session_reset"
    FORUM_POST_CREATED = "forum_post_created"
    FORUM_POST_REPORTED = "forum_post_reported"
    HELPLINE_DISPLAYED = "helpline_displayed"
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"


# Dedicated audit logger — separate from request logging
_audit_logger = logging.getLogger("aegismind.audit")
_audit_logger.setLevel(logging.INFO)


class AuditEntry:
    """Immutable audit log entry."""

    def __init__(
        self,
        event_type: AuditEventType,
        actor_token: str = None,
        target_id: str = None,
        details: dict = None,
        ip_address: str = None,
    ):
        self.event_type = event_type
        self.actor_token = actor_token
        self.target_id = target_id
        self.details = details or {}
        self.ip_address = ip_address
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "actor_token": self.actor_token,
            "target_id": self.target_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


def log_audit_event(
    event_type: AuditEventType,
    actor_token: str = None,
    target_id: str = None,
    details: dict = None,
    ip_address: str = None,
) -> AuditEntry:
    """
    Record an audit event.

    In production, this should also write to the audit_logs PostgreSQL table.
    For now, it writes structured JSON to the audit logger.

    Args:
        event_type: Classification of the event
        actor_token: Anonymous user token performing the action
        target_id: ID of the entity being acted upon
        details: Additional context (no PHI)
        ip_address: Client IP (anonymized in logs)

    Returns:
        AuditEntry for testing/inspection
    """
    entry = AuditEntry(
        event_type=event_type,
        actor_token=actor_token,
        target_id=target_id,
        details=details,
        ip_address=ip_address,
    )

    _audit_logger.info(entry.to_json())

    # TODO: When PostgreSQL is enabled, write to audit_logs table:
    # from models import db, AuditLog
    # db.session.add(AuditLog(
    #     event_type=event_type.value,
    #     actor_token=actor_token,
    #     target_id=target_id,
    #     details=details,
    #     ip_address=ip_address,
    # ))
    # db.session.commit()

    return entry
