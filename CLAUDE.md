# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-tenant personal finance tracker that integrates with MCP_Auth (https://github.com/jtuchinsky/MCP_Auth) for JWT authentication. Built with FastAPI following a layered architecture pattern.

## Environment Setup

**Requirements:**
- Python >= 3.12
- UV package manager
- PostgreSQL (production) or SQLite (development)
- **Running MCP_Auth service for authentication** - Both services must run together

**Setup:**
```bash
uv venv
source .venv/bin/activate  # On macOS/Linux
uv pip install -e ".[dev]"
```

**CRITICAL Configuration:**
```bash
cp .env.example .env
# Edit .env and set SECRET_KEY to match your MCP_Auth instance
```

The `SECRET_KEY` in `.env` MUST be identical to MCP_Auth's SECRET_KEY for JWT validation.

**Running Both Services Together:**

Finance Planner requires MCP_Auth for JWT token generation and validation. See [docs/RUNNING.md](docs/RUNNING.md) for comprehensive deployment guides including:

- **Development**: Two terminals, tmux, startup scripts, log monitoring
- **Production**: systemd, Supervisor, Docker Compose templates, nginx reverse proxy
- **Configuration**: Shared SECRET_KEY verification scripts
- **Health Checks**: Service monitoring and integration testing
- **Troubleshooting**: Multi-service specific issues

Quick development setup:
```bash
# Terminal 1 - MCP_Auth (port 8001)
cd ../MCP_Auth && source .venv/bin/activate
uvicorn main:app --reload --port 8001

# Terminal 2 - Finance Planner (port 8000)
cd ../finance_planner && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

## Development Commands

### Running the Application
```bash
# Development server with auto-reload
uvicorn app.main:app --reload

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API documentation available at `http://localhost:8000/docs`

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_accounts.py
```

### Code Quality
```bash
# Format code
ruff format .

# Lint code
ruff check .
```

## Architecture

**Layered Architecture:**
```
Routes (API Layer) → Services (Business Logic) → Repositories (Data Access) → Models (Database)
```

This pattern mirrors the MCP_Auth service architecture for consistency.

### Directory Structure
```
app/
├── main.py                 # FastAPI app, exception handlers, CORS
├── config.py              # Pydantic settings from .env
├── database.py            # SQLAlchemy session factory
├── dependencies.py        # FastAPI dependencies (JWT validation)
├── core/
│   ├── security.py       # JWT decode/validate functions
│   └── exceptions.py     # Custom exception classes
├── models/
│   ├── base.py           # SQLAlchemy Base + TimestampMixin
│   ├── user.py           # User model (tracks MCP_Auth user_id)
│   ├── account.py        # Account model with AccountType enum
│   └── transaction.py    # Transaction model
├── schemas/
│   ├── account_schemas.py      # Pydantic request/response models
│   └── transaction_schemas.py  # Transaction schemas + batch operations
├── repositories/
│   ├── user_repository.py      # User data access + auto-create
│   ├── account_repository.py   # Account CRUD with user_id filtering
│   └── transaction_repository.py # Transaction CRUD + batch operations
├── services/
│   ├── account_service.py      # Account business logic
│   └── transaction_service.py  # Transaction business logic + balance updates
└── routes/
    ├── account_routes.py       # Account API endpoints
    └── transaction_routes.py   # Transaction API endpoints + batch creation
```

## Key Patterns and Conventions

### Multi-Tenant Isolation
**CRITICAL:** All data queries MUST filter by `user_id` to prevent cross-user data access.

```python
# ✅ CORRECT - Always filter by user_id
accounts = db.query(Account).filter(Account.user_id == user.id).all()

