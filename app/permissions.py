from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models import User, Document, Grant, now
from app import audit

ALL_ACTIONS = {"read", "download", "edit", "delete", "grant"}
READ_ACTIONS = {"read", "download"}
EDIT_ACTIONS = READ_ACTIONS | {"edit"}


def can(db: Session, user: User, doc: Document, action: str) -> bool:
    """Deny by default. Checks the database every time, nothing is cached."""
    if action not in ALL_ACTIONS:
        return False
    if user is None or not user.is_active:
        return False
    if doc is None or doc.deleted_at is not None:
        return False
    if doc.owner_id == user.id:
        return True  # the owner can do everything to their own document
    # NOTE: there is deliberately no "admin" shortcut. Admins manage users and
    # see activity, but cannot read documents unless someone granted them access.
    grants = db.query(Grant).filter(
        Grant.document_id == doc.id,
        Grant.user_id == user.id,
        Grant.revoked_at.is_(None),
        or_(Grant.expires_at.is_(None), Grant.expires_at > now()),
    ).all()
    allowed = set()
    for g in grants:
        if g.permission == "edit":
            allowed |= EDIT_ACTIONS
        elif g.permission == "read":
            allowed |= READ_ACTIONS
    return action in allowed  # delete and grant are never reachable through a grant


def require(db: Session, user: User, doc_id: int, action: str) -> Document:
    """Every document route calls this first. Refusals are logged, then answered with 404."""
    doc = db.get(Document, doc_id)
    if not can(db, user, doc, action):
        audit.log(db, user.id, action, doc_id, "refused", "no permission or not found")
        raise HTTPException(status_code=404, detail="Document not found")
    return doc