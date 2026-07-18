"""Small helper so every module logs to the audit trail the same way."""
from modules.database import get_session
from modules.models import AuditLog


def log_action(invoice_id, user_id, action: str, details: str = ""):
    session = get_session()
    try:
        entry = AuditLog(invoice_id=invoice_id, user_id=user_id, action=action, details=details)
        session.add(entry)
        session.commit()
        return entry.id
    finally:
        session.close()


def get_audit_trail(invoice_id):
    session = get_session()
    try:
        rows = (
            session.query(AuditLog)
            .filter(AuditLog.invoice_id == invoice_id)
            .order_by(AuditLog.created_at.asc())
            .all()
        )
        return [
            {
                "action": r.action,
                "details": r.details,
                "user_id": r.user_id,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    finally:
        session.close()
