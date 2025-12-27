import pytest
from datetime import date, timedelta


class TestTransactionCreation:
    """Tests for creating transactions"""

    def test_create_transaction_success(self, client, auth_headers):
        """User can create a transaction"""
        # Create account first
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking", "initial_balance": 1000.00},
        )
        account_id = account_response.json()["id"]

        # Create transaction
        transaction_data = {
            "account_id": account_id,
            "amount": -50.00,
            "date": str(date.today()),
            "category": "groceries",
            "description": "Weekly shopping",
            "merchant": "Whole Foods",
            "location": "Seattle, WA",
            "tags": ["food", "essentials"],
        }
        response = client.post("/api/transactions", headers=auth_headers, json=transaction_data)

        assert response.status_code == 201
        transaction = response.json()
        assert transaction["amount"] == -50.00
        assert transaction["category"] == "groceries"
        assert transaction["merchant"] == "Whole Foods"
        assert transaction["tags"] == ["food", "essentials"]
        assert "id" in transaction

    def test_create_transaction_updates_balance(self, client, auth_headers):
        """Creating transaction updates account balance correctly"""
        # Create account with initial balance
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking", "initial_balance": 1000.00},
        )
        account_id = account_response.json()["id"]

        # Create expense transaction
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account_id,
                "amount": -50.00,
                "date": str(date.today()),
                "category": "groceries",
            },
        )

        # Check account balance
        account_response = client.get(f"/api/accounts/{account_id}", headers=auth_headers)
        assert account_response.json()["balance"] == 950.00

    def test_create_transaction_minimal_fields(self, client, auth_headers):
        """Transaction can be created with minimal required fields"""
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking"},
        )
        account_id = account_response.json()["id"]

        transaction_data = {
            "account_id": account_id,
            "amount": 100.00,
            "date": str(date.today()),
            "category": "income",
        }
        response = client.post("/api/transactions", headers=auth_headers, json=transaction_data)

        assert response.status_code == 201
        assert response.json()["amount"] == 100.00

    def test_create_transaction_invalid_account(self, client, auth_headers):
        """Creating transaction with invalid account_id returns 404"""
        transaction_data = {
            "account_id": 99999,
            "amount": 50.00,
            "date": str(date.today()),
            "category": "test",
        }
        response = client.post("/api/transactions", headers=auth_headers, json=transaction_data)

        assert response.status_code == 404

    def test_create_transaction_other_user_account(self, client, user_a_headers, user_b_headers):
        """Cannot create transaction for another user's account"""
        # User A creates account
        account_response = client.post(
            "/api/accounts",
            headers=user_a_headers,
            json={"name": "User A Account", "account_type": "checking"},
        )
        account_id = account_response.json()["id"]

        # User B tries to create transaction in User A's account
        transaction_data = {
            "account_id": account_id,
            "amount": 50.00,
            "date": str(date.today()),
            "category": "test",
        }
        response = client.post("/api/transactions", headers=user_b_headers, json=transaction_data)

        assert response.status_code == 404


