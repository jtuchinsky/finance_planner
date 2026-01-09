import pytest
from app.models.role import TenantRole
from tests.conftest import create_test_token


class TestListUserTenants:
    """Tests for GET /api/tenants (list all user's tenants)"""

    def test_list_user_tenants_single_tenant(self, client, db_session, test_user, shared_tenant, owner_membership):
        """User can list all tenants they belong to (single tenant case)"""
        # Create token WITHOUT tenant_id (this endpoint doesn't require tenant context)
        token = create_test_token(user_id="test-user-123")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/tenants", headers=headers)

        assert response.status_code == 200
        tenants = response.json()
        assert len(tenants) == 1
        assert tenants[0]["id"] == shared_tenant.id
        assert tenants[0]["name"] == "Test Shared Tenant"
        assert tenants[0]["role"] == TenantRole.OWNER
        assert "created_at" in tenants[0]
        assert "updated_at" in tenants[0]

    def test_list_user_tenants_multiple_tenants(self, client, db_session, test_user):
        """User can see all tenants they belong to (multiple tenants)"""
        from app.models.tenant import Tenant
        from app.models.tenant_membership import TenantMembership

        # Create three tenants
        tenant1 = Tenant(name="Personal Finances")
        tenant2 = Tenant(name="Family Budget")
        tenant3 = Tenant(name="Business Account")
        db_session.add_all([tenant1, tenant2, tenant3])
        db_session.commit()

        # Add user as member of all three with different roles
        membership1 = TenantMembership(tenant_id=tenant1.id, user_id=test_user.id, role=TenantRole.OWNER)
        membership2 = TenantMembership(tenant_id=tenant2.id, user_id=test_user.id, role=TenantRole.ADMIN)
        membership3 = TenantMembership(tenant_id=tenant3.id, user_id=test_user.id, role=TenantRole.MEMBER)
        db_session.add_all([membership1, membership2, membership3])
        db_session.commit()

        # Create token WITHOUT tenant_id
        token = create_test_token(user_id="test-user-123")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/tenants", headers=headers)

        assert response.status_code == 200
        tenants = response.json()
        assert len(tenants) == 3

        # Verify each tenant has correct role
        tenant_map = {t["name"]: t for t in tenants}
        assert tenant_map["Personal Finances"]["role"] == TenantRole.OWNER
        assert tenant_map["Family Budget"]["role"] == TenantRole.ADMIN
        assert tenant_map["Business Account"]["role"] == TenantRole.MEMBER

    def test_list_user_tenants_empty_list(self, client, db_session):
        """User with no tenant memberships gets empty list"""
        from app.models.user import User

        # Create user with no tenant memberships
        new_user = User(auth_user_id="user-no-tenants")
        db_session.add(new_user)
        db_session.commit()

        token = create_test_token(user_id="user-no-tenants")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/tenants", headers=headers)

        assert response.status_code == 200
        tenants = response.json()
        assert len(tenants) == 0
        assert tenants == []

    def test_list_user_tenants_requires_auth(self, client):
        """Endpoint requires authentication"""
        response = client.get("/api/tenants")
        assert response.status_code == 401


