import os
import sys
import uuid
from app import audit
from app.config import STORAGE_DIR
from app.db import SessionLocal
from app.models import Document, Grant, User
from app.security import hash_password


def password(var: str) -> str:
    value = os.getenv(var)
    if not value or len(value) < 8:
        sys.exit(f"Set {var} (at least 8 characters)")
    return value


def ensure_user(db, name, role, pw):
    u = db.query(User).filter_by(username=name).first()
    if u is None:
        u = User(username=name, password_hash=hash_password(pw), role=role)
        db.add(u)
        db.commit()
        audit.log(db, u.id, "seed_user", details=f"{name} ({role})")
    return u


def ensure_doc(db, owner, title, category, text):
    data = text.encode()
    doc = db.query(Document).filter_by(owner_id=owner.id, title=title).first()
    if doc is None:
        doc = Document(owner_id=owner.id, title=title, category=category,
                       stored_name=uuid.uuid4().hex, original_name=title + ".txt",
                       content_type="text/plain", size=len(data))
        db.add(doc)
        db.commit()
        audit.log(db, owner.id, "upload", doc.id, details="seed")
    os.makedirs(STORAGE_DIR, exist_ok=True)
    path = os.path.join(STORAGE_DIR, doc.stored_name)
    if not os.path.isfile(path):  # free hosting wipes the disk on redeploy
        with open(path, "wb") as f:
            f.write(data)
    return doc


with SessionLocal() as db:
    admin = ensure_user(db, "demo_admin", "admin", password("DEMO_ADMIN_PASSWORD"))
    owner = ensure_user(db, "demo_owner", "user", password("DEMO_OWNER_PASSWORD"))
    viewer = ensure_user(db, "demo_viewer", "user", password("DEMO_VIEWER_PASSWORD"))
    shared = ensure_doc(db, owner, "Shared contract (demo)", "contracts", "Demo contract shared with the viewer.\n")
    ensure_doc(db, owner, "Private salary letter (demo)", "hr", "Demo salary letter. Only the owner may read this.\n")
    if not db.query(Grant).filter_by(document_id=shared.id, user_id=viewer.id, revoked_at=None).first():
        db.add(Grant(document_id=shared.id, user_id=viewer.id, permission="read", granted_by=owner.id))
        db.commit()
        audit.log(db, owner.id, "grant", shared.id, details="to=demo_viewer permission=read (seed)")
print("Seed complete.")