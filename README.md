# Finance Planner

Multi-tenant personal finance tracker with JWT authentication via MCP_Auth integration.

## Overview

This is a FastAPI-based Resource Server that integrates with [MCP_Auth](https://github.com/jtuchinsky/MCP_Auth) for authentication. It provides per-user account and transaction management with strict multi-tenant isolation.

## Features

- **JWT Authentication**: Validates access tokens from MCP_Auth using shared SECRET_KEY
- **Multi-Tenant Architecture**: Complete data isolation per user
- **Account Management**: Full CRUD operations for financial accounts
- **Transaction Tracking**: Record income/expenses with detailed metadata (coming soon)
- **Auto-User Creation**: First API request automatically creates user record
- **RESTful API**: OpenAPI/Swagger documentation at `/docs`

## Tech Stack

- **FastAPI** 0.126+ - Modern web framework with automatic OpenAPI docs
- **SQLAlchemy** 2.0 - ORM with Alembic migrations
- **PostgreSQL/SQLite** - Production/development databases
- **python-jose** - JWT token validation
- **Pydantic** - Data validation and settings management

## Architecture

```
Routes ’ Services ’ Repositories ’ Models
```

- **Routes**: FastAPI endpoints with dependency injection
- **Services**: Business logic and orchestration
- **Repositories**: Data access with multi-tenant filtering
- **Models**: SQLAlchemy ORM models

## Quick Start

### Prerequisites

- Python 3.12+
- UV package manager
- PostgreSQL (production) or SQLite (development)
- Running MCP_Auth service for authentication

### Installation

1. Clone the repository:
```bash
git clone https://github.com/jtuchinsky/finance_planner.git
cd finance_planner
```

2. Create virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate  # On macOS/Linux
uv pip install -e ".[dev]"
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env and set SECRET_KEY to match your MCP_Auth instance!
```

**  CRITICAL**: The `SECRET_KEY` in `.env` MUST match your MCP_Auth service's SECRET_KEY for JWT validation to work.

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the server:
```bash
uvicorn app.main:app --reload
```

6. Visit API documentation:
```
http://localhost:8000/docs
```

## Configuration

All configuration via environment variables (see `.env.example`):

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL or SQLite connection string | Yes |
| `SECRET_KEY` | Shared secret with MCP_Auth for JWT validation | Yes |
| `DEBUG` | Enable debug mode and API docs | No (default: false) |
| `LOG_LEVEL` | Logging level (INFO, DEBUG, WARNING, ERROR) | No (default: INFO) |
| `CORS_ORIGINS` | Comma-separated allowed origins | No |

## API Endpoints

All endpoints require `Authorization: Bearer <jwt_token>` header.

### Accounts (`/api/accounts`)

- `POST /api/accounts` - Create account
- `GET /api/accounts` - List user's accounts
- `GET /api/accounts/{id}` - Get account details
- `PATCH /api/accounts/{id}` - Update account
- `DELETE /api/accounts/{id}` - Delete account

### Health Check

- `GET /health` - Service health status

## Authentication Flow

1. User authenticates with MCP_Auth service ’ receives JWT access token
2. User makes request to Finance Planner with `Authorization: Bearer <token>`
3. Finance Planner validates JWT using shared SECRET_KEY
4. Extracts user_id from JWT `sub` claim
5. Auto-creates User record if first request
6. Returns only data belonging to that user

## Database Schema

### Users
Tracks user_id from MCP_Auth (no passwords stored here)

### Accounts
- user_id (foreign key)
- name, account_type, balance
- Cascade deletes to transactions

### Transactions (coming soon)
- account_id (foreign key)
- amount, date, category
- description, merchant, location, tags

## Development

### Run Tests
```bash
pytest
```

### Create Migration
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Code Style
```bash
ruff check .
ruff format .
```

## Deployment

See `docs/PLAN.md` for comprehensive deployment guide including:
- Docker setup
- Production configuration
- Security considerations
- Database pooling

## Project Status

**Completed:**
-  JWT authentication integration
-  Multi-tenant user management
-  Account CRUD API
-  Database migrations
-  OpenAPI documentation

**In Progress:**
- =( Transaction management
- =( Balance calculations
- =( Test suite

**Planned:**
- =Ë Analytics endpoints
- =Ë Bulk operations
- =Ë Export/import features

## Security

- JWT tokens validated using HS256 with shared secret
- Multi-tenant isolation enforced at repository layer
- No user can access another user's data
- SQL injection protection via SQLAlchemy ORM
- CORS configurable for frontend integration

## Contributing

This is a personal project, but feedback and issues are welcome!

## License

MIT License - see LICENSE file for details

## Related Projects

- [MCP_Auth](https://github.com/jtuchinsky/MCP_Auth) - Authentication service