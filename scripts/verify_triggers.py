import os
import sys
from sqlalchemy import create_engine, text

url = os.getenv("VERIFY_DB_URL")
if not url:
    sys.exit("Set VERIFY_DB_URL to the External Database URL")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg2://", 1)
elif url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(url)
for label, sql in [("UPDATE", "UPDATE audit_log SET details = 'x' WHERE id = 1"),
                   ("DELETE", "DELETE FROM audit_log WHERE id = 1"),
                   ("TRUNCATE", "TRUNCATE audit_log")]:
    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
        print(label, "-> SUCCEEDED (triggers are NOT working)")
    except Exception as e:
        first_line = str(e.orig).splitlines()[0] if getattr(e, "orig", None) else str(e)[:80]
        print(label, "-> rejected:", first_line)