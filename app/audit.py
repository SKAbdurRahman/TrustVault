import hashlib
import threading
from sqlalchemy import text
_write_lock = threading.Lock()
_PG_LOCK_KEY = 748392  # arbitrary number that identifies "audit log writer"
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models import AuditLog, now


def _compute_hash(prev_hash, time, actor_id, action, document_id, result, details) -> str:
    text = "|".join([prev_hash, time.isoformat(), str(actor_id), action,
                     str(document_id), result, details])
    return hashlib.sha256(text.encode()).hexdigest()


def log(db: Session, actor_id: Optional[int], action: str,
        document_id: Optional[int] = None, result: str = "allowed",
        details: str = "") -> AuditLog:
    # Everything from "read the last row" to "commit" happens under the lock,
    # so two requests can never both build on the same previous row.
    with _write_lock:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _PG_LOCK_KEY})
        last = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        prev_hash = last.hash if last else ""
        t = now()
        row = AuditLog(
            time=t, actor_id=actor_id, action=action, document_id=document_id,
            result=result, details=details, prev_hash=prev_hash,
            hash=_compute_hash(prev_hash, t, actor_id, action, document_id, result, details),
        )
        db.add(row)
        db.commit()  # commit releases the Postgres lock too
    return row


def verify_chain(db: Session) -> Tuple[bool, Optional[int]]:
    """Returns (True, None) if intact, or (False, id_of_first_bad_row)."""
    prev_hash = ""
    for row in db.query(AuditLog).order_by(AuditLog.id):
        expected = _compute_hash(prev_hash, row.time, row.actor_id, row.action,
                                 row.document_id, row.result, row.details)
        if row.prev_hash != prev_hash or row.hash != expected:
            return False, row.id
        prev_hash = row.hash
    return True, None