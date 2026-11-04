from datetime import timedelta
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from app import audit
from app.models import LoginAttempt, now

WINDOW_MINUTES = 15
MAX_PER_USERNAME = 5
MAX_PER_IP = 20


def client_ip(request: Request) -> str:
    # Behind Render's proxy the real address is in X-Forwarded-For.
    # A client can fake this header, so the per-IP limit is best-effort;
    # the per-username limit does not depend on it.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:64] or "unknown"
    return request.client.host if request.client else "unknown"


def _since():
    return now() - timedelta(minutes=WINDOW_MINUTES)


def check_login_allowed(db: Session, username: str, ip: str) -> None:
    by_user = db.query(LoginAttempt).filter(
        LoginAttempt.username == username, LoginAttempt.time > _since()).count()
    by_ip = db.query(LoginAttempt).filter(
        LoginAttempt.ip == ip, LoginAttempt.time > _since()).count()
    if by_user >= MAX_PER_USERNAME or by_ip >= MAX_PER_IP:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.",
                            headers={"Retry-After": str(WINDOW_MINUTES * 60)})


def record_failure(db: Session, username: str, ip: str) -> None:
    db.query(LoginAttempt).filter(  # keep the table small
        LoginAttempt.time < now() - timedelta(days=1)).delete()
    db.add(LoginAttempt(username=username, ip=ip))
    db.commit()
    count = db.query(LoginAttempt).filter(
        LoginAttempt.username == username, LoginAttempt.time > _since()).count()
    if count == MAX_PER_USERNAME:  # logged once, so blocked requests cannot flood the audit log
        audit.log(db, None, "login_lockout", result="refused",
                  details=f"username={username} ip={ip} after {count} failures")


def clear_failures(db: Session, username: str) -> None:
    db.query(LoginAttempt).filter(LoginAttempt.username == username).delete()
    db.commit()