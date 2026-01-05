import pytest
from datetime import datetime, timedelta, UTC
from jose import jwt
from app.config import settings
from tests.conftest import create_test_token


def test_health_endpoint_no_auth(client):
    """Health endpoint should not require authentication"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint_no_auth(client):
    """Root endpoint should not require authentication"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_valid_token_accepted(client, auth_headers):
    """Valid JWT token should be accepted"""
    response = client.get("/api/accounts", headers=auth_headers)
    # 200 OK with empty list (no accounts yet)
    assert response.status_code == 200
    assert response.json()["accounts"] == []


def test_missing_token_rejected(client):
    """Request without Authorization header should return 401"""
    response = client.get("/api/accounts")
    assert response.status_code == 401  # HTTPBearer returns 401 for missing header


def test_expired_token_rejected(client):
    """Expired tokens should return 401"""
    expired_token = create_test_token(expired=True)
    headers = {"Authorization": f"Bearer {expired_token}"}

    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 401
    assert "detail" in response.json()


def test_invalid_signature_rejected(client):
    """Tokens signed with wrong key should fail"""
    payload = {"sub": "test-user", "exp": datetime.now(UTC) + timedelta(minutes=15)}
    token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 401


def test_malformed_token_rejected(client):
    """Malformed tokens should return 401"""
    headers = {"Authorization": "Bearer not-a-valid-jwt-token"}
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 401


def test_missing_sub_claim_rejected(client):
    """Token without 'sub' claim should be rejected"""
    payload = {"exp": datetime.now(UTC) + timedelta(minutes=15), "iat": datetime.now(UTC)}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 401
    assert "user identifier" in response.json()["detail"].lower()


def test_missing_exp_claim_rejected(client):
    """Token without 'exp' claim should be rejected"""
    payload = {"sub": "test-user", "iat": datetime.now(UTC)}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 401
    assert "expiration" in response.json()["detail"].lower()


def test_bearer_prefix_required(client):
    """Authorization header must have 'Bearer' prefix"""
    token = create_test_token()
    # Missing 'Bearer' prefix
    headers = {"Authorization": token}

    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 401  # HTTPBearer validation


def test_user_auto_created_on_first_request(client, db_session):
    """User record should be auto-created on first API request"""
    from app.models.user import User
    from app.models.tenant import Tenant
    from app.models.tenant_membership import TenantMembership
    from app.models.role import TenantRole

    # Verify no users exist
    assert db_session.query(User).count() == 0

    # Create a tenant first (required for multi-tenant system)
    tenant = Tenant(name="Test Tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    # Make first request with tenant_id in token
    token = create_test_token(user_id="new-user-123", tenant_id=tenant.id)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/accounts", headers=headers)

    # Will fail with 403 because user doesn't have membership yet
    assert response.status_code == 403

    # Verify user was auto-created even though membership check failed
    user = db_session.query(User).filter_by(auth_user_id="new-user-123").first()
    assert user is not None

    # Now create membership manually and try again
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        role=TenantRole.MEMBER
    )
    db_session.add(membership)
    db_session.commit()

    # Now request should succeed
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 200


def test_same_user_not_duplicated(client, db_session):
    """Multiple requests from same user should not create duplicates"""
    from app.models.user import User
    from app.models.tenant import Tenant
    from app.models.tenant_membership import TenantMembership
    from app.models.role import TenantRole

    # Create tenant and user with membership
    tenant = Tenant(name="Test Tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    token = create_test_token(user_id="same-user", tenant_id=tenant.id)
    headers = {"Authorization": f"Bearer {token}"}

    # First request will auto-create user but fail on membership check
    client.get("/api/accounts", headers=headers)

    # Verify user was created
    user = db_session.query(User).filter_by(auth_user_id="same-user").first()
    assert user is not None

    # Create membership
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        role=TenantRole.MEMBER
    )
    db_session.add(membership)
    db_session.commit()

    # Make multiple requests
    client.get("/api/accounts", headers=headers)
    client.get("/api/accounts", headers=headers)
    client.get("/api/accounts", headers=headers)

    # Should only have one user
    users = db_session.query(User).all()
    assert len(users) == 1
    assert users[0].auth_user_id == "same-user"