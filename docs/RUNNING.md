# Finance Planner Running Guide

A comprehensive quick-start guide for setting up and running the Finance Planner project from scratch.

## Prerequisites

- **Python 3.12 or higher**
- **Git**
- **uv** package manager (recommended) or pip
- **PostgreSQL** (for production) or SQLite (for development)
- **MCP_Auth** running (for JWT token generation)

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/jtuchinsky/finance_planner.git
cd finance_planner
```

### 2. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Database Configuration
DATABASE_URL=postgresql://finance_user:your_password@localhost:5432/finance_planner
# For SQLite (development): DATABASE_URL=sqlite:///./finance_planner.db

# Security (MUST match MCP_Auth SECRET_KEY)
SECRET_KEY=your-super-secret-key-here

# Application Settings
APP_NAME=Finance Planner API
APP_VERSION=1.0.0
DEBUG=true
LOG_LEVEL=INFO

# CORS Settings (comma-separated origins)
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
CORS_ALLOW_CREDENTIALS=true
```

**Important:** The `SECRET_KEY` must be identical to the one used in MCP_Auth for JWT validation to work.

#### Generating a Secure Secret Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and use it in both `.env` files (MCP_Auth and Finance Planner).

### 3. Install Dependencies

Using **uv** (recommended):

```bash
uv sync
```

Using **pip**:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

This creates a `.venv` directory with all required packages:
- FastAPI, Uvicorn
- SQLAlchemy, Alembic
- python-jose (JWT)
- psycopg2-binary (PostgreSQL)
- Pydantic Settings
- Pytest (for testing)

### 4. Database Setup

#### Option A: PostgreSQL (Production)

1. **Install PostgreSQL** (if not already installed):
   ```bash
   # macOS
   brew install postgresql@16
   brew services start postgresql@16

   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   sudo systemctl start postgresql
   ```

2. **Create Database and User**:
   ```bash
   psql postgres
   ```
   ```sql
   CREATE DATABASE finance_planner;
   CREATE USER finance_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE finance_planner TO finance_user;
   \q
   ```

3. **Run Migrations**:
   ```bash
   source .venv/bin/activate  # Activate virtual environment
   alembic upgrade head
   ```

4. **Verify Tables Created**:
   ```bash
   psql finance_planner
   \dt
   ```
   You should see: `users`, `accounts`, `transactions`, `alembic_version`

#### Option B: SQLite (Development)

1. **Update `.env`**:
   ```env
   DATABASE_URL=sqlite:///./finance_planner.db
   ```

2. **Run Migrations**:
   ```bash
   source .venv/bin/activate
   alembic upgrade head
   ```

3. **Verify Tables**:
   ```bash
   sqlite3 finance_planner.db ".tables"
   ```

### 5. Start the Development Server

Activate the virtual environment:

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Run the server:

```bash
uvicorn app.main:app --reload
```

The server starts on `http://127.0.0.1:8000`

**Access Points:**
- **API Root**: http://127.0.0.1:8000
- **Interactive Docs**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/health

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Running Tests

The project includes 58 comprehensive tests covering authentication, accounts, and transactions.

### Run All Tests

```bash
source .venv/bin/activate
pytest
```

Expected output:
```
============================== 58 passed in 0.53s ===============================
```

### Run Specific Test Files

```bash
pytest tests/test_auth_middleware.py  # 12 auth tests
pytest tests/test_accounts.py         # 20 account tests
pytest tests/test_transactions.py     # 26 transaction tests
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Coverage Report

```bash
pytest --cov=app --cov-report=term-missing
```

**Note:** Tests use SQLite in-memory database and do not affect your production/development database.

## API Usage Workflows

### Prerequisites: Get JWT Token from MCP_Auth

The Finance Planner requires a valid JWT token from MCP_Auth for all API calls (except `/health` and `/`).

1. **Ensure MCP_Auth is running** on http://127.0.0.1:8001

2. **Register a user** (if not already registered):
   ```bash
   curl -X POST http://127.0.0.1:8001/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "SecurePassword123!"}'
   ```

3. **Login to get access token**:
   ```bash
   curl -X POST http://127.0.0.1:8001/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "SecurePassword123!"}'
   ```

   Response:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "refresh_token": "...",
     "token_type": "bearer"
   }
   ```

4. **Use the access token** in all Finance Planner API calls:
   ```bash
   export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   ```

### Workflow 1: Create and Manage Accounts

