# Plan: Multi-Tenant Personal Finance Tracker with MCP_Auth Integration

## Overview

Build a FastAPI-based finance tracker that integrates with the existing MCP_Auth service (https://github.com/jtuchinsky/MCP_Auth) as a Resource Server. The finance tracker validates JWT tokens from MCP_Auth and provides per-user account and transaction management.

## Architecture Decisions

**Authentication Strategy:**
- Finance tracker validates JWTs using SHARED SECRET_KEY (same as MCP_Auth)
- Extracts user_id from JWT 'sub' claim
- Auto-creates User record on first API request with valid JWT
- Zero authentication logic in finance tracker (all delegated to MCP_Auth)

**Multi-Tenancy:**
- All data scoped by user_id extracted from JWT
- Repository layer enforces user_id filtering on every query
- No user can access another user's data

**Technology Stack:**
- FastAPI (mirroring MCP_Auth architecture)
- PostgreSQL database (separate from MCP_Auth)
- SQLAlchemy 2.0 + Alembic migrations
- python-jose for JWT validation
- Layered architecture: Routes → Services → Repositories → Models

**Data Model:**
- **Users**: Track auth_user_id from MCP_Auth (no passwords/emails)
- **Accounts**: Multiple per user (name, account_type, balance)
- **Transactions**: Per account with amount, date, category, description, tags, merchant, location

## Project Structure

```
app/
├── main.py                 # FastAPI application
├── config.py              # Settings (DATABASE_URL, SECRET_KEY)
├── database.py            # SQLAlchemy session
├── dependencies.py        # JWT validation dependency
├── core/
│   ├── security.py       # JWT decode/validation
│   └── exceptions.py     # Custom exceptions
├── models/
│   ├── base.py           # Base class + TimestampMixin
│   ├── user.py           # User model
│   ├── account.py        # Account model
│   └── transaction.py    # Transaction model
├── schemas/
│   ├── account_schemas.py
│   └── transaction_schemas.py
├── repositories/
│   ├── base_repository.py
│   ├── user_repository.py
│   ├── account_repository.py
│   └── transaction_repository.py
├── services/
│   ├── account_service.py
│   └── transaction_service.py
└── routes/
    ├── account_routes.py
    └── transaction_routes.py

alembic/                   # Database migrations
tests/                     # pytest tests with JWT mocking
.env                       # Environment variables
```

## Database Schema

### User Model
- `id`: Primary key
- `auth_user_id`: User ID from MCP_Auth (unique, indexed)
- Relationships: `accounts` (cascade delete)

### Account Model
- `id`: Primary key
- `user_id`: Foreign key to User (indexed)
- `name`: Account name
- `account_type`: Enum (checking, savings, credit_card, investment, loan, other)
- `balance`: Decimal(15,2) - updated by transaction service
- Relationships: `user`, `transactions` (cascade delete)

### Transaction Model
- `id`: Primary key
- `account_id`: Foreign key to Account (indexed)
- `amount`: Decimal(15,2) - positive=income, negative=expense
- `date`: Date (indexed)
- `category`: String (indexed)
- `description`: Text (nullable)
- `merchant`: String (nullable)
- `location`: String (nullable)
- `tags`: JSON array (nullable)
- Composite indexes: (account_id, date), (account_id, category)

## API Endpoints (All Require JWT)

### Accounts (`/api/accounts`)
- `POST /` - Create account
- `GET /` - List user's accounts
- `GET /{id}` - Get account details
- `PATCH /{id}` - Update account
- `DELETE /{id}` - Delete account (cascade to transactions)

### Transactions (`/api/transactions`)
- `POST /` - Create transaction (updates account balance)
- `GET /` - List with filtering (account_id, date range, category, merchant, tags, pagination)
- `GET /{id}` - Get transaction details
- `PATCH /{id}` - Update transaction (recalculates balance)
- `DELETE /{id}` - Delete transaction (recalculates balance)

## Implementation Steps

### Phase 0: Documentation
1. Create `docs/` directory
2. Save this plan to `docs/PLAN.md` for reference

### Phase 1: Foundation
1. Update `pyproject.toml` with dependencies (FastAPI, SQLAlchemy, Alembic, psycopg2, python-jose, pydantic-settings)
2. Create `.env.example` and `.env` files with DATABASE_URL and SECRET_KEY
3. Create `app/config.py` with Pydantic settings
4. Create `app/database.py` with SQLAlchemy engine and session factory
5. Create SQLAlchemy models (base, user, account, transaction)
6. Initialize Alembic: `alembic init alembic`
7. Configure `alembic/env.py` to use app settings and import models
8. Create initial migration: `alembic revision --autogenerate -m "Initial schema"`
9. Apply migration: `alembic upgrade head`

### Phase 2: Authentication Layer
1. Create `app/core/exceptions.py` with custom exceptions
2. Create `app/core/security.py` with JWT decode/validation
3. Create `app/repositories/user_repository.py` with `get_or_create_by_auth_id()`
4. Create `app/dependencies.py` with `get_current_user()` dependency
5. Create `app/main.py` with FastAPI app and exception handlers
6. Add `/health` endpoint for health checks

### Phase 3: Account Management
1. Create `app/repositories/account_repository.py` with user_id filtering
2. Create `app/services/account_service.py` with business logic
3. Create `app/schemas/account_schemas.py` with Pydantic models
4. Create `app/routes/account_routes.py` with all CRUD endpoints
5. Register account router in `app/main.py`
6. Test with curl/Postman using JWT from MCP_Auth

### Phase 4: Transaction Management
1. Create `app/repositories/transaction_repository.py` with filtering
2. Create `app/services/transaction_service.py` with balance calculation logic
3. Create `app/schemas/transaction_schemas.py` with validation
4. Create `app/routes/transaction_routes.py` with CRUD + filtering
5. Register transaction router in `app/main.py`
6. Implement atomic balance updates (SQLAlchemy transactions)
7. Test balance calculations with multiple transactions

### Phase 5: Testing
1. Create `tests/conftest.py` with test DB fixtures and mock JWT generator
2. Create `tests/test_auth_middleware.py` - JWT validation tests
3. Create `tests/test_accounts.py` - Account CRUD and multi-tenancy isolation
4. Create `tests/test_transactions.py` - Transaction CRUD and balance calculations
5. Run full test suite: `pytest`

### Phase 6: Documentation & Cleanup
1. Update `README.md` with API documentation
2. Update `CLAUDE.md` with development commands
3. Create `docker-compose.yml` for local development
4. Add `.gitignore` entries for `.env` and `test.db`
5. Commit all changes to git

## Critical Files to Create (in order)

1. `pyproject.toml` - Dependencies
2. `.env.example` + `.env` - Configuration
3. `app/config.py` - Settings management
4. `app/database.py` - Database connection
5. `app/models/*.py` - Data models
6. `alembic/env.py` - Migration setup
7. `app/core/security.py` - JWT validation
8. `app/dependencies.py` - FastAPI dependencies
9. `app/repositories/account_repository.py` - Data access
10. `app/services/account_service.py` - Business logic
11. `app/routes/account_routes.py` - API endpoints
12. `app/main.py` - FastAPI application

## Configuration Required

**.env file (shared SECRET_KEY is critical):**
```env
DATABASE_URL=postgresql://finance_user:password@localhost:5432/finance_planner
SECRET_KEY=<SAME-KEY-AS-MCP-AUTH>
DEBUG=true
LOG_LEVEL=INFO
```

## Testing Strategy

- Use SQLite in-memory DB for tests
- Mock JWT tokens with `python-jose`
- Test multi-tenancy isolation (user A cannot access user B's data)
- Test balance calculation accuracy
- Test cascade deletes
- Test invalid/expired JWT rejection

## Edge Cases Handled

1. **Auto-create user**: First API request with valid JWT creates User record
2. **Cascade deletes**: Deleting account → deletes transactions
3. **Balance consistency**: Updated atomically via SQLAlchemy transactions
4. **Multi-tenant safety**: All queries filtered by user_id from JWT
5. **Account ownership validation**: Service layer verifies account belongs to user before transactions
6. **Pagination**: List endpoints support limit/offset for large datasets

## Success Criteria

✅ User can create accounts after authenticating with MCP_Auth JWT
✅ User can create/read/update/delete transactions
✅ Account balance updates correctly with transactions
✅ User A cannot access User B's accounts or transactions
✅ Invalid/expired JWTs return 401 Unauthorized
✅ All endpoints require valid JWT Bearer token
✅ Tests pass with >80% coverage