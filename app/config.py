import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trustvault.db")
STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
SESSION_HOURS = int(os.getenv("SESSION_HOURS", 8))

ALLOWED_TYPES = {
    "application/pdf": (b"%PDF-",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "text/plain": (),  # no magic bytes; checked as UTF-8 text instead
}