from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app import audit
from app.db import get_db
from app.models import Grant, User, now
from app.permissions import require
from app.security import get_current_user

router = APIRouter(prefix="/documents/{doc_id}/grants", tags=["grants"])


class GrantIn(BaseModel):
    username: str = Field(max_length=50)
    permission: str = Field(pattern="^(read|edit)$")
    expires_at: Optional[datetime] = None


def _grant_out(g: Grant, username: str) -> dict:
    return {"id": g.id, "user_id": g.user_id, "username": username, "permission": g.permission,
            "created_at": g.created_at.isoformat(),
            "expires_at": g.expires_at.isoformat() if g.expires_at else None}


@router.post("", status_code=201)
def grant_access(doc_id: int, body: GrantIn, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    doc = require(db, user, doc_id, "grant")  # only the owner passes this
    target = db.query(User).filter_by(username=body.username, is_active=True).first()
    if target is None:
        audit.log(db, user.id, "grant", doc.id, "refused", "unknown user")
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == doc.owner_id:
        raise HTTPException(status_code=400, detail="Owner already has full access")
    if body.expires_at is not None and body.expires_at <= now():
        raise HTTPException(status_code=400, detail="Expiry must be in the future")
    # Replace any earlier active grant for this person, so there is never ambiguity.
    for old in db.query(Grant).filter(Grant.document_id == doc.id, Grant.user_id == target.id,
                                      Grant.revoked_at.is_(None)).all():
        old.revoked_at = now()
    g = Grant(document_id=doc.id, user_id=target.id, permission=body.permission,
              granted_by=user.id, expires_at=body.expires_at)
    db.add(g)
    db.commit()
    audit.log(db, user.id, "grant", doc.id,
              details=f"to={target.username} permission={body.permission} expires={body.expires_at}")
    return _grant_out(g, target.username)


@router.get("")
def list_grants(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = require(db, user, doc_id, "grant")  # owner only
    rows = (db.query(Grant, User).join(User, User.id == Grant.user_id)
            .filter(Grant.document_id == doc.id, Grant.revoked_at.is_(None)).all())
    return [_grant_out(g, u.username) for g, u in rows]


@router.delete("/{grant_id}")
def revoke_access(doc_id: int, grant_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    doc = require(db, user, doc_id, "grant")  # owner only
    g = db.query(Grant).filter_by(id=grant_id, document_id=doc.id, revoked_at=None).first()
    if g is None:
        raise HTTPException(status_code=404, detail="Grant not found")
    g.revoked_at = now()
    db.commit()
    audit.log(db, user.id, "revoke", doc.id, details=f"grant_id={g.id} user_id={g.user_id}")
    return {"status": "revoked"}