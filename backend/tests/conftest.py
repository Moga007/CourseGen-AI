"""
Fixtures partagées pour tous les tests CourseGen AI.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ajoute le dossier backend au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="function")
def db_session():
    """Session SQLite in-memory isolée pour chaque test.

    StaticPool + check_same_thread=False sont indispensables :
    TestClient exécute les routes dans un thread différent de celui du fixture,
    et SQLite interdit par défaut l'usage cross-thread d'une même connexion.
    """
    from database import Base

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,   # force le partage de la même connexion entre threads
    )
    Base.metadata.create_all(test_engine)
    TestSession = sessionmaker(bind=test_engine)

    db = TestSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Client FastAPI avec base de données de test injectée."""
    from main import app
    from database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()