# ❌ WRONG - No user_id filter allows access to all users' data
accounts = db.query(Account).all()
```

Repositories enforce this pattern automatically. Always use repository methods.

### Authentication Flow
1. User obtains JWT from MCP_Auth (`/auth/login` or `/auth/register`)
2. Client sends JWT in `Authorization: Bearer <token>` header
3. `get_current_user()` dependency validates JWT using shared SECRET_KEY
4. Extracts `auth_user_id` from JWT `sub` claim
5. Auto-creates User record on first request
6. All endpoints receive authenticated `User` object

### Repository Pattern
Repositories handle ALL database access with built-in multi-tenant filtering:

```python
# In service layer
def get_account(self, account_id: int, user: User) -> Account:
    # Repository ensures account belongs to user
    account = self.repo.get_by_id_and_user(account_id, user.id)
    if not account:
        raise NotFoundException("Account not found")
    return account
```

### Service Layer
Services contain business logic and orchestration:
- Validation beyond Pydantic schemas
- Cross-entity operations
- Business rule enforcement
- Balance calculations (for transactions)

### Error Handling
Custom exceptions with HTTP status mapping:

```python
raise NotFoundException("Account not found")  # → 404
raise UnauthorizedException("Invalid token")  # → 401
raise ForbiddenException("Access denied")     # → 403
raise ValidationException("Invalid amount")   # → 400
```

## Database Models

### User
- `id`: Internal primary key
- `auth_user_id`: User ID from MCP_Auth (from JWT `sub` claim)
- Relationships: `accounts` (cascade delete)

### Account
- `id`: Primary key
- `user_id`: Foreign key to User (indexed for multi-tenant queries)
- `name`: Account name (e.g., "Chase Checking")
- `account_type`: Enum (checking, savings, credit_card, investment, loan, other)
- `balance`: Decimal(15,2) - updated by transaction service
- Relationships: `user`, `transactions` (cascade delete)

### Transaction
- `id`: Primary key
- `account_id`: Foreign key to Account (indexed)
- `amount`: Decimal(15,2) - positive=income, negative=expense
- `date`: Date (indexed)
- `category`: String (indexed)
- `der_category`: Derived/normalized category (indexed)
- `der_merchant`: Derived/normalized merchant
- `description`, `merchant`, `location`: Optional text fields
- `tags`: JSON array
- Composite indexes: (account_id, date), (account_id, category), (account_id, der_category)

## Testing Strategy

### Test Database
Tests use SQLite in-memory database for speed.

### JWT Mocking
Mock JWT tokens in tests:

```python
from jose import jwt
from app.config import settings

def create_test_token(user_id: str = "test-user-123"):
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

# In tests
headers = {"Authorization": f"Bearer {create_test_token()}"}
response = client.get("/api/accounts", headers=headers)
```

### Multi-Tenancy Tests
ALWAYS test that users cannot access other users' data:

```python
def test_user_cannot_access_other_user_account():
    # User A creates account
    token_a = create_test_token("user-a")
    account = client.post("/api/accounts", headers={"Authorization": f"Bearer {token_a}"},
                         json={"name": "A's Account", "account_type": "checking"})

    # User B tries to access
    token_b = create_test_token("user-b")
    response = client.get(f"/api/accounts/{account.json()['id']}",
                         headers={"Authorization": f"Bearer {token_b}"})

    assert response.status_code == 404  # Must not reveal account exists
```

## Common Tasks

### Adding a New Endpoint
1. Define Pydantic schemas in `app/schemas/`
2. Add repository method with user_id filtering in `app/repositories/`
3. Add service method with business logic in `app/services/`
4. Add route in `app/routes/`
5. Register router in `app/main.py`
6. Write tests with multi-tenancy checks

### Adding a New Model
1. Create model in `app/models/`
2. Import in `alembic/env.py`
3. Run `alembic revision --autogenerate -m "Add model"`
4. Review generated migration
5. Run `alembic upgrade head`

### Balance Calculations (for transactions)
When implementing transaction CRUD:
- Use database transactions for atomicity
- Update account.balance in same transaction
- Consider reconciliation job for data integrity

### Batch Operations
The batch transaction creation endpoint demonstrates key patterns:

```python
# In TransactionService
def create_transaction_batch(self, batch_data, user):
    # 1. Verify account ownership
    account = self.account_repo.get_by_id_and_user(batch_data.account_id, user.id)

    # 2. Calculate total upfront (single balance update)
    total_amount = sum(txn.amount for txn in batch_data.transactions)

    try:
        # 3. Bulk insert without committing
        created_transactions = self.transaction_repo.create_bulk(transaction_objects)

        # 4. Update balance without committing
        account.balance = float(account.balance) + total_amount
        self.account_repo.update_no_commit(account)

        # 5. SINGLE ATOMIC COMMIT
        self.db.commit()

        # 6. Refresh all objects
        self.db.refresh(account)
        for txn in created_transactions:
            self.db.refresh(txn)

        return created_transactions, float(account.balance)

    except Exception as e:
        # 7. Explicit rollback on failure
        self.db.rollback()
        raise