class TestGetCurrentTenant:
    """Tests for GET /api/tenants/me"""

    def test_get_current_tenant_success(self, client, auth_headers, shared_tenant):
        """User can view their current tenant details"""
        response = client.get("/api/tenants/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == shared_tenant.id
        assert data["name"] == "Test Shared Tenant"
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_current_tenant_requires_auth(self, client):
        """Endpoint requires authentication"""
        response = client.get("/api/tenants/me")
        assert response.status_code == 401


class TestUpdateTenant:
    """Tests for PATCH /api/tenants/me"""

    def test_update_tenant_name_as_owner(self, client, owner_headers, shared_tenant):
        """Owner can update tenant name"""
        response = client.patch(
            "/api/tenants/me",
            headers=owner_headers,
            json={"name": "Updated Tenant Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Tenant Name"
        assert data["id"] == shared_tenant.id

    def test_update_tenant_name_as_member_forbidden(
        self, client, member_headers, shared_tenant
    ):
        """Member cannot update tenant name"""
        response = client.patch(
            "/api/tenants/me",
            headers=member_headers,
            json={"name": "Hacked Name"},
        )

        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()

    def test_update_tenant_name_as_viewer_forbidden(
        self, client, viewer_headers, shared_tenant
    ):
        """Viewer cannot update tenant name"""
        response = client.patch(
            "/api/tenants/me",
            headers=viewer_headers,
            json={"name": "Hacked Name"},
        )

        assert response.status_code == 403


class TestListMembers:
    """Tests for GET /api/tenants/me/members"""

    def test_list_members_as_owner(
        self, client, owner_headers, shared_tenant, owner_membership
    ):
        """Owner can list all members"""
        response = client.get("/api/tenants/me/members", headers=owner_headers)

        assert response.status_code == 200
        members = response.json()
        assert len(members) == 1
        assert members[0]["auth_user_id"] == "test-user-123"
        assert members[0]["role"] == TenantRole.OWNER

    def test_list_members_as_member(
        self, client, member_headers, shared_tenant, member_membership
    ):
        """Member can list all members"""
        response = client.get("/api/tenants/me/members", headers=member_headers)

        assert response.status_code == 200
        members = response.json()
        assert len(members) >= 1

    def test_list_members_as_viewer(
        self, client, viewer_headers, shared_tenant, viewer_membership
    ):
        """Viewer can list all members"""
        response = client.get("/api/tenants/me/members", headers=viewer_headers)

        assert response.status_code == 200
        members = response.json()
        assert len(members) >= 1


class TestInviteMember:
    """Tests for POST /api/tenants/me/members"""

    def test_invite_member_as_owner(
        self, client, owner_headers, shared_tenant, owner_membership
    ):
        """Owner can invite new members"""
        response = client.post(
            "/api/tenants/me/members",
            headers=owner_headers,
            json={"auth_user_id": "new-user-456", "role": "member"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["auth_user_id"] == "new-user-456"
        assert data["role"] == TenantRole.MEMBER
        assert "id" in data
        assert "user_id" in data

    def test_invite_member_as_admin(
        self, client, db_session, shared_tenant, test_user
    ):
        """Admin can invite new members"""
        # Create admin membership
        from app.models.tenant_membership import TenantMembership

        membership = TenantMembership(
            tenant_id=shared_tenant.id, user_id=test_user.id, role=TenantRole.ADMIN
        )
        db_session.add(membership)
        db_session.commit()

        from tests.conftest import create_test_token

        admin_token = create_test_token(
            user_id="test-user-123", tenant_id=shared_tenant.id
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            "/api/tenants/me/members",
            headers=admin_headers,
            json={"auth_user_id": "new-user-789", "role": "viewer"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["auth_user_id"] == "new-user-789"
        assert data["role"] == TenantRole.VIEWER

    def test_invite_member_as_member_forbidden(
        self, client, member_headers, shared_tenant, member_membership
    ):
        """Member cannot invite new members"""
        response = client.post(
            "/api/tenants/me/members",
            headers=member_headers,
            json={"auth_user_id": "new-user-999"},
        )

        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    def test_invite_member_as_viewer_forbidden(
        self, client, viewer_headers, shared_tenant, viewer_membership
    ):
        """Viewer cannot invite new members"""
        response = client.post(
            "/api/tenants/me/members",
            headers=viewer_headers,
            json={"auth_user_id": "new-user-888"},
        )

        assert response.status_code == 403

    def test_invite_duplicate_member_fails(
        self, client, owner_headers, shared_tenant, owner_membership
    ):
        """Cannot invite a user who is already a member"""
        # First invite
        client.post(
            "/api/tenants/me/members",
            headers=owner_headers,
            json={"auth_user_id": "duplicate-user"},
        )

        # Try to invite again
        response = client.post(
            "/api/tenants/me/members",
            headers=owner_headers,
            json={"auth_user_id": "duplicate-user"},
        )

        assert response.status_code == 400
        assert "already a member" in response.json()["detail"].lower()

    def test_admin_cannot_invite_as_owner(
        self, client, db_session, shared_tenant, test_user
    ):
        """Admin cannot invite someone as OWNER"""
        # Create admin membership
        from app.models.tenant_membership import TenantMembership

        membership = TenantMembership(
            tenant_id=shared_tenant.id, user_id=test_user.id, role=TenantRole.ADMIN
        )
        db_session.add(membership)
        db_session.commit()

        from tests.conftest import create_test_token

        admin_token = create_test_token(
            user_id="test-user-123", tenant_id=shared_tenant.id
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            "/api/tenants/me/members",
            headers=admin_headers,
            json={"auth_user_id": "new-owner", "role": "owner"},
        )

        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()

    def test_owner_can_invite_as_owner(
        self, client, owner_headers, shared_tenant, owner_membership
    ):
        """Owner can invite someone as OWNER"""
        response = client.post(
            "/api/tenants/me/members",
            headers=owner_headers,
            json={"auth_user_id": "new-owner-user", "role": "owner"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == TenantRole.OWNER


class TestUpdateMemberRole:
    """Tests for PATCH /api/tenants/me/members/{user_id}/role"""

    def test_owner_can_change_member_role(
        self, client, owner_headers, db_session, shared_tenant, user_a
    ):
        """Owner can change member's role"""
        # Create member membership for user_a
        from app.models.tenant_membership import TenantMembership

        membership = TenantMembership(
            tenant_id=shared_tenant.id, user_id=user_a.id, role=TenantRole.MEMBER
        )
        db_session.add(membership)
        db_session.commit()

        response = client.patch(
            f"/api/tenants/me/members/{user_a.id}/role",
            headers=owner_headers,
            json={"role": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == TenantRole.ADMIN
        assert data["user_id"] == user_a.id

    def test_owner_cannot_change_owner_role(
        self, client, owner_headers, db_session, shared_tenant, user_a
    ):
        """Owner cannot change another owner's role"""
        # Create owner membership for user_a
        from app.models.tenant_membership import TenantMembership

        membership = TenantMembership(
            tenant_id=shared_tenant.id, user_id=user_a.id, role=TenantRole.OWNER
        )
        db_session.add(membership)
        db_session.commit()

        response = client.patch(
            f"/api/tenants/me/members/{user_a.id}/role",
            headers=owner_headers,
            json={"role": "member"},
        )

        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()

    def test_member_cannot_change_role(
        self, client, member_headers, db_session, shared_tenant, user_a
    ):
        """Member cannot change roles"""
        # Create viewer membership for user_a
        from app.models.tenant_membership import TenantMembership

        membership = TenantMembership(
            tenant_id=shared_tenant.id, user_id=user_a.id, role=TenantRole.VIEWER
        )
        db_session.add(membership)
        db_session.commit()

        response = client.patch(
            f"/api/tenants/me/members/{user_a.id}/role",
            headers=member_headers,
            json={"role": "admin"},
        )

        assert response.status_code == 403

    def test_owner_cannot_change_own_role(
        self, client, owner_headers, shared_tenant, test_user
    ):
        """Owner cannot change their own role"""
        response = client.patch(
            f"/api/tenants/me/members/{test_user.id}/role",
            headers=owner_headers,
            json={"role": "member"},
        )

        assert response.status_code == 403
        assert "own role" in response.json()["detail"].lower()


class TestRemoveMember:
    """Tests for DELETE /api/tenants/me/members/{user_id}"""

    def test_owner_can_remove_member(
        self, client, owner_headers, db_session, shared_tenant, user_a
    ):
        """Owner can remove members"""
        # Create member membership for user_a
        from app.models.tenant_membership import TenantMembership

        membership = TenantMembership(
            tenant_id=shared_tenant.id, user_id=user_a.id, role=TenantRole.MEMBER
        )
        db_session.add(membership)
        db_session.commit()

        response = client.delete(
            f"/api/tenants/me/members/{user_a.id}", headers=owner_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "removed successfully" in data["message"].lower()
        assert data["removed_user_id"] == user_a.id

        # Verify member is removed
        members_response = client.get("/api/tenants/me/members", headers=owner_headers)
        members = members_response.json()
        assert not any(m["user_id"] == user_a.id for m in members)

    def test_admin_can_remove_member(
        self, client, db_session, shared_tenant, test_user, user_a
    ):
        """Admin can remove members"""
        # Create admin membership
        from app.models.tenant_membership import TenantMembership

        admin_membership = TenantMembership(
            tenant_id=shared_tenant.id, user_id=test_user.id, role=TenantRole.ADMIN
        )
        db_session.add(admin_membership)

        # Create member membership for user_a
        member_membership = TenantMembership(
            tenant_id=shared_tenant.id, user_id=user_a.id, role=TenantRole.MEMBER
        )
        db_session.add(member_membership)
        db_session.commit()

        from tests.conftest import create_test_token

        admin_token = create_test_token(
            user_id="test-user-123", tenant_id=shared_tenant.id
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.delete(
            f"/api/tenants/me/members/{user_a.id}", headers=admin_headers
        )

        assert response.status_code == 200

    def test_member_cannot_remove_member(
        self, client, member_headers, db_session, shared_tenant, user_a
    ):
        """Member cannot remove other members"""
        # Create viewer membership for user_a
        from app.models.tenant_membership import TenantMembership

        membership = TenantMembership(
            tenant_id=shared_tenant.id, user_id=user_a.id, role=TenantRole.VIEWER
        )
        db_session.add(membership)
        db_session.commit()

        response = client.delete(
            f"/api/tenants/me/members/{user_a.id}", headers=member_headers
        )

        assert response.status_code == 403

    def test_cannot_remove_owner(
        self, client, owner_headers, db_session, shared_tenant, user_a
    ):
        """Cannot remove owner from tenant"""
        # Create owner membership for user_a
        from app.models.tenant_membership import TenantMembership

        membership = TenantMembership(
            tenant_id=shared_tenant.id, user_id=user_a.id, role=TenantRole.OWNER
        )
        db_session.add(membership)
        db_session.commit()

        response = client.delete(
            f"/api/tenants/me/members/{user_a.id}", headers=owner_headers
        )

        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()

    def test_cannot_remove_self(
        self, client, owner_headers, shared_tenant, test_user
    ):
        """User cannot remove themselves"""
        response = client.delete(
            f"/api/tenants/me/members/{test_user.id}", headers=owner_headers
        )

        assert response.status_code == 403
        assert "yourself" in response.json()["detail"].lower()
