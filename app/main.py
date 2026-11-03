from fastapi import FastAPI
from app.db import Base, engine
from app import models  # noqa: F401  (registers the tables)
from app.routes import auth, documents, grants
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrustVault")
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(grants.router)


@app.get("/health")
def health():
    return {"status": "ok"}