1. **Create a checking account**:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/accounts \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Chase Checking",
       "account_type": "checking",
       "initial_balance": 5000.00
     }'
   ```

   Response:
   ```json
   {
     "id": 1,
     "user_id": 1,
     "name": "Chase Checking",
     "account_type": "checking",
     "balance": 5000.0,
     "created_at": "2025-12-27T10:30:00",
     "updated_at": "2025-12-27T10:30:00"
   }
   ```

2. **List all accounts**:
   ```bash
   curl -X GET http://127.0.0.1:8000/api/accounts \
     -H "Authorization: Bearer $TOKEN"
   ```

3. **Update account name**:
   ```bash
   curl -X PATCH http://127.0.0.1:8000/api/accounts/1 \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name": "Chase Checking - Personal"}'
   ```

### Workflow 2: Create and Track Transactions

1. **Create an expense transaction** (negative amount):
   ```bash
   curl -X POST http://127.0.0.1:8000/api/transactions \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "account_id": 1,
       "amount": -87.50,
       "date": "2025-12-27",
       "category": "groceries",
       "description": "Weekly grocery shopping",
       "merchant": "Whole Foods Market",
       "location": "Seattle, WA",
       "tags": ["food", "essentials"]
     }'
   ```

   **Note:** Account balance automatically updates from 5000.00 to 4912.50

2. **Create an income transaction** (positive amount):
   ```bash
   curl -X POST http://127.0.0.1:8000/api/transactions \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "account_id": 1,
       "amount": 2500.00,
       "date": "2025-12-27",
       "category": "salary",
       "description": "Monthly paycheck"
     }'
   ```

   Balance now: 7412.50

3. **List all transactions**:
   ```bash
   curl -X GET http://127.0.0.1:8000/api/transactions \
     -H "Authorization: Bearer $TOKEN"
   ```

### Workflow 3: Filter and Search Transactions

1. **Filter by date range**:
   ```bash
   curl -X GET "http://127.0.0.1:8000/api/transactions?start_date=2025-12-01&end_date=2025-12-31" \
     -H "Authorization: Bearer $TOKEN"
   ```

2. **Filter by category**:
   ```bash
   curl -X GET "http://127.0.0.1:8000/api/transactions?category=groceries" \
     -H "Authorization: Bearer $TOKEN"
   ```

3. **Filter by merchant** (partial match):
   ```bash
   curl -X GET "http://127.0.0.1:8000/api/transactions?merchant=Whole" \
     -H "Authorization: Bearer $TOKEN"
   ```

4. **Filter by tags** (comma-separated, matches ANY):
   ```bash
   curl -X GET "http://127.0.0.1:8000/api/transactions?tags=food,essentials" \
     -H "Authorization: Bearer $TOKEN"
   ```

5. **Combine filters with pagination**:
   ```bash
   curl -X GET "http://127.0.0.1:8000/api/transactions?category=groceries&limit=10&offset=0" \
     -H "Authorization: Bearer $TOKEN"
   ```

### Workflow 4: Update and Delete Transactions

1. **Update transaction amount** (balance recalculates automatically):
   ```bash
   curl -X PATCH http://127.0.0.1:8000/api/transactions/1 \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"amount": -100.00}'
   ```

2. **Update transaction details** (balance unchanged):
   ```bash
   curl -X PATCH http://127.0.0.1:8000/api/transactions/1 \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "category": "food",
       "description": "Updated description",
       "tags": ["food", "weekly"]
     }'
   ```

3. **Delete transaction** (balance updates):
   ```bash
   curl -X DELETE http://127.0.0.1:8000/api/transactions/1 \
     -H "Authorization: Bearer $TOKEN"
   ```

## Interactive API Documentation

Visit http://127.0.0.1:8000/docs for Swagger UI where you can:

1. **Authorize** - Click "Authorize" button, enter `Bearer YOUR_TOKEN`
2. **Try endpoints** - Expand any endpoint and click "Try it out"
3. **View schemas** - See request/response models
4. **Test in browser** - Execute requests directly from the UI

## Common Issues and Troubleshooting

### Port 8000 Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Kill the process using port 8000
lsof -ti:8000 | xargs kill -9

# Or run on a different port
uvicorn app.main:app --reload --port 8001
```

### Database Connection Errors

**Error:** `could not connect to server: Connection refused`

**Solutions:**

1. **PostgreSQL not running:**
   ```bash
   # macOS
   brew services start postgresql@16

   # Ubuntu/Debian
   sudo systemctl start postgresql
   ```

2. **Wrong DATABASE_URL:**
   - Verify connection string in `.env`
   - Check username, password, host, and database name

3. **Database doesn't exist:**
   ```bash
   psql postgres -c "CREATE DATABASE finance_planner;"
   ```

### JWT Authentication Errors

**Error:** `401 Unauthorized` or `Invalid token`

**Common Causes:**

1. **SECRET_KEY mismatch** - Ensure `.env` SECRET_KEY matches MCP_Auth
2. **Expired token** - Tokens expire after 15 minutes, get a new one
3. **Missing Bearer prefix** - Use `Authorization: Bearer TOKEN`, not just `TOKEN`
4. **MCP_Auth not running** - Start MCP_Auth first to generate tokens

