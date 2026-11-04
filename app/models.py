from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def now() -> datetime:
    """All times are stored as naive UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10), default="user")  # "admin" or "user"
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=now)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=now)
    expires_at: Mapped[datetime]


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50), default="general")
    stored_name: Mapped[str] = mapped_column(String(64), unique=True)  # random name on disk
    original_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=now)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class Grant(Base):
    __tablename__ = "grants"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    permission: Mapped[str] = mapped_column(String(10))  # "read" or "edit"
    granted_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=now)
    expires_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(default=None)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    time: Mapped[datetime] = mapped_column(default=now)
    actor_id: Mapped[Optional[int]] = mapped_column(default=None)
    action: Mapped[str] = mapped_column(String(40))
    document_id: Mapped[Optional[int]] = mapped_column(default=None)
    result: Mapped[str] = mapped_column(String(10))  # "allowed" or "refused"
    details: Mapped[str] = mapped_column(Text, default="")
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    time: Mapped[datetime] = mapped_column(default=now, index=True)
    username: Mapped[str] = mapped_column(String(50), index=True)
    ip: Mapped[str] = mapped_column(String(64), index=True)