class TestTransactionRetrieval:
    """Tests for retrieving transactions"""

    def test_list_empty_transactions(self, client, auth_headers):
        """Listing transactions when none exist returns empty list"""
        response = client.get("/api/transactions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["transactions"] == []
        assert data["total"] == 0

    def test_list_transactions(self, client, auth_headers):
        """User can list their transactions"""
        # Create account
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking"},
        )
        account_id = account_response.json()["id"]

        # Create multiple transactions
        for i in range(3):
            client.post(
                "/api/transactions",
                headers=auth_headers,
                json={
                    "account_id": account_id,
                    "amount": float(i * 10),
                    "date": str(date.today()),
                    "category": "test",
                },
            )

        # List transactions
        response = client.get("/api/transactions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["transactions"]) == 3

    def test_get_transaction_by_id(self, client, auth_headers):
        """User can retrieve specific transaction by ID"""
        # Create account and transaction
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking"},
        )
        account_id = account_response.json()["id"]

        create_response = client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account_id,
                "amount": 50.00,
                "date": str(date.today()),
                "category": "test",
            },
        )
        transaction_id = create_response.json()["id"]

        # Retrieve transaction
        response = client.get(f"/api/transactions/{transaction_id}", headers=auth_headers)

        assert response.status_code == 200
        transaction = response.json()
        assert transaction["id"] == transaction_id
        assert transaction["amount"] == 50.00

    def test_get_nonexistent_transaction(self, client, auth_headers):
        """Retrieving non-existent transaction returns 404"""
        response = client.get("/api/transactions/99999", headers=auth_headers)

        assert response.status_code == 404

    def test_filter_by_account(self, client, auth_headers):
        """Can filter transactions by account_id"""
        # Create two accounts
        account1 = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Account 1", "account_type": "checking"},
        ).json()
        account2 = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Account 2", "account_type": "savings"},
        ).json()

        # Create transactions in both accounts
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account1["id"],
                "amount": 100.00,
                "date": str(date.today()),
                "category": "test",
            },
        )
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account2["id"],
                "amount": 200.00,
                "date": str(date.today()),
                "category": "test",
            },
        )

        # Filter by account1
        response = client.get(
            f"/api/transactions?account_id={account1['id']}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["transactions"][0]["account_id"] == account1["id"]

    def test_filter_by_date_range(self, client, auth_headers):
        """Can filter transactions by date range"""
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking"},
        )
        account_id = account_response.json()["id"]

        # Create transactions on different dates
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        for transaction_date in [week_ago, yesterday, today]:
            client.post(
                "/api/transactions",
                headers=auth_headers,
                json={
                    "account_id": account_id,
                    "amount": 50.00,
                    "date": str(transaction_date),
                    "category": "test",
                },
            )

        # Filter for last 3 days
        start_date = today - timedelta(days=3)
        response = client.get(
            f"/api/transactions?start_date={start_date}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # yesterday and today

    def test_filter_by_category(self, client, auth_headers):
        """Can filter transactions by category"""
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking"},
        )
        account_id = account_response.json()["id"]

        # Create transactions with different categories
        for category in ["groceries", "groceries", "entertainment"]:
            client.post(
                "/api/transactions",
                headers=auth_headers,
                json={
                    "account_id": account_id,
                    "amount": 50.00,
                    "date": str(date.today()),
                    "category": category,
                },
            )

        # Filter by groceries
        response = client.get("/api/transactions?category=groceries", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_filter_by_merchant(self, client, auth_headers):
        """Can filter transactions by merchant (partial match)"""
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking"},
        )
        account_id = account_response.json()["id"]

        # Create transactions
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account_id,
                "amount": 50.00,
                "date": str(date.today()),
                "category": "groceries",
                "merchant": "Whole Foods Market",
            },
        )
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account_id,
                "amount": 30.00,
                "date": str(date.today()),
                "category": "groceries",
                "merchant": "Safeway",
            },
        )

        # Filter by "Whole" (partial match)
        response = client.get("/api/transactions?merchant=Whole", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "Whole Foods" in data["transactions"][0]["merchant"]

    def test_filter_by_tags(self, client, auth_headers):
        """Can filter transactions by tags"""
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking"},
        )
        account_id = account_response.json()["id"]

        # Create transactions with different tags
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account_id,
                "amount": 50.00,
                "date": str(date.today()),
                "category": "groceries",
                "tags": ["food", "essentials"],
            },
        )
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account_id,
                "amount": 30.00,
                "date": str(date.today()),
                "category": "entertainment",
                "tags": ["leisure", "movies"],
            },
        )

        # Filter by "food" tag
        response = client.get("/api/transactions?tags=food", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_pagination(self, client, auth_headers):
        """Pagination works correctly"""
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking"},
        )
        account_id = account_response.json()["id"]

        # Create 10 transactions
        for i in range(10):
            client.post(
                "/api/transactions",
                headers=auth_headers,
                json={
                    "account_id": account_id,
                    "amount": float(i),
                    "date": str(date.today()),
                    "category": "test",
                },
            )

        # Get first page (5 items)
        response = client.get("/api/transactions?limit=5&offset=0", headers=auth_headers)
        assert response.json()["total"] == 10
        assert len(response.json()["transactions"]) == 5

        # Get second page (5 items)
        response = client.get("/api/transactions?limit=5&offset=5", headers=auth_headers)
        assert len(response.json()["transactions"]) == 5


