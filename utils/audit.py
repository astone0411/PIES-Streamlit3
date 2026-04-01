"""
Audit logging helpers.
Every data-changing action should call log_action() so there is an
immutable record of who did what and when.
"""

import json
from datetime import datetime
from database.models import AuditLog, get_session
from utils.auth import current_user_id


def log_action(action: str, specimen_id: int | None = None, detail: dict | None = None):
    """
    Write an audit log entry.

    Parameters
    ----------
    action      : dot-namespaced string, e.g. "specimen.create", "qc.approve"
    specimen_id : FK to specimens table (optional)
    detail      : arbitrary dict serialised to JSON (optional)
    """
    session = get_session()
    try:
        entry = AuditLog(
            user_id=current_user_id(),
            specimen_id=specimen_id,
            action=action,
            detail=json.dumps(detail) if detail else None,
            timestamp=datetime.utcnow(),
        )
        session.add(entry)
        session.commit()
    finally:
        session.close()
