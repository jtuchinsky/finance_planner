"""
Integration tests for Finance Planner API.

Tests complete workflows across multiple endpoints and the full stack
(routes → services → repositories → database).
"""

import pytest
from datetime import date, timedelta


class TestCompleteUserWorkflow:
    """Integration tests for complete user workflows"""

    def test_new_user_complete_workflow(self, client, auth_headers):
        """Test complete workflow: user signup → create accounts → add transactions → verify balances"""

        # Step 1: User makes first API call (auto-created in database)
        response = client.get("/api/accounts", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0

        # Step 2: Create checking and savings accounts
        checking = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "My Checking", "account_type": "checking", "initial_balance": 5000.00},
        ).json()

        savings = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "My Savings", "account_type": "savings", "initial_balance": 10000.00},
        ).json()

        # Step 3: Add transactions to checking account
        # Expense: Rent
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": checking["id"],
                "amount": -1500.00,
                "date": str(date.today()),
                "category": "rent",
                "description": "Monthly rent payment",
                "merchant": "Property Management",
            },
        )

        # Expense: Groceries
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": checking["id"],
                "amount": -250.00,
                "date": str(date.today()),
                "category": "groceries",
                "merchant": "Whole Foods",
                "tags": ["food", "essentials"],
            },
        )

        # Income: Paycheck
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": checking["id"],
                "amount": 3000.00,
                "date": str(date.today()),
                "category": "salary",
                "description": "Bi-weekly paycheck",
            },
        )

        # Step 4: Transfer from checking to savings
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": checking["id"],
                "amount": -500.00,
                "date": str(date.today()),
                "category": "transfer",
                "description": "Transfer to savings",
            },
        )

        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": savings["id"],
                "amount": 500.00,
                "date": str(date.today()),
                "category": "transfer",
                "description": "Transfer from checking",
            },
        )

        # Step 5: Verify final balances
        # Checking: 5000 - 1500 - 250 + 3000 - 500 = 5750
        checking_final = client.get(f"/api/accounts/{checking['id']}", headers=auth_headers).json()
        assert checking_final["balance"] == 5750.00

        # Savings: 10000 + 500 = 10500
        savings_final = client.get(f"/api/accounts/{savings['id']}", headers=auth_headers).json()
        assert savings_final["balance"] == 10500.00

        # Step 6: Verify transaction history
        transactions = client.get("/api/transactions", headers=auth_headers).json()
        assert transactions["total"] == 5  # 3 checking + 2 savings transactions


class TestBalanceConsistency:
    """Integration tests for balance calculation consistency"""

    def test_balance_remains_consistent_through_updates(self, client, auth_headers):
        """Balance should remain consistent through create/update/delete operations"""

        # Create account
        account = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test Account", "account_type": "checking", "initial_balance": 1000.00},
        ).json()

        # Add transaction
        trans1 = client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account["id"],
                "amount": -100.00,
                "date": str(date.today()),
                "category": "test",
            },
        ).json()

        # Verify balance: 1000 - 100 = 900
        balance1 = client.get(f"/api/accounts/{account['id']}", headers=auth_headers).json()["balance"]
        assert balance1 == 900.00

        # Update transaction amount
        client.patch(
            f"/api/transactions/{trans1['id']}",
            headers=auth_headers,
            json={"amount": -200.00},
        )

        # Verify balance: 1000 - 200 = 800
        balance2 = client.get(f"/api/accounts/{account['id']}", headers=auth_headers).json()["balance"]
        assert balance2 == 800.00

        # Add another transaction
        trans2 = client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account["id"],
                "amount": 50.00,
                "date": str(date.today()),
                "category": "income",
            },
        ).json()

        # Verify balance: 800 + 50 = 850
        balance3 = client.get(f"/api/accounts/{account['id']}", headers=auth_headers).json()["balance"]
        assert balance3 == 850.00

        # Delete first transaction
        client.delete(f"/api/transactions/{trans1['id']}", headers=auth_headers)

        # Verify balance: 850 + 200 (removed expense) = 1050
        balance4 = client.get(f"/api/accounts/{account['id']}", headers=auth_headers).json()["balance"]
        assert balance4 == 1050.00

        # Delete second transaction
        client.delete(f"/api/transactions/{trans2['id']}", headers=auth_headers)

        # Verify balance: 1050 - 50 (removed income) = 1000 (back to initial)
        balance5 = client.get(f"/api/accounts/{account['id']}", headers=auth_headers).json()["balance"]
        assert balance5 == 1000.00

    def test_complex_balance_calculation(self, client, auth_headers):
        """Test balance with multiple transactions of various types"""

        account = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Complex Account", "account_type": "checking", "initial_balance": 0.00},
        ).json()

        # Add various transactions
        transactions = [
            {"amount": 1000.00, "category": "salary"},          # 1000
            {"amount": -123.45, "category": "groceries"},       # 876.55
            {"amount": -67.89, "category": "gas"},              # 808.66
            {"amount": 50.00, "category": "refund"},            # 858.66
            {"amount": -999.99, "category": "rent"},            # -141.33
            {"amount": 500.00, "category": "bonus"},            # 358.67
            {"amount": -12.34, "category": "subscription"},     # 346.33
            {"amount": 100.00, "category": "cashback"},         # 446.33
        ]

        for trans in transactions:
            client.post(
                "/api/transactions",
                headers=auth_headers,
                json={
                    "account_id": account["id"],
                    "amount": trans["amount"],
                    "date": str(date.today()),
                    "category": trans["category"],
                },
            )

        # Verify final balance
        final_balance = client.get(f"/api/accounts/{account['id']}", headers=auth_headers).json()["balance"]
        expected = sum(t["amount"] for t in transactions)
        assert abs(final_balance - expected) < 0.01  # Allow small floating-point variance