class TestTransactionUpdate:
    """Tests for updating transactions"""

    def test_update_transaction_amount(self, client, auth_headers):
        """Updating transaction amount recalculates account balance"""
        # Create account
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking", "initial_balance": 1000.00},
        )
        account_id = account_response.json()["id"]

        # Create transaction
        create_response = client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account_id,
                "amount": -50.00,
                "date": str(date.today()),
                "category": "groceries",
            },
        )
        transaction_id = create_response.json()["id"]

        # Verify initial balance
        account = client.get(f"/api/accounts/{account_id}", headers=auth_headers).json()
        assert account["balance"] == 950.00

        # Update transaction amount
        response = client.patch(
            f"/api/transactions/{transaction_id}",
            headers=auth_headers,
            json={"amount": -100.00},
        )

        assert response.status_code == 200

        # Verify balance updated correctly (1000 - 100 = 900)
        account = client.get(f"/api/accounts/{account_id}", headers=auth_headers).json()
        assert account["balance"] == 900.00

    def test_update_transaction_details_no_balance_change(self, client, auth_headers):
        """Updating non-amount fields doesn't change account balance"""
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking", "initial_balance": 1000.00},
        )
        account_id = account_response.json()["id"]

        create_response = client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account_id,
                "amount": -50.00,
                "date": str(date.today()),
                "category": "groceries",
            },
        )
        transaction_id = create_response.json()["id"]

        # Update category only
        response = client.patch(
            f"/api/transactions/{transaction_id}",
            headers=auth_headers,
            json={"category": "food"},
        )

        assert response.status_code == 200
        assert response.json()["category"] == "food"

        # Balance should still be 950
        account = client.get(f"/api/accounts/{account_id}", headers=auth_headers).json()
        assert account["balance"] == 950.00

    def test_update_nonexistent_transaction(self, client, auth_headers):
        """Updating non-existent transaction returns 404"""
        response = client.patch(
            "/api/transactions/99999",
            headers=auth_headers,
            json={"amount": 100.00},
        )

        assert response.status_code == 404


class TestTransactionDeletion:
    """Tests for deleting transactions"""

    def test_delete_transaction_updates_balance(self, client, auth_headers):
        """Deleting transaction updates account balance"""
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking", "initial_balance": 1000.00},
        )
        account_id = account_response.json()["id"]

        # Create transaction
        create_response = client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account_id,
                "amount": -50.00,
                "date": str(date.today()),
                "category": "groceries",
            },
        )
        transaction_id = create_response.json()["id"]

        # Verify balance after creation
        account = client.get(f"/api/accounts/{account_id}", headers=auth_headers).json()
        assert account["balance"] == 950.00

        # Delete transaction
        response = client.delete(f"/api/transactions/{transaction_id}", headers=auth_headers)

        assert response.status_code == 204

        # Verify balance restored
        account = client.get(f"/api/accounts/{account_id}", headers=auth_headers).json()
        assert account["balance"] == 1000.00

    def test_delete_nonexistent_transaction(self, client, auth_headers):
        """Deleting non-existent transaction returns 404"""
        response = client.delete("/api/transactions/99999", headers=auth_headers)

        assert response.status_code == 404


