from fastapi import FastAPI
from app.db import Base, engine
from app import models  # noqa: F401  (registers the tables)
from app.routes import auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrustVault")
app.include_router(auth.router)


@app.get("/health")
def health():
    return {"status": "ok"}