class TestCascadeOperations:
    """Integration tests for cascade delete behavior"""

    def test_deleting_account_cascades_to_transactions(self, client, auth_headers):
        """Deleting an account should delete all its transactions"""

        # Create account
        account = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "To Delete", "account_type": "checking"},
        ).json()

        # Add transactions
        trans_ids = []
        for i in range(5):
            trans = client.post(
                "/api/transactions",
                headers=auth_headers,
                json={
                    "account_id": account["id"],
                    "amount": float(i * 10),
                    "date": str(date.today()),
                    "category": "test",
                },
            ).json()
            trans_ids.append(trans["id"])

        # Verify transactions exist
        transactions = client.get(
            f"/api/transactions?account_id={account['id']}", headers=auth_headers
        ).json()
        assert transactions["total"] == 5

        # Delete account
        response = client.delete(f"/api/accounts/{account['id']}", headers=auth_headers)
        assert response.status_code == 204

        # Verify transactions are gone (cascade delete)
        for trans_id in trans_ids:
            response = client.get(f"/api/transactions/{trans_id}", headers=auth_headers)
            assert response.status_code == 404


class TestFilteringAndPagination:
    """Integration tests for filtering and pagination with real data"""

    def test_comprehensive_filtering(self, client, auth_headers):
        """Test filtering transactions across multiple dimensions"""

        # Create account
        account = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Filter Test", "account_type": "checking"},
        ).json()

        # Create transactions with various attributes
        today = date.today()
        transactions_data = [
            {
                "date": str(today - timedelta(days=10)),
                "category": "groceries",
                "merchant": "Whole Foods",
                "tags": ["food", "organic"],
                "amount": -150.00,
            },
            {
                "date": str(today - timedelta(days=5)),
                "category": "groceries",
                "merchant": "Safeway",
                "tags": ["food"],
                "amount": -80.00,
            },
            {
                "date": str(today - timedelta(days=3)),
                "category": "dining",
                "merchant": "Chipotle",
                "tags": ["food", "lunch"],
                "amount": -25.00,
            },
            {
                "date": str(today - timedelta(days=1)),
                "category": "gas",
                "merchant": "Shell",
                "tags": ["car", "fuel"],
                "amount": -60.00,
            },
            {
                "date": str(today),
                "category": "salary",
                "merchant": None,
                "tags": ["income"],
                "amount": 2000.00,
            },
        ]

        for trans in transactions_data:
            client.post(
                "/api/transactions",
                headers=auth_headers,
                json={
                    "account_id": account["id"],
                    "amount": trans["amount"],
                    "date": trans["date"],
                    "category": trans["category"],
                    "merchant": trans["merchant"],
                    "tags": trans["tags"],
                },
            )

        # Test 1: Filter by category
        groceries = client.get(
            "/api/transactions?category=groceries", headers=auth_headers
        ).json()
        assert groceries["total"] == 2

        # Test 2: Filter by date range
        week_ago = today - timedelta(days=7)
        recent = client.get(
            f"/api/transactions?start_date={week_ago}", headers=auth_headers
        ).json()
        assert recent["total"] == 4  # Excludes 10-day-old transaction

        # Test 3: Filter by merchant (partial match)
        whole_foods = client.get(
            "/api/transactions?merchant=Whole", headers=auth_headers
        ).json()
        assert whole_foods["total"] == 1

        # Test 4: Filter by tags
        food_tagged = client.get(
            "/api/transactions?tags=food", headers=auth_headers
        ).json()
        assert food_tagged["total"] == 3

        # Test 5: Combined filters
        combined = client.get(
            f"/api/transactions?category=groceries&start_date={week_ago}",
            headers=auth_headers,
        ).json()
        assert combined["total"] == 1  # Only Safeway transaction

    def test_pagination_with_real_data(self, client, auth_headers):
        """Test pagination works correctly with real transaction data"""

        # Create account
        account = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Pagination Test", "account_type": "checking"},
        ).json()

        # Create 25 transactions
        for i in range(25):
            client.post(
                "/api/transactions",
                headers=auth_headers,
                json={
                    "account_id": account["id"],
                    "amount": float(i),
                    "date": str(date.today()),
                    "category": f"category_{i}",
                },
            )

        # Test pagination
        page1 = client.get("/api/transactions?limit=10&offset=0", headers=auth_headers).json()
        assert page1["total"] == 25
        assert len(page1["transactions"]) == 10

        page2 = client.get("/api/transactions?limit=10&offset=10", headers=auth_headers).json()
        assert page2["total"] == 25
        assert len(page2["transactions"]) == 10

        page3 = client.get("/api/transactions?limit=10&offset=20", headers=auth_headers).json()
        assert page3["total"] == 25
        assert len(page3["transactions"]) == 5  # Remaining items

        # Verify no duplicate IDs across pages
        ids_page1 = {t["id"] for t in page1["transactions"]}
        ids_page2 = {t["id"] for t in page2["transactions"]}
        ids_page3 = {t["id"] for t in page3["transactions"]}

        assert len(ids_page1 & ids_page2) == 0  # No overlap
        assert len(ids_page2 & ids_page3) == 0  # No overlap


