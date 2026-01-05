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
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.role import TenantRole
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


def create_test_token(
    user_id: str = "test-user-123", tenant_id: int | None = None, expired: bool = False
) -> str:
    """
    Generate valid JWT token for testing with multi-tenant support.

    Args:
        user_id: User ID to embed in 'sub' claim
        tenant_id: Tenant ID to embed in 'tenant_id' claim (required for multi-tenant)
        expired: If True, create expired token

    Returns:
        Encoded JWT token
    """
    if expired:
        exp = datetime.now(UTC) - timedelta(minutes=5)
    else:
        exp = datetime.now(UTC) + timedelta(minutes=15)

    payload = {"sub": user_id, "exp": exp, "iat": datetime.now(UTC)}

    # Add tenant_id if provided (required for multi-tenant endpoints)
    if tenant_id is not None:
        payload["tenant_id"] = str(tenant_id)

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


@pytest.fixture
def mock_jwt_token(shared_tenant):
    """Generate valid JWT token with tenant_id"""
    return create_test_token(tenant_id=shared_tenant.id)


@pytest.fixture
def auth_headers(shared_tenant, owner_membership):
    """
    Authorization headers for authenticated requests with OWNER permissions.

    This is the default fixture for most tests. It automatically:
    - Creates a shared tenant
    - Creates test-user-123 as OWNER
    - Returns auth headers with tenant_id
    """
    token = create_test_token(user_id="test-user-123", tenant_id=shared_tenant.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_a_headers(db_session, shared_tenant, user_a):
    """
    Authorization headers for user A with MEMBER permissions.

    For backward compatibility with existing tests. Auto-creates membership.
    """
    # Auto-create MEMBER membership for user A
    membership = TenantMembership(
        tenant_id=shared_tenant.id, user_id=user_a.id, role=TenantRole.MEMBER
    )
    db_session.add(membership)
    db_session.commit()
    token = create_test_token(user_id="user-a", tenant_id=shared_tenant.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_b_headers(db_session, shared_tenant, user_b):
    """
    Authorization headers for user B with MEMBER permissions.

    For backward compatibility with existing tests. Auto-creates membership.
    """
    # Auto-create MEMBER membership for user B
    membership = TenantMembership(
        tenant_id=shared_tenant.id, user_id=user_b.id, role=TenantRole.MEMBER
    )
    db_session.add(membership)
    db_session.commit()
    token = create_test_token(user_id="user-b", tenant_id=shared_tenant.id)
    return {"Authorization": f"Bearer {token}"}


# ============= Multi-Tenant Test Fixtures =============


@pytest.fixture
def shared_tenant(db_session):
    """Create a shared tenant for tests"""
    tenant = Tenant(name="Test Shared Tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def test_user(db_session):
    """Create test user (test-user-123)"""
    user = User(auth_user_id="test-user-123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_a(db_session):
    """Create user A"""
    user = User(auth_user_id="user-a")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_b(db_session):
    """Create user B"""
    user = User(auth_user_id="user-b")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def owner_membership(db_session, shared_tenant, test_user):
    """Create OWNER membership for test user"""
    membership = TenantMembership(
        tenant_id=shared_tenant.id, user_id=test_user.id, role=TenantRole.OWNER
    )
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture
def member_membership(db_session, shared_tenant, test_user):
    """Create MEMBER membership for test user"""
    membership = TenantMembership(
        tenant_id=shared_tenant.id, user_id=test_user.id, role=TenantRole.MEMBER
    )
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture
def viewer_membership(db_session, shared_tenant, test_user):
    """Create VIEWER membership for test user"""
    membership = TenantMembership(
        tenant_id=shared_tenant.id, user_id=test_user.id, role=TenantRole.VIEWER
    )
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture
def owner_headers(shared_tenant, owner_membership):
    """Authorization headers with OWNER permissions"""
    token = create_test_token(user_id="test-user-123", tenant_id=shared_tenant.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def member_headers(shared_tenant, member_membership):
    """Authorization headers with MEMBER permissions"""
    token = create_test_token(user_id="test-user-123", tenant_id=shared_tenant.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(shared_tenant, viewer_membership):
    """Authorization headers with VIEWER permissions (read-only)"""
    token = create_test_token(user_id="test-user-123", tenant_id=shared_tenant.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_a_owner_headers(db_session, shared_tenant, user_a):
    """Authorization headers for user A as OWNER"""
    membership = TenantMembership(
        tenant_id=shared_tenant.id, user_id=user_a.id, role=TenantRole.OWNER
    )
    db_session.add(membership)
    db_session.commit()
    token = create_test_token(user_id="user-a", tenant_id=shared_tenant.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_b_member_headers(db_session, shared_tenant, user_b):
    """Authorization headers for user B as MEMBER"""
    membership = TenantMembership(
        tenant_id=shared_tenant.id, user_id=user_b.id, role=TenantRole.MEMBER
    )
    db_session.add(membership)
    db_session.commit()
    token = create_test_token(user_id="user-b", tenant_id=shared_tenant.id)
    return {"Authorization": f"Bearer {token}"}


# ============= Cross-Tenant Isolation Test Fixtures =============


@pytest.fixture
def tenant_a(db_session):
    """Create separate tenant A for isolation testing"""
    tenant = Tenant(name="Tenant A")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def tenant_b(db_session):
    """Create separate tenant B for isolation testing"""
    tenant = Tenant(name="Tenant B")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def user_a_tenant_a_headers(db_session, tenant_a, user_a):
    """Authorization headers for user A in tenant A (MEMBER)"""
    membership = TenantMembership(
        tenant_id=tenant_a.id, user_id=user_a.id, role=TenantRole.MEMBER
    )
    db_session.add(membership)
    db_session.commit()
    token = create_test_token(user_id="user-a", tenant_id=tenant_a.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_b_tenant_b_headers(db_session, tenant_b, user_b):
    """Authorization headers for user B in tenant B (MEMBER)"""
    membership = TenantMembership(
        tenant_id=tenant_b.id, user_id=user_b.id, role=TenantRole.MEMBER
    )
    db_session.add(membership)
    db_session.commit()
    token = create_test_token(user_id="user-b", tenant_id=tenant_b.id)
    return {"Authorization": f"Bearer {token}"}