class TestBalanceCalculations:
    """Tests for balance calculation accuracy"""

    def test_balance_with_multiple_transactions(self, client, auth_headers):
        """Account balance correctly reflects multiple transactions"""
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking", "initial_balance": 1000.00},
        )
        account_id = account_response.json()["id"]

        # Create multiple transactions
        transactions = [
            {"amount": 500.00, "category": "income"},     # 1500
            {"amount": -100.00, "category": "groceries"}, # 1400
            {"amount": -50.00, "category": "gas"},        # 1350
            {"amount": 200.00, "category": "refund"},     # 1550
        ]

        for trans in transactions:
            client.post(
                "/api/transactions",
                headers=auth_headers,
                json={
                    "account_id": account_id,
                    "amount": trans["amount"],
                    "date": str(date.today()),
                    "category": trans["category"],
                },
            )

        # Verify final balance
        account = client.get(f"/api/accounts/{account_id}", headers=auth_headers).json()
        assert account["balance"] == 1550.00

    def test_balance_after_transaction_cascade_delete(self, client, auth_headers):
        """Deleting account cascades to transactions (balance irrelevant after)"""
        account_response = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking", "initial_balance": 1000.00},
        )
        account_id = account_response.json()["id"]

        # Create transaction
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account_id,
                "amount": -50.00,
                "date": str(date.today()),
                "category": "test",
            },
        )

        # Delete account
        response = client.delete(f"/api/accounts/{account_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify account is gone
        account_response = client.get(f"/api/accounts/{account_id}", headers=auth_headers)
        assert account_response.status_code == 404


class TestMultiTenancy:
    """Critical tests for multi-tenant data isolation"""

    def test_users_see_only_own_transactions(self, client, user_a_headers, user_b_headers):
        """Users should only see their own transactions"""
        # User A creates account and transactions
        account_a = client.post(
            "/api/accounts",
            headers=user_a_headers,
            json={"name": "User A Account", "account_type": "checking"},
        ).json()

        for i in range(3):
            client.post(
                "/api/transactions",
                headers=user_a_headers,
                json={
                    "account_id": account_a["id"],
                    "amount": float(i * 10),
                    "date": str(date.today()),
                    "category": "test",
                },
            )

        # User B creates account and transaction
        account_b = client.post(
            "/api/accounts",
            headers=user_b_headers,
            json={"name": "User B Account", "account_type": "checking"},
        ).json()

        client.post(
            "/api/transactions",
            headers=user_b_headers,
            json={
                "account_id": account_b["id"],
                "amount": 100.00,
                "date": str(date.today()),
                "category": "test",
            },
        )

        # User A should see 3 transactions
        response_a = client.get("/api/transactions", headers=user_a_headers)
        assert response_a.json()["total"] == 3

        # User B should see 1 transaction
        response_b = client.get("/api/transactions", headers=user_b_headers)
        assert response_b.json()["total"] == 1

    def test_user_cannot_access_other_user_transaction(self, client, user_a_headers, user_b_headers):
        """User cannot access another user's transaction by ID"""
        # User A creates transaction
        account_a = client.post(
            "/api/accounts",
            headers=user_a_headers,
            json={"name": "User A Account", "account_type": "checking"},
        ).json()

        transaction_a = client.post(
            "/api/transactions",
            headers=user_a_headers,
            json={
                "account_id": account_a["id"],
                "amount": 50.00,
                "date": str(date.today()),
                "category": "test",
            },
        ).json()

        # User B tries to access User A's transaction
        response_b = client.get(f"/api/transactions/{transaction_a['id']}", headers=user_b_headers)

        # Must return 404 (not 403) to avoid revealing transaction existence
        assert response_b.status_code == 404

    def test_user_cannot_update_other_user_transaction(self, client, user_a_headers, user_b_headers):
        """User cannot update another user's transaction"""
        # User A creates transaction
        account_a = client.post(
            "/api/accounts",
            headers=user_a_headers,
            json={"name": "User A Account", "account_type": "checking"},
        ).json()

        transaction_a = client.post(
            "/api/transactions",
            headers=user_a_headers,
            json={
                "account_id": account_a["id"],
                "amount": 50.00,
                "date": str(date.today()),
                "category": "test",
            },
        ).json()

        # User B tries to update User A's transaction
        response_b = client.patch(
            f"/api/transactions/{transaction_a['id']}",
            headers=user_b_headers,
            json={"amount": 1000.00},
        )

        assert response_b.status_code == 404

        # Verify transaction unchanged
        transaction_check = client.get(
            f"/api/transactions/{transaction_a['id']}", headers=user_a_headers
        ).json()
        assert transaction_check["amount"] == 50.00

    def test_user_cannot_delete_other_user_transaction(self, client, user_a_headers, user_b_headers):
        """User cannot delete another user's transaction"""
        # User A creates transaction
        account_a = client.post(
            "/api/accounts",
            headers=user_a_headers,
            json={"name": "User A Account", "account_type": "checking"},
        ).json()

        transaction_a = client.post(
            "/api/transactions",
            headers=user_a_headers,
            json={
                "account_id": account_a["id"],
                "amount": 50.00,
                "date": str(date.today()),
                "category": "test",
            },
        ).json()

        # User B tries to delete User A's transaction
        response_b = client.delete(
            f"/api/transactions/{transaction_a['id']}", headers=user_b_headers
        )

        assert response_b.status_code == 404

        # Verify transaction still exists for User A
        transaction_check = client.get(
            f"/api/transactions/{transaction_a['id']}", headers=user_a_headers
        )
        assert transaction_check.status_code == 200
