import pytest
from datetime import datetime, timedelta, UTC
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from jose import jwt

from app.database import get_db
from app.models.base import Base
from app.config import settings
# Import all model classes to ensure they're registered with SQLAlchemy
from app.models.user import User
from app.models.account import Account
from app.models.transaction import Transaction
# Import FastAPI app AFTER model imports
from app.main import app

# Test database (SQLite in-memory for speed)
# Use StaticPool to ensure all connections share the same in-memory database
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with test database"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_test_token(user_id: str = "test-user-123", expired: bool = False) -> str:
    """
    Generate valid JWT token for testing.

    Args:
        user_id: User ID to embed in 'sub' claim
        expired: If True, create expired token

    Returns:
        Encoded JWT token
    """
    if expired:
        exp = datetime.now(UTC) - timedelta(minutes=5)
    else:
        exp = datetime.now(UTC) + timedelta(minutes=15)

    payload = {"sub": user_id, "exp": exp, "iat": datetime.now(UTC)}

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


@pytest.fixture
def mock_jwt_token():
    """Generate valid JWT token"""
    return create_test_token()


@pytest.fixture
def auth_headers(mock_jwt_token):
    """Authorization headers for authenticated requests"""
    return {"Authorization": f"Bearer {mock_jwt_token}"}


@pytest.fixture
def user_a_headers():
    """Authorization headers for user A"""
    token = create_test_token(user_id="user-a")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_b_headers():
    """Authorization headers for user B"""
    token = create_test_token(user_id="user-b")
    return {"Authorization": f"Bearer {token}"}