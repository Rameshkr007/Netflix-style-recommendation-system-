"""
Shared pytest fixtures.

Each test gets a fresh, isolated SQLite database file (never the real
Postgres instance) so tests are fast, deterministic, and safe to run in CI
without any external services running.

IMPORTANT: because the app wires its SQLAlchemy engine at import time
(`app.core.database` reads settings.DATABASE_URL once, at module load),
and pytest runs many tests in a single process, we must fully evict every
`app.*` module from sys.modules between tests -- not just reload one
module -- otherwise later tests silently reuse the first test's engine
(pointed at an already-deleted temp file) via stale references held by
already-imported sibling modules (app.models.db_models, app.core.deps,
the route modules, etc).
"""
import os
import sys
import tempfile

import pytest


@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # Evict every previously-imported app module so this test builds a
    # completely fresh engine/app wired to the new DATABASE_URL.
    for mod_name in list(sys.modules):
        if mod_name == "app" or mod_name.startswith("app.") or mod_name.startswith("scripts."):
            del sys.modules[mod_name]

    from app.core.config import get_settings
    get_settings.cache_clear()

    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client

    os.remove(db_path)


@pytest.fixture()
def seeded_client(client):
    """A client whose database already has the sample catalog + ratings loaded."""
    from scripts.seed_database import seed
    seed()

    # the model was warmed up at startup *before* seeding -- refresh it now
    from app.core.database import SessionLocal
    from app.services.recommendation_service import RecommendationService

    db = SessionLocal()
    try:
        RecommendationService.get_instance().refresh(db)
    finally:
        db.close()

    return client
