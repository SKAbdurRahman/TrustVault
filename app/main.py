import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from app.db import Base, engine
from app import models  # noqa: F401  (registers the tables)
from app.routes import auth, documents, grants, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrustVault")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(grants.router)
app.include_router(admin.router)

INDEX_HTML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root():
    if os.path.isfile(INDEX_HTML_PATH):
        return FileResponse(INDEX_HTML_PATH, media_type="text/html")
    return RedirectResponse(url="/docs")