```

**Key principles:**
- Repository methods ending with `_no_commit()` for atomic operations
- Service layer controls the transaction boundary (single commit)
- Calculate aggregates upfront to minimize database operations
- Explicit rollback on any failure for data integrity

## Workflows and Use Cases

### API Usage Examples

#### 1. Complete User Workflow

```bash
# Step 1: Get JWT token from MCP_Auth
TOKEN=$(curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "password"}' \
  | jq -r '.access_token')

# Step 2: Create an account (user auto-created on first request)
ACCOUNT=$(curl -X POST http://localhost:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Checking Account", "account_type": "checking", "initial_balance": 1000.00}' \
  | jq -r '.id')

# Step 3: Add single transaction
curl -X POST http://localhost:8000/api/transactions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"account_id\": $ACCOUNT, \"amount\": -50.00, \"date\": \"2026-01-03\", \"category\": \"groceries\", \"merchant\": \"Whole Foods\"}"

# Step 4: View account balance (should be 950.00)
curl -X GET http://localhost:8000/api/accounts/$ACCOUNT \
  -H "Authorization: Bearer $TOKEN"
```

#### 2. Batch Transaction Import (Historical Data)

```bash
# Import CSV or historical data as batch
curl -X POST http://localhost:8000/api/transactions/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "transactions": [
      {"amount": -150.00, "date": "2026-01-01", "category": "groceries", "merchant": "Safeway"},
      {"amount": -45.00, "date": "2026-01-01", "category": "gas", "merchant": "Shell"},
      {"amount": 2500.00, "date": "2026-01-01", "category": "income", "description": "Salary"},
      {"amount": -1200.00, "date": "2026-01-01", "category": "rent", "merchant": "Landlord"},
      {"amount": -80.00, "date": "2026-01-02", "category": "utilities", "merchant": "PG&E"}
    ]
  }'
```

#### 3. Advanced Filtering and Pagination

```bash
# Filter transactions by date range
curl -X GET "http://localhost:8000/api/transactions?account_id=1&start_date=2026-01-01&end_date=2026-01-31" \
  -H "Authorization: Bearer $TOKEN"

# Filter by category
curl -X GET "http://localhost:8000/api/transactions?category=groceries" \
  -H "Authorization: Bearer $TOKEN"

# Filter by derived category (normalized)
curl -X GET "http://localhost:8000/api/transactions?der_category=food" \
  -H "Authorization: Bearer $TOKEN"

# Pagination with limit and offset
curl -X GET "http://localhost:8000/api/transactions?limit=20&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Complex filter: date range + category + pagination
curl -X GET "http://localhost:8000/api/transactions?start_date=2026-01-01&end_date=2026-01-31&category=groceries&limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

#### 4. Transaction Update with Automatic Balance Recalculation

```bash
# Update transaction amount (balance automatically recalculated)
curl -X PATCH http://localhost:8000/api/transactions/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": -75.00}'

# Update non-financial fields (no balance change)
curl -X PATCH http://localhost:8000/api/transactions/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category": "dining", "merchant": "Restaurant XYZ"}'

# Update derived fields for normalization
curl -X PATCH http://localhost:8000/api/transactions/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"der_category": "food_dining", "der_merchant": "restaurant_xyz"}'
```

### Development Workflows

#### Daily Development Cycle

