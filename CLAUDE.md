# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-tenant personal finance tracker that integrates with MCP_Auth (https://github.com/jtuchinsky/MCP_Auth) for JWT authentication. Built with FastAPI following a layered architecture pattern.

## Environment Setup

**Requirements:**
- Python >= 3.12
- UV package manager
- PostgreSQL (production) or SQLite (development)
- Running MCP_Auth service for authentication

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
│   └── transaction_schemas.py  # (coming soon)
├── repositories/
│   ├── user_repository.py      # User data access + auto-create
│   ├── account_repository.py   # Account CRUD with user_id filtering
│   └── transaction_repository.py # (coming soon)
├── services/
│   ├── account_service.py      # Account business logic
│   └── transaction_service.py  # (coming soon)
└── routes/
    ├── account_routes.py       # Account API endpoints
    └── transaction_routes.py   # (coming soon)
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
- `description`, `merchant`, `location`: Optional text fields
- `tags`: JSON array
- Composite indexes: (account_id, date), (account_id, category)

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
- Multi-tenant data isolation
- Database migrations
- OpenAPI documentation

**Next Steps:**
- Transaction CRUD with balance calculations
- Comprehensive test suite
- Analytics endpoints (optional)
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