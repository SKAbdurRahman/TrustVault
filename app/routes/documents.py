import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app import audit
from app.config import ALLOWED_TYPES, MAX_UPLOAD_BYTES, STORAGE_DIR
from app.db import get_db
from app.models import Document, Grant, User, now
from app.permissions import require
from app.security import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])
DocId = Path(ge=1, le=2147483647)

def _detect_type(data: bytes) -> Optional[str]:
    """Decide the type from the content itself. The client's claim is ignored."""
    for ctype, signatures in ALLOWED_TYPES.items():
        if signatures and any(data.startswith(s) for s in signatures):
            return ctype
    try:
        data.decode("utf-8")
        if b"\x00" not in data:
            return "text/plain"
    except UnicodeDecodeError:
        pass
    return None


def _safe_display_name(name: str) -> str:
    """Only for showing the name back. Never used as a path on disk."""
    base = os.path.basename((name or "file").replace("\\", "/"))
    cleaned = "".join(c for c in base if c.isprintable() and c not in '<>:"|?*')
    return cleaned[:255] or "file"


def _doc_out(d: Document) -> dict:
    return {"id": d.id, "title": d.title, "category": d.category, "owner_id": d.owner_id,
            "owner_username": d.owner.username,
            "original_name": d.original_name, "content_type": d.content_type,
            "size": d.size, "created_at": d.created_at.isoformat()}


@router.post("", status_code=201)
async def upload(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=200),
    category: str = Form("general", max_length=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = await file.read(MAX_UPLOAD_BYTES + 1)  # never read more than the limit + 1 byte
    if len(data) > MAX_UPLOAD_BYTES:
        audit.log(db, user.id, "upload", result="refused", details="file too large")
        raise HTTPException(status_code=413, detail="File too large")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    ctype = _detect_type(data)
    if ctype is None:
        audit.log(db, user.id, "upload", result="refused", details="type not allowed")
        raise HTTPException(status_code=415, detail="File type not allowed")

    stored_name = uuid.uuid4().hex  # random; the user's file name never touches the disk path
    os.makedirs(STORAGE_DIR, exist_ok=True)
    with open(os.path.join(STORAGE_DIR, stored_name), "wb") as f:
        f.write(data)

    doc = Document(owner_id=user.id, title=title.strip(), category=category.strip() or "general",
                   stored_name=stored_name, original_name=_safe_display_name(file.filename),
                   content_type=ctype, size=len(data))
    db.add(doc)
    db.commit()
    audit.log(db, user.id, "upload", doc.id, details=f"{ctype}, {len(data)} bytes")
    return _doc_out(doc)


@router.get("")
def list_documents(
    q: Optional[str] = None,
    owner_id: Optional[int] = None,
    category: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Only documents this user may read can ever appear, so search cannot leak titles."""
    granted_ids = db.query(Grant.document_id).filter(
        Grant.user_id == user.id,
        Grant.revoked_at.is_(None),
        or_(Grant.expires_at.is_(None), Grant.expires_at > now()),
    )
    query = db.query(Document).filter(
        Document.deleted_at.is_(None),
        or_(Document.owner_id == user.id, Document.id.in_(granted_ids)),
    )
    if q:
        query = query.filter(Document.title.ilike(f"%{q}%"))
    if owner_id is not None:
        query = query.filter(Document.owner_id == owner_id)
    if category:
        query = query.filter(Document.category == category)
    return [_doc_out(d) for d in query.order_by(Document.id.desc()).limit(200)]


@router.get("/{doc_id}")
def get_document(doc_id: int = DocId, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = require(db, user, doc_id, "read")
    audit.log(db, user.id, "read", doc.id)
    return _doc_out(doc)


@router.get("/{doc_id}/download")
def download(doc_id: int = DocId, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = require(db, user, doc_id, "download")
    path = os.path.join(STORAGE_DIR, doc.stored_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Document not found")
    audit.log(db, user.id, "download", doc.id)  # logged BEFORE the bytes leave the server
    return FileResponse(path, media_type=doc.content_type, filename=doc.original_name,
                        headers={"X-Content-Type-Options": "nosniff"})

@router.patch("/{doc_id}")
def edit_document(doc_id: int = DocId, title: Optional[str] = Form(None, max_length=200),
                  category: Optional[str] = Form(None, max_length=50),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = require(db, user, doc_id, "edit")
    changes = []
    if title is not None and title.strip():
        doc.title = title.strip()
        changes.append("title")
    if category is not None and category.strip():
        doc.category = category.strip()
        changes.append("category")
    db.commit()
    audit.log(db, user.id, "edit", doc.id, details=",".join(changes) or "no change")
    return _doc_out(doc)


@router.delete("/{doc_id}")
def delete_document(doc_id: int = DocId, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = require(db, user, doc_id, "delete")  # owner only
    doc.deleted_at = now()  # soft delete: the file and the audit trail stay
    db.commit()
    audit.log(db, user.id, "delete", doc.id)
    return {"status": "deleted"}