**Solution:**
```bash
# Verify SECRET_KEY matches
grep SECRET_KEY .env
grep SECRET_KEY ../MCP_Auth/.env

# Get fresh token
curl -X POST http://127.0.0.1:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

### Migration Errors

**Error:** `Can't locate revision identified by 'xxxxx'`

**Solution:**
```bash
# Delete and recreate database
rm finance_planner.db  # SQLite
# Or: psql -c "DROP DATABASE finance_planner; CREATE DATABASE finance_planner;" postgres

# Run migrations fresh
alembic upgrade head
```

### Module Not Found Errors

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
uv sync
# Or: pip install -e .

# Verify installation
python -c "import app; print('Success!')"
```

### Test Failures

**Error:** Tests failing with database errors

**Solutions:**

1. **Delete test database:**
   ```bash
   rm test_integration.db  # If it exists
   ```

2. **Reinstall test dependencies:**
   ```bash
   uv sync
   # Or: pip install -e ".[dev]"
   ```

3. **Run specific failing test:**
   ```bash
   pytest tests/test_transactions.py::TestTransactionCreation -v
   ```

### Balance Calculation Issues

**Error:** Account balance doesn't match expected value

**Causes:**
- Transaction created/updated/deleted without service layer (bypassing balance logic)
- Direct database modification

**Solution:**
- Always use API endpoints (not direct DB access)
- Recalculate balance:
  ```python
  # In Python shell
  from app.database import SessionLocal
  from app.repositories.transaction_repository import TransactionRepository

  db = SessionLocal()
  repo = TransactionRepository(db)
  balance = repo.get_account_balance(account_id=1)
  print(f"Actual balance: {balance}")
  ```

## Development Tips

### Without Activating Virtual Environment

You can run commands using full paths:

```bash
# Run server
.venv/bin/uvicorn app.main:app --reload

# Run tests
.venv/bin/pytest

# Run migrations
.venv/bin/alembic upgrade head
```

### Hot Reload Development

The `--reload` flag watches for file changes and automatically restarts the server:

```bash
uvicorn app.main:app --reload
```

Edit any Python file and save - the server restarts automatically.

### Database Inspection

**PostgreSQL:**
```bash
psql finance_planner
\dt                    # List tables
\d users              # Describe users table
SELECT * FROM accounts LIMIT 5;
```

**SQLite:**
```bash
sqlite3 finance_planner.db
.tables               # List tables
.schema accounts      # Show table schema
SELECT * FROM transactions LIMIT 5;
```

### Running Both Servers

Finance Planner requires MCP_Auth running. Use different ports:

**Terminal 1 - MCP_Auth:**
```bash
cd ../MCP_Auth
source .venv/bin/activate
uvicorn main:app --reload --port 8001
```

**Terminal 2 - Finance Planner:**
```bash
cd ../finance_planner
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Monitoring Logs

Set log level in `.env`:
```env
LOG_LEVEL=DEBUG  # For detailed logs
LOG_LEVEL=INFO   # For normal operation
```

View real-time logs in terminal where uvicorn is running.

## Multi-Tenant Security

**Critical:** All API endpoints enforce multi-tenant isolation:
- Users can only see/modify their own accounts and transactions
- Attempting to access another user's data returns 404 (not 403)
- User ID extracted from JWT token, not user input

**Test multi-tenancy:**
```bash
# User 1 creates account
curl -X POST http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $USER1_TOKEN" \
  -d '{"name": "User 1 Account", "account_type": "checking"}'

# User 2 tries to access (will get 404)
curl -X GET http://127.0.0.1:8000/api/accounts/1 \
  -H "Authorization: Bearer $USER2_TOKEN"
```

## Next Steps

1. ✅ Verify server is running: http://127.0.0.1:8000/health
2. ✅ Get JWT token from MCP_Auth
3. ✅ Create your first account
4. ✅ Add transactions and track spending
5. ✅ Explore filtering and search features
6. ✅ Review interactive docs: http://127.0.0.1:8000/docs

## Additional Resources

- **Project Documentation**: See `README.md` and `CLAUDE.md`
- **Implementation Plan**: See `docs/PLAN.md`
- **MCP_Auth Setup**: https://github.com/jtuchinsky/MCP_Auth/blob/main/docs/RUNNING.md
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org
- **Alembic Docs**: https://alembic.sqlalchemy.org

## Support

For issues, bugs, or questions:
- Check this guide first
- Review error messages carefully
- Verify environment configuration
- Ensure MCP_Auth is running and SECRET_KEY matches
- Check that virtual environment is activated
