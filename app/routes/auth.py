from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app import audit
from app.db import get_db
from app.models import User
from app.security import (bearer, create_session, end_session, get_current_user,
                          hash_password, verify_password)

router = APIRouter(prefix="/auth", tags=["auth"])

# Used so a login for an unknown username takes about as long as a real one.
DUMMY_HASH = hash_password("dummy-password")


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    username: str = Field(max_length=50)
    password: str = Field(max_length=128)


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=body.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    # The role is never read from the request, so nobody can register as admin.
    user = User(username=body.username, password_hash=hash_password(body.password), role="user")
    db.add(user)
    db.commit()
    audit.log(db, user.id, "register")
    return {"id": user.id, "username": user.username, "role": user.role}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=body.username).first()
    if user is None:
        verify_password(body.password, DUMMY_HASH)
    ok = user is not None and user.is_active and verify_password(body.password, user.password_hash)
    if not ok:
        audit.log(db, user.id if user else None, "login", result="refused",
                  details=f"username={body.username[:50]}")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(db, user)
    audit.log(db, user.id, "login")
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    end_session(db, creds.credentials)
    audit.log(db, user.id, "logout")
    return {"status": "logged out"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}