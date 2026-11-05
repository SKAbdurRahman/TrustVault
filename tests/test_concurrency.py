import threading
import time
from app import audit
from app.db import SessionLocal
from app.models import AuditLog


def test_concurrent_audit_writes_do_not_fork_the_chain(monkeypatch):
    real = audit._compute_hash

    def slow(*args, **kwargs):
        time.sleep(0.02)  # widen the window between "read last row" and "commit"
        return real(*args, **kwargs)

    monkeypatch.setattr(audit, "_compute_hash", slow)
    errors = []

    def worker(i):
        try:
            with SessionLocal() as db:
                audit.log(db, i, "test_concurrent", details=str(i))
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(15)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    with SessionLocal() as db:
        assert db.query(AuditLog).count() == 15
        assert audit.verify_chain(db) == (True, None)