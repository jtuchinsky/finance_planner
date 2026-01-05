import pytest
from app.models.account import AccountType


class TestAccountCreation:
    """Tests for creating accounts"""

    def test_create_account_success(self, client, auth_headers):
        """User can create an account"""
        data = {
            "name": "Chase Checking",
            "account_type": "checking",
            "initial_balance": 1000.00,
        }

        response = client.post("/api/accounts", headers=auth_headers, json=data)

        assert response.status_code == 201
        account = response.json()
        assert account["name"] == "Chase Checking"
        assert account["account_type"] == "checking"
        assert account["balance"] == 1000.00
        assert "id" in account
        assert "created_at" in account

    def test_create_account_zero_balance(self, client, auth_headers):
        """Account can be created with zero balance"""
        data = {"name": "Savings", "account_type": "savings", "initial_balance": 0}

        response = client.post("/api/accounts", headers=auth_headers, json=data)

        assert response.status_code == 201
        assert response.json()["balance"] == 0.00

    def test_create_account_default_balance(self, client, auth_headers):
        """Account defaults to zero balance if not specified"""
        data = {"name": "Credit Card", "account_type": "credit_card"}

        response = client.post("/api/accounts", headers=auth_headers, json=data)

        assert response.status_code == 201
        assert response.json()["balance"] == 0.00

    def test_create_account_all_types(self, client, auth_headers):
        """All account types can be created"""
        types = ["checking", "savings", "credit_card", "investment", "loan", "other"]

        for account_type in types:
            data = {"name": f"Test {account_type}", "account_type": account_type}
            response = client.post("/api/accounts", headers=auth_headers, json=data)

            assert response.status_code == 201
            assert response.json()["account_type"] == account_type

    def test_create_account_missing_name(self, client, auth_headers):
        """Creating account without name should fail"""
        data = {"account_type": "checking"}

        response = client.post("/api/accounts", headers=auth_headers, json=data)

        assert response.status_code == 422  # Validation error

    def test_create_account_invalid_type(self, client, auth_headers):
        """Creating account with invalid type should fail"""
        data = {"name": "Test Account", "account_type": "invalid_type"}

        response = client.post("/api/accounts", headers=auth_headers, json=data)

        assert response.status_code == 422


class TestAccountRetrieval:
    """Tests for retrieving accounts"""

    def test_list_empty_accounts(self, client, auth_headers):
        """Listing accounts when none exist returns empty list"""
        response = client.get("/api/accounts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["accounts"] == []
        assert data["total"] == 0

    def test_list_user_accounts(self, client, auth_headers):
        """User can list their accounts"""
        # Create multiple accounts
        accounts_data = [
            {"name": "Checking", "account_type": "checking"},
            {"name": "Savings", "account_type": "savings"},
            {"name": "Investment", "account_type": "investment"},
        ]

        for data in accounts_data:
            client.post("/api/accounts", headers=auth_headers, json=data)

        # List accounts
        response = client.get("/api/accounts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["accounts"]) == 3

    def test_get_account_by_id(self, client, auth_headers):
        """User can retrieve specific account by ID"""
        # Create account
        create_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "My Account", "account_type": "checking"},
        )
        account_id = create_response.json()["id"]

        # Retrieve account
        response = client.get(f"/api/accounts/{account_id}", headers=auth_headers)

        assert response.status_code == 200
        account = response.json()
        assert account["id"] == account_id
        assert account["name"] == "My Account"

    def test_get_nonexistent_account(self, client, auth_headers):
        """Retrieving non-existent account returns 404"""
        response = client.get("/api/accounts/99999", headers=auth_headers)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestAccountUpdate:
    """Tests for updating accounts"""

    def test_update_account_name(self, client, auth_headers):
        """User can update account name"""
        # Create account
        create_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Old Name", "account_type": "checking"},
        )
        account_id = create_response.json()["id"]

        # Update name
        response = client.patch(
            f"/api/accounts/{account_id}", headers=auth_headers, json={"name": "New Name"}
        )

        assert response.status_code == 200
        account = response.json()
        assert account["name"] == "New Name"
        assert account["id"] == account_id

    def test_update_account_type(self, client, auth_headers):
        """User can update account type"""
        # Create account
        create_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "My Account", "account_type": "checking"},
        )
        account_id = create_response.json()["id"]

        # Update type
        response = client.patch(
            f"/api/accounts/{account_id}",
            headers=auth_headers,
            json={"account_type": "savings"},
        )

        assert response.status_code == 200
        assert response.json()["account_type"] == "savings"

    def test_update_account_partial(self, client, auth_headers):
        """Can update only some fields"""
        # Create account
        create_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Original", "account_type": "checking"},
        )
        account_id = create_response.json()["id"]

        # Update only name
        response = client.patch(
            f"/api/accounts/{account_id}", headers=auth_headers, json={"name": "Updated"}
        )

        account = response.json()
        assert account["name"] == "Updated"
        assert account["account_type"] == "checking"  # Unchanged

    def test_update_nonexistent_account(self, client, auth_headers):
        """Updating non-existent account returns 404"""
        response = client.patch(
            "/api/accounts/99999", headers=auth_headers, json={"name": "New Name"}
        )

        assert response.status_code == 404