```bash
# 1. Pull latest changes
git pull origin main

# 2. Ensure services are running
# Terminal 1: MCP_Auth
cd ../MCP_Auth && source .venv/bin/activate
uvicorn main:app --reload --port 8001

# Terminal 2: Finance Planner
cd ../finance_planner && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# 3. Make code changes

# 4. Run tests continuously during development
pytest tests/test_transactions.py -v  # Specific file
pytest -v -k "batch"                  # Tests matching pattern
pytest --lf                            # Last failed tests only

# 5. Check code style
ruff check .
ruff format .

# 6. Run full test suite before commit
pytest -v

# 7. Commit and push
git add .
git commit -m "Description"
git push origin main
```

#### Testing New Features Workflow

```python
# tests/test_new_feature.py

def test_new_feature(client, auth_headers):
    """Template for testing new features"""
    # 1. Setup: Create test data
    account = client.post(
        "/api/accounts",
        headers=auth_headers,
        json={"name": "Test", "account_type": "checking"}
    ).json()

    # 2. Action: Execute feature
    response = client.post(
        "/api/new-endpoint",
        headers=auth_headers,
        json={"account_id": account["id"], "data": "value"}
    )

    # 3. Assert: Verify results
    assert response.status_code == 201
    data = response.json()
    assert data["field"] == "expected_value"

    # 4. Verify side effects (e.g., balance updates)
    updated_account = client.get(
        f"/api/accounts/{account['id']}",
        headers=auth_headers
    ).json()
    assert updated_account["balance"] == expected_balance


def test_new_feature_multi_tenant_security(client, user_a_headers, user_b_headers):
    """ALWAYS test multi-tenant isolation"""
    # User A creates resource
    resource = client.post(
        "/api/new-endpoint",
        headers=user_a_headers,
        json={"data": "value"}
    ).json()

    # User B should not access User A's resource
    response = client.get(
        f"/api/new-endpoint/{resource['id']}",
        headers=user_b_headers
    )
    assert response.status_code == 404  # Not 403!
```

### Database Workflows

#### Inspecting Database During Development

```bash
# SQLite (development)
sqlite3 finance_planner.db

# Check current schema
.schema accounts
.schema transactions

# View all accounts
SELECT id, name, account_type, balance FROM accounts;

# View recent transactions with account info
SELECT t.id, a.name, t.amount, t.date, t.category, t.merchant
FROM transactions t
JOIN accounts a ON t.account_id = a.id
ORDER BY t.date DESC
LIMIT 10;

# Check balance consistency
SELECT
    a.id,
    a.name,
    a.balance as stored_balance,
    COALESCE(SUM(t.amount), 0) as calculated_balance,
    a.balance - COALESCE(SUM(t.amount), 0) as difference
FROM accounts a
LEFT JOIN transactions t ON a.id = t.account_id
GROUP BY a.id;

# Exit
.quit
```

#### Database Migration Workflow

```bash
# 1. Modify model in app/models/
# Example: Add new field to Transaction model

# 2. Generate migration
alembic revision --autogenerate -m "Add payment_method to transactions"

# 3. Review generated migration in alembic/versions/
# IMPORTANT: Always review autogenerated migrations!
# Alembic may miss: indexes, constraints, data migrations

# 4. Edit migration if needed
# Example: Add index, set default values, migrate existing data

# 5. Apply migration
alembic upgrade head

# 6. Verify migration
alembic current  # Check current revision
sqlite3 finance_planner.db ".schema transactions"

# 7. Test rollback (before committing)
alembic downgrade -1  # Rollback one revision
alembic upgrade head  # Re-apply

# 8. Update tests and schemas to use new field
```

### Debugging Workflows

#### Common Debugging Scenarios

**1. Balance Discrepancy**

```python
# In Python shell or notebook
from app.database import SessionLocal
from app.models.account import Account
from app.models.transaction import Transaction
from sqlalchemy import func

db = SessionLocal()

# Find accounts with balance discrepancies
accounts = db.query(Account).all()
for account in accounts:
    stored_balance = float(account.balance)
    calculated_balance = db.query(func.sum(Transaction.amount)).filter(
        Transaction.account_id == account.id
    ).scalar() or 0

    if abs(stored_balance - float(calculated_balance)) > 0.01:
        print(f"MISMATCH: Account {account.id} ({account.name})")
        print(f"  Stored: {stored_balance}")
        print(f"  Calculated: {calculated_balance}")

        # Fix discrepancy
        account.balance = calculated_balance
        db.commit()
        print(f"  FIXED to {calculated_balance}")
```