class TestMultiTenantEndToEnd:
    """Integration tests for complete multi-tenant isolation"""

    def test_complete_tenant_isolation(self, client, user_a_headers, user_b_headers):
        """Verify complete isolation between users across all operations"""

        # User A: Create account and transactions
        account_a = client.post(
            "/api/accounts",
            headers=user_a_headers,
            json={"name": "User A Account", "account_type": "checking", "initial_balance": 1000.00},
        ).json()

        for i in range(3):
            client.post(
                "/api/transactions",
                headers=user_a_headers,
                json={
                    "account_id": account_a["id"],
                    "amount": float(i * 10),
                    "date": str(date.today()),
                    "category": "user_a_category",
                },
            )

        # User B: Create account and transactions
        account_b = client.post(
            "/api/accounts",
            headers=user_b_headers,
            json={"name": "User B Account", "account_type": "savings", "initial_balance": 2000.00},
        ).json()

        for i in range(2):
            client.post(
                "/api/transactions",
                headers=user_b_headers,
                json={
                    "account_id": account_b["id"],
                    "amount": float(i * 20),
                    "date": str(date.today()),
                    "category": "user_b_category",
                },
            )

        # Test 1: User A sees only their account
        accounts_a = client.get("/api/accounts", headers=user_a_headers).json()
        assert accounts_a["total"] == 1
        assert accounts_a["accounts"][0]["id"] == account_a["id"]

        # Test 2: User B sees only their account
        accounts_b = client.get("/api/accounts", headers=user_b_headers).json()
        assert accounts_b["total"] == 1
        assert accounts_b["accounts"][0]["id"] == account_b["id"]

        # Test 3: User A sees only their transactions
        transactions_a = client.get("/api/transactions", headers=user_a_headers).json()
        assert transactions_a["total"] == 3
        assert all(t["category"] == "user_a_category" for t in transactions_a["transactions"])

        # Test 4: User B sees only their transactions
        transactions_b = client.get("/api/transactions", headers=user_b_headers).json()
        assert transactions_b["total"] == 2
        assert all(t["category"] == "user_b_category" for t in transactions_b["transactions"])

        # Test 5: User A cannot access User B's account
        response = client.get(f"/api/accounts/{account_b['id']}", headers=user_a_headers)
        assert response.status_code == 404

        # Test 6: User B cannot access User A's transactions
        transaction_a_id = transactions_a["transactions"][0]["id"]
        response = client.get(f"/api/transactions/{transaction_a_id}", headers=user_b_headers)
        assert response.status_code == 404

        # Test 7: Filtering returns no cross-tenant results
        all_groceries = client.get("/api/transactions?category=user_a_category", headers=user_b_headers).json()
        assert all_groceries["total"] == 0  # User B shouldn't see User A's categories