class TestAccountDeletion:
    """Tests for deleting accounts"""

    def test_delete_account(self, client, auth_headers):
        """User can delete their account"""
        # Create account
        create_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "To Delete", "account_type": "checking"},
        )
        account_id = create_response.json()["id"]

        # Delete account
        response = client.delete(f"/api/accounts/{account_id}", headers=auth_headers)

        assert response.status_code == 204

        # Verify account is deleted
        get_response = client.get(f"/api/accounts/{account_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_nonexistent_account(self, client, auth_headers):
        """Deleting non-existent account returns 404"""
        response = client.delete("/api/accounts/99999", headers=auth_headers)

        assert response.status_code == 404


class TestMultiTenancy:
    """Critical tests for cross-tenant data isolation"""

    def test_users_see_only_own_accounts(self, client, user_a_tenant_a_headers, user_b_tenant_b_headers):
        """Users in different tenants should only see their own tenant's accounts"""
        # User A (Tenant A) creates accounts
        client.post(
            "/api/accounts",
            headers=user_a_tenant_a_headers,
            json={"name": "A's Checking", "account_type": "checking"},
        )
        client.post(
            "/api/accounts",
            headers=user_a_tenant_a_headers,
            json={"name": "A's Savings", "account_type": "savings"},
        )

        # User B (Tenant B) creates account
        client.post(
            "/api/accounts",
            headers=user_b_tenant_b_headers,
            json={"name": "B's Checking", "account_type": "checking"},
        )

        # User A should only see their tenant's 2 accounts
        response_a = client.get("/api/accounts", headers=user_a_tenant_a_headers)
        assert response_a.json()["total"] == 2

        # User B should only see their tenant's 1 account
        response_b = client.get("/api/accounts", headers=user_b_tenant_b_headers)
        assert response_b.json()["total"] == 1

    def test_user_cannot_access_other_user_account(self, client, user_a_tenant_a_headers, user_b_tenant_b_headers):
        """User in Tenant B cannot access Tenant A's account by ID"""
        # User A (Tenant A) creates account
        response_a = client.post(
            "/api/accounts",
            headers=user_a_tenant_a_headers,
            json={"name": "A's Account", "account_type": "checking"},
        )
        account_id = response_a.json()["id"]

        # User B (Tenant B) tries to access Tenant A's account
        response_b = client.get(f"/api/accounts/{account_id}", headers=user_b_tenant_b_headers)

        # Must return 404 (not 403) to avoid revealing account existence
        assert response_b.status_code == 404

    def test_user_cannot_update_other_user_account(self, client, user_a_tenant_a_headers, user_b_tenant_b_headers):
        """User in Tenant B cannot update Tenant A's account"""
        # User A (Tenant A) creates account
        response_a = client.post(
            "/api/accounts",
            headers=user_a_tenant_a_headers,
            json={"name": "A's Account", "account_type": "checking"},
        )
        account_id = response_a.json()["id"]

        # User B (Tenant B) tries to update Tenant A's account
        response_b = client.patch(
            f"/api/accounts/{account_id}",
            headers=user_b_tenant_b_headers,
            json={"name": "Hacked Name"},
        )

        assert response_b.status_code == 404

        # Verify account name unchanged
        response_a_check = client.get(f"/api/accounts/{account_id}", headers=user_a_tenant_a_headers)
        assert response_a_check.json()["name"] == "A's Account"

    def test_user_cannot_delete_other_user_account(self, client, user_a_tenant_a_headers, user_b_tenant_b_headers):
        """User in Tenant B cannot delete Tenant A's account"""
        # User A (Tenant A) creates account
        response_a = client.post(
            "/api/accounts",
            headers=user_a_tenant_a_headers,
            json={"name": "A's Account", "account_type": "checking"},
        )
        account_id = response_a.json()["id"]

        # User B (Tenant B) tries to delete Tenant A's account
        response_b = client.delete(f"/api/accounts/{account_id}", headers=user_b_tenant_b_headers)

        assert response_b.status_code == 404

        # Verify account still exists for User A
        response_a_check = client.get(f"/api/accounts/{account_id}", headers=user_a_tenant_a_headers)
        assert response_a_check.status_code == 200