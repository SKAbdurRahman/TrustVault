from app.db import Base, engine
from app import models  # noqa: F401

Base.metadata.create_all(bind=engine)
if engine.dialect.name == "postgresql":
    with open("sql/audit_triggers.sql") as f:
        sql = f.read()
    with engine.begin() as conn:
        conn.exec_driver_sql("SET lock_timeout = '30s'")
        conn.exec_driver_sql(sql)
    print("Tables ready, audit triggers applied.")
else:
    print("Tables ready (no triggers on", engine.dialect.name + ").")