from fastapi import FastAPI
from app.db import Base, engine
from app import models  # noqa: F401  (registers the tables)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrustVault")


@app.get("/health")
def health():
    return {"status": "ok"}