**2. JWT Token Issues**

```bash
# Decode JWT to inspect claims (debugging only - don't do in production!)
echo "$TOKEN" | cut -d. -f2 | base64 -d | jq .

# Check token expiration
python3 << EOF
from jose import jwt
import os
token = "$TOKEN"
decoded = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
print(f"User ID: {decoded['sub']}")
print(f"Expires: {decoded['exp']}")
EOF
```

**3. Multi-Tenant Data Leak Check**

```python
# Verify no cross-user data access
def test_no_data_leaks(db):
    """Run this check periodically"""
    from app.models.account import Account
    from app.models.user import User

    users = db.query(User).all()
    for user in users:
        # Get accounts directly (bypassing repository)
        all_accounts = db.query(Account).all()
        user_accounts = db.query(Account).filter(Account.user_id == user.id).all()

        print(f"User {user.auth_user_id}:")
        print(f"  Should see: {len(user_accounts)} accounts")
        print(f"  Total in DB: {len(all_accounts)} accounts")

        # Verify repository enforces filtering
        from app.repositories.account_repository import AccountRepository
        repo = AccountRepository(db)
        repo_accounts = repo.get_by_user(user.id)
        assert len(repo_accounts) == len(user_accounts), "Repository filter broken!"
```

### Performance Optimization Workflows

#### Query Performance Analysis

```python
# Enable SQLAlchemy query logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Now run your code and observe SQL queries
# Look for:
# - N+1 query problems
# - Missing indexes
# - Full table scans
```

#### Batch vs. Individual Inserts Benchmark

```python
import time
from datetime import date

# Individual inserts (OLD WAY - SLOW)
start = time.time()
for i in range(100):
    client.post("/api/transactions", json={
        "account_id": 1,
        "amount": float(i),
        "date": str(date.today()),
        "category": "test"
    })
individual_time = time.time() - start

# Batch insert (NEW WAY - FAST)
start = time.time()
client.post("/api/transactions/batch", json={
    "account_id": 1,
    "transactions": [
        {"amount": float(i), "date": str(date.today()), "category": "test"}
        for i in range(100)
    ]
})
batch_time = time.time() - start

print(f"Individual: {individual_time:.2f}s")
print(f"Batch: {batch_time:.2f}s")
print(f"Speedup: {individual_time / batch_time:.1f}x")
```

### Use Case Examples

#### Use Case 1: Monthly Budget Import

```python
# Importing monthly transactions from CSV
import csv
from datetime import datetime

def import_monthly_transactions(csv_file, account_id, auth_token):
    """Import transactions from CSV using batch endpoint"""
    transactions = []

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            transactions.append({
                "amount": float(row['amount']),
                "date": row['date'],
                "category": row['category'],
                "merchant": row.get('merchant'),
                "description": row.get('description'),
                "der_category": normalize_category(row['category']),
                "der_merchant": normalize_merchant(row.get('merchant', ''))
            })

    # Split into batches of 100
    for i in range(0, len(transactions), 100):
        batch = transactions[i:i+100]
        response = requests.post(
            "http://localhost:8000/api/transactions/batch",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"account_id": account_id, "transactions": batch}
        )
        print(f"Imported batch {i//100 + 1}: {response.json()['count']} transactions")

def normalize_category(category):
    """Normalize category for reporting"""
    mapping = {
        "groceries": "food_grocery",
        "dining": "food_dining",
        "gas": "transportation_fuel",
        # ... more mappings
    }
    return mapping.get(category.lower(), category.lower())
```

#### Use Case 2: Account Reconciliation

