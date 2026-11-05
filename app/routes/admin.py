from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query , Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app import audit
from app.db import get_db
from app.models import AuditLog, LoginSession, User
from app.security import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Every admin route depends on this. Non-admins get the same 404 as an unknown URL."""
    if user.role != "admin":
        audit.log(db, user.id, "admin_access", result="refused", details="not an admin")
        raise HTTPException(status_code=404, detail="Not Found")
    return user


class RoleIn(BaseModel):
    role: str = Field(pattern="^(user|admin)$")


@router.get("/activity")
def activity(
    actor_id: Optional[int] = Query(None, ge=1, le=2147483647),
    action: Optional[str] = Query(None, max_length=40),
    document_id: Optional[int] = Query(None, ge=1, le=2147483647),
    result: Optional[str] = Query(None, pattern="^(allowed|refused)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if actor_id is not None:
        q = q.filter(AuditLog.actor_id == actor_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if document_id is not None:
        q = q.filter(AuditLog.document_id == document_id)
    if result:
        q = q.filter(AuditLog.result == result)
    rows = q.order_by(AuditLog.id.desc()).offset(offset).limit(limit).all()
    out = [{"id": r.id, "time": r.time.isoformat(), "actor_id": r.actor_id, "action": r.action,
            "document_id": r.document_id, "result": r.result, "details": r.details}
           for r in rows]
    audit.log(db, admin.id, "admin_view_activity", details=f"returned {len(out)} rows")
    return out


@router.get("/audit/verify")
def verify_audit(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    ok, bad_id = audit.verify_chain(db)
    audit.log(db, admin.id, "admin_verify_audit", details=f"intact={ok}")
    return {"intact": ok, "first_bad_row_id": bad_id}


@router.get("/users")
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [{"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active,
             "created_at": u.created_at.isoformat()}
            for u in db.query(User).order_by(User.id).all()]


def _target(db: Session, user_id: int) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    return target


@router.post("/users/{user_id}/deactivate")
def deactivate(user_id: int = Path(ge=1, le=2147483647), admin: User = Depends(require_admin),
               db: Session = Depends(get_db)):
    target = _target(db, user_id)
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate yourself")
    target.is_active = False
    db.query(LoginSession).filter_by(user_id=target.id).delete()  # kicks them out right now
    db.commit()
    audit.log(db, admin.id, "deactivate_user", details=f"user_id={target.id} username={target.username}")
    return {"status": "deactivated"}


@router.post("/users/{user_id}/activate")
def activate(user_id: int = Path(ge=1, le=2147483647), admin: User = Depends(require_admin),
             db: Session = Depends(get_db)):
    target = _target(db, user_id)
    target.is_active = True
    db.commit()
    audit.log(db, admin.id, "activate_user", details=f"user_id={target.id} username={target.username}")
    return {"status": "activated"}


@router.patch("/users/{user_id}/role")
def change_role(body: RoleIn, user_id: int = Path(ge=1, le=2147483647),
                admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = _target(db, user_id)
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot change your own role")
    old = target.role
    target.role = body.role
    db.commit()
    audit.log(db, admin.id, "change_role", details=f"user_id={target.id} {old}->{body.role}")
    return {"id": target.id, "role": target.role}