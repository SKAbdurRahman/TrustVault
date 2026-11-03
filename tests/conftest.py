import os
os.environ["DATABASE_URL"] = "sqlite:///./test_trustvault.db"  # never touch the real database

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)