```python
def reconcile_account(account_id, expected_balance, auth_token):
    """Reconcile account balance with expected value"""
    # Get current balance
    account = requests.get(
        f"http://localhost:8000/api/accounts/{account_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    ).json()

    current_balance = account['balance']
    difference = expected_balance - current_balance

    if abs(difference) > 0.01:
        print(f"DISCREPANCY: ${difference:.2f}")
        print(f"  Current: ${current_balance:.2f}")
        print(f"  Expected: ${expected_balance:.2f}")

        # Add reconciliation adjustment
        requests.post(
            "http://localhost:8000/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "account_id": account_id,
                "amount": difference,
                "date": str(date.today()),
                "category": "adjustment",
                "description": f"Reconciliation adjustment: ${difference:.2f}"
            }
        )
        print("Reconciliation transaction created")
    else:
        print("Account balanced!")
```

#### Use Case 3: Monthly Spending Report

```python
def generate_monthly_report(month, year, auth_token):
    """Generate spending report by category for a month"""
    from calendar import monthrange

    start_date = f"{year}-{month:02d}-01"
    last_day = monthrange(year, month)[1]
    end_date = f"{year}-{month:02d}-{last_day}"

    # Get all transactions for month
    response = requests.get(
        f"http://localhost:8000/api/transactions",
        params={"start_date": start_date, "end_date": end_date, "limit": 1000},
        headers={"Authorization": f"Bearer {auth_token}"}
    ).json()

    # Group by category
    spending = {}
    income = 0

    for txn in response['transactions']:
        amount = txn['amount']
        category = txn.get('der_category') or txn['category']

        if amount < 0:
            spending[category] = spending.get(category, 0) + abs(amount)
        else:
            income += amount

    # Print report
    print(f"\nSpending Report: {month}/{year}")
    print("=" * 50)
    print(f"Income: ${income:.2f}")
    print(f"\nExpenses by Category:")
    for category, amount in sorted(spending.items(), key=lambda x: -x[1]):
        print(f"  {category:20s} ${amount:>10.2f}")
    print("=" * 50)
    print(f"Total Expenses: ${sum(spending.values()):.2f}")
    print(f"Net: ${income - sum(spending.values()):.2f}")
```

## Security Considerations

1. **JWT Validation**: SECRET_KEY must match MCP_Auth exactly
2. **Multi-Tenancy**: Every query must filter by user_id
3. **Cascade Deletes**: Deleting account deletes transactions (by design)
4. **SQL Injection**: SQLAlchemy ORM handles parameterization
5. **CORS**: Configure origins in .env for frontend access

## Current Status

**Implemented:**
- JWT authentication integration with MCP_Auth
- User auto-creation on first request
- Account CRUD API (`/api/accounts`)
- Transaction CRUD API (`/api/transactions`) with:
  - Single transaction creation/update/delete with automatic balance updates
  - Batch transaction creation (1-100 transactions atomically)
  - Advanced filtering (date range, category, merchant, tags, derived fields)
  - Pagination support
- Multi-tenant data isolation
- Database migrations
- OpenAPI documentation
- Comprehensive test suite (82/82 tests passing)

**Next Steps:**
- Analytics endpoints (spending reports, category summaries, trends)
- Export/import features (CSV, JSON)
- Advanced search and filtering capabilities
- Docker deployment setup

## Troubleshooting

### JWT Validation Fails
- Verify SECRET_KEY in .env matches MCP_Auth
- Check JWT token hasn't expired (15-min default)
- Ensure Authorization header format: `Bearer <token>`

### Database Connection Issues
- For SQLite: Check DATABASE_URL path is writable
- For PostgreSQL: Verify service is running and credentials are correct
- Run `alembic upgrade head` to ensure schema is up-to-date

### Import Errors
- Run `uv pip install -e ".[dev]"` to reinstall
- Check virtual environment is activated

## Additional Resources

- Full implementation plan: `docs/PLAN.md`
- MCP_Auth repository: https://github.com/jtuchinsky/MCP_Auth
- FastAPI documentation: https://fastapi.tiangolo.com
- SQLAlchemy 2.0 documentation: https://docs.sqlalchemy.org/en/20/