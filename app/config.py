import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trustvault.db")
STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
SESSION_HOURS = int(os.getenv("SESSION_HOURS", 8))