class TestErrorHandlingEndToEnd:
    """Integration tests for error handling across the stack"""

    def test_invalid_account_in_transaction_creation(self, client, auth_headers):
        """Creating transaction with invalid account should fail properly"""

        response = client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": 99999,
                "amount": 100.00,
                "date": str(date.today()),
                "category": "test",
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_invalid_data_validation(self, client, auth_headers):
        """Invalid data should be caught by validation layer"""

        # Create account first
        account = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Test", "account_type": "checking"},
        ).json()

        # Test invalid date format
        response = client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account["id"],
                "amount": 100.00,
                "date": "invalid-date",
                "category": "test",
            },
        )
        assert response.status_code == 422  # Validation error

        # Test missing required fields
        response = client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": account["id"],
                "amount": 100.00,
                # Missing date and category
            },
        )
        assert response.status_code == 422

    def test_unauthorized_access_to_protected_endpoints(self, client):
        """Accessing protected endpoints without auth should fail"""

        # No auth headers
        response = client.get("/api/accounts")
        assert response.status_code == 401

        response = client.get("/api/transactions")
        assert response.status_code == 401

        response = client.post(
            "/api/accounts",
            json={"name": "Test", "account_type": "checking"},
        )
        assert response.status_code == 401


class TestComplexScenarios:
    """Integration tests for complex real-world scenarios"""

    def test_monthly_budgeting_scenario(self, client, auth_headers):
        """Simulate a month of budgeting with multiple accounts and categories"""

        # Setup: Create accounts
        checking = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Checking", "account_type": "checking", "initial_balance": 3000.00},
        ).json()

        savings = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Savings", "account_type": "savings", "initial_balance": 5000.00},
        ).json()

        credit_card = client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Credit Card", "account_type": "credit_card", "initial_balance": 0.00},
        ).json()

        # Scenario: Month of transactions
        today = date.today()

        # Week 1: Payday and expenses
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": checking["id"],
                "amount": 2500.00,
                "date": str(today - timedelta(days=28)),
                "category": "salary",
                "description": "Bi-weekly paycheck",
            },
        )

        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": checking["id"],
                "amount": -1200.00,
                "date": str(today - timedelta(days=27)),
                "category": "rent",
                "merchant": "Property Management",
            },
        )

        # Week 2: Regular expenses
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": credit_card["id"],
                "amount": -150.00,
                "date": str(today - timedelta(days=21)),
                "category": "groceries",
                "merchant": "Whole Foods",
                "tags": ["food", "monthly"],
            },
        )

        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": credit_card["id"],
                "amount": -60.00,
                "date": str(today - timedelta(days=18)),
                "category": "gas",
                "merchant": "Shell",
                "tags": ["car"],
            },
        )

        # Week 3: Payday and savings
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": checking["id"],
                "amount": 2500.00,
                "date": str(today - timedelta(days=14)),
                "category": "salary",
            },
        )

        # Transfer to savings (10% of income)
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": checking["id"],
                "amount": -500.00,
                "date": str(today - timedelta(days=14)),
                "category": "transfer",
                "description": "Monthly savings",
            },
        )

        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": savings["id"],
                "amount": 500.00,
                "date": str(today - timedelta(days=14)),
                "category": "transfer",
            },
        )

        # Week 4: Pay credit card
        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": checking["id"],
                "amount": -210.00,
                "date": str(today - timedelta(days=7)),
                "category": "payment",
                "description": "Credit card payment",
            },
        )

        client.post(
            "/api/transactions",
            headers=auth_headers,
            json={
                "account_id": credit_card["id"],
                "amount": 210.00,
                "date": str(today - timedelta(days=7)),
                "category": "payment",
            },
        )

        # Verify final balances
        checking_final = client.get(f"/api/accounts/{checking['id']}", headers=auth_headers).json()
        # 3000 + 2500 - 1200 + 2500 - 500 - 210 = 6090
        assert checking_final["balance"] == 6090.00

        savings_final = client.get(f"/api/accounts/{savings['id']}", headers=auth_headers).json()
        # 5000 + 500 = 5500
        assert savings_final["balance"] == 5500.00

        credit_card_final = client.get(f"/api/accounts/{credit_card['id']}", headers=auth_headers).json()
        # 0 - 150 - 60 + 210 = 0 (paid off)
        assert credit_card_final["balance"] == 0.00

        # Verify spending by category
        groceries_spending = client.get(
            "/api/transactions?category=groceries", headers=auth_headers
        ).json()
        assert groceries_spending["total"] == 1
        assert groceries_spending["transactions"][0]["amount"] == -150.00

        # Verify all accounts have correct transaction counts
        all_transactions = client.get("/api/transactions", headers=auth_headers).json()
        assert all_transactions["total"] == 9  # Total transactions created