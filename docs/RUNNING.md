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

### Multi-Service Issues

Problems specific to running both MCP_Auth and Finance Planner together.

#### SECRET_KEY Mismatch Between Services

**Error:** JWT tokens work with MCP_Auth but fail validation in Finance Planner with 401 Unauthorized

**Symptoms:**
- Can successfully login to MCP_Auth and receive token
- Using that token with Finance Planner returns `401 Unauthorized` or `Invalid token`
- Logs show "Could not validate credentials"

**Solution:**
```bash
# 1. Verify SECRET_KEY matches in both .env files
echo "MCP_Auth SECRET_KEY:"
grep "^SECRET_KEY=" ../MCP_Auth/.env

echo "Finance Planner SECRET_KEY:"
grep "^SECRET_KEY=" .env

# 2. If they don't match, generate a new shared key
NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 3. Update both files with the same key
sed -i.bak "s/^SECRET_KEY=.*/SECRET_KEY=$NEW_KEY/" ../MCP_Auth/.env
sed -i.bak "s/^SECRET_KEY=.*/SECRET_KEY=$NEW_KEY/" .env

# 4. Restart both services for changes to take effect
```

#### Service Startup Order Problems

**Error:** Finance Planner starts but JWT validation fails because MCP_Auth isn't ready yet

**Symptoms:**
- Finance Planner starts successfully
- But all authenticated requests fail with 401
- MCP_Auth is still starting up

**Solution:**
```bash
# Always start MCP_Auth first and verify it's healthy
cd ../MCP_Auth
uvicorn main:app --reload --port 8001 &

# Wait for MCP_Auth to be ready
sleep 3
curl -f http://127.0.0.1:8001/health || { echo "MCP_Auth not ready"; exit 1; }

# Now start Finance Planner
cd ../finance_planner
uvicorn app.main:app --reload --port 8000
```

For production with systemd, use dependency ordering (see Production Deployment Options above).

#### Port Conflicts When Running Both Services

**Error:** `Address already in use` when trying to start second service

**Common Causes:**
1. **Both services configured for same port** - Check `.env` or command-line args
2. **Another process using the port** - Find and kill it
3. **Previous instance didn't shut down cleanly** - Kill stale process

**Solution:**
```bash
# Check what's using ports 8000 and 8001
lsof -i :8000
lsof -i :8001

# Kill processes if needed
lsof -ti:8000 | xargs kill -9
lsof -ti:8001 | xargs kill -9

# Or use different ports
# MCP_Auth:
uvicorn main:app --reload --port 8001

# Finance Planner:
uvicorn app.main:app --reload --port 8000
```

#### Both Services Cannot Connect to Database

**Error:** Multiple `could not connect to server` errors from both services

**Causes:**
- PostgreSQL not running
- Connection pool exhausted (both services using too many connections)
- Firewall blocking connections

**Solutions:**

1. **Check PostgreSQL is running:**
   ```bash
   # macOS
   brew services list | grep postgresql
   brew services start postgresql@16

   # Linux
   sudo systemctl status postgresql
   sudo systemctl start postgresql
   ```

2. **Check connection pool settings:**
   ```bash
   # PostgreSQL max connections (default 100)
   psql postgres -c "SHOW max_connections;"

   # Ensure both services' pools don't exceed this
   # finance_planner/.env
   DB_POOL_SIZE=10
   DB_MAX_OVERFLOW=10  # Total: 20 per service

   # mcp_auth/.env (if using PostgreSQL)
   DB_POOL_SIZE=10
   DB_MAX_OVERFLOW=10

   # Total usage: ~40 connections (well under 100 limit)
   ```

3. **Verify DATABASE_URL in both services:**
   ```bash
   grep DATABASE_URL .env
   grep DATABASE_URL ../MCP_Auth/.env
   ```

#### Process Won't Stop Cleanly

**Error:** Services don't respond to Ctrl+C or keep running after terminal closes

**Symptoms:**
- Pressing Ctrl+C doesn't stop the process
- Closing terminal leaves services running
- Port still in use after "stopping" services

**Solutions:**

1. **Find the process IDs:**
   ```bash
   # Find processes
   ps aux | grep uvicorn

   # Or by port
   lsof -ti:8000  # Finance Planner
   lsof -ti:8001  # MCP_Auth
   ```

2. **Gracefully stop (SIGTERM):**
   ```bash
   kill <PID>

   # Or by port
   lsof -ti:8000 | xargs kill
   lsof -ti:8001 | xargs kill
   ```

3. **Force stop (SIGKILL):**
   ```bash
   kill -9 <PID>

   # Or by port
   lsof -ti:8000 | xargs kill -9
   lsof -ti:8001 | xargs kill -9
   ```

4. **Prevent background processes:**
   ```bash
   # Don't use & or nohup for development
   # Use tmux or separate terminals instead

   # If you must use background processes, track PIDs
   uvicorn app.main:app --port 8000 &
   echo $! > /tmp/finance_planner.pid

   # Stop later with:
   kill $(cat /tmp/finance_planner.pid)
   ```

#### Token Works in MCP_Auth but Not Finance Planner

**Error:** Login successful, token received, but Finance Planner rejects it

**Diagnostic Steps:**

1. **Verify token contents:**
   ```bash
   # Install jwt-cli (optional): pip install pyjwt
   python3 << 'EOF'
   import sys
   from jose import jwt

   token = "YOUR_TOKEN_HERE"
   try:
       # Decode without verification to see contents
       payload = jwt.get_unverified_claims(token)
       print("Token payload:", payload)
       print("Subject (sub):", payload.get('sub'))
       print("Expiration:", payload.get('exp'))
   except Exception as e:
       print(f"Error decoding token: {e}")
   EOF
   ```

2. **Check token hasn't expired:**
   - Tokens expire after 15 minutes by default
   - Get a fresh token if expired

3. **Verify SECRET_KEY matches:**
   ```bash
   # Use the verify-config.sh script
   ./verify-config.sh
   ```

4. **Check Authorization header format:**
   ```bash
   # ✅ Correct
   curl -H "Authorization: Bearer eyJhbGc..." http://127.0.0.1:8000/api/accounts

   # ❌ Wrong (missing "Bearer")
   curl -H "Authorization: eyJhbGc..." http://127.0.0.1:8000/api/accounts

   # ❌ Wrong (case sensitive)
   curl -H "authorization: Bearer eyJhbGc..." http://127.0.0.1:8000/api/accounts
   ```

#### Different Dependency Versions Between Services

**Error:** One service works fine but the other has import errors or version conflicts

**Symptoms:**
- `ImportError` or `ModuleNotFoundError` in one service
- Different behavior between services
- Dependency version warnings

**Solution:**
```bash
# Each service has its own virtual environment
# Make sure you're activating the correct one

# For MCP_Auth
cd ../MCP_Auth
source .venv/bin/activate
pip list  # Check installed packages

# For Finance Planner
cd ../finance_planner
source .venv/bin/activate
pip list  # Check installed packages

# Reinstall dependencies if needed
uv sync  # or: pip install -e .
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

### Running Both Services Together

Finance Planner requires MCP_Auth for JWT token generation and validation. This section covers running both services on the same host for development and testing.

#### Method 1: Two Terminals (Recommended for Development)

The simplest approach for development - run each service in its own terminal window.

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

**Verify Both Services:**
```bash
# Check MCP_Auth health
curl http://127.0.0.1:8001/health

# Check Finance Planner health
curl http://127.0.0.1:8000/health
```

#### Method 2: tmux Session Manager

Use tmux to manage both services in a single terminal with split panes.

**Create and configure tmux session:**
```bash
# Start new tmux session
tmux new -s finance-stack

# Split window horizontally
# Ctrl+b then "

# In first pane (top), start MCP_Auth:
cd ../MCP_Auth
source .venv/bin/activate
uvicorn main:app --reload --port 8001

# Switch to second pane (Ctrl+b then arrow down)
# Start Finance Planner:
cd ../finance_planner
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Navigate between panes: Ctrl+b then arrow keys
# Detach from session: Ctrl+b then d
# Reattach later: tmux attach -t finance-stack
# Kill session: tmux kill-session -t finance-stack
```

#### Method 3: Simple Startup Script

Create a startup script to launch both services in the background.

**Create `start-services.sh`:**
```bash
#!/bin/bash

echo "Starting Finance Stack..."

# Start MCP_Auth
cd ../MCP_Auth
source .venv/bin/activate
nohup uvicorn main:app --port 8001 > logs/mcp_auth.log 2>&1 &
MCP_AUTH_PID=$!
echo "MCP_Auth started (PID: $MCP_AUTH_PID)"

# Wait for MCP_Auth to be ready
sleep 2
if curl -s http://127.0.0.1:8001/health > /dev/null; then
    echo "✓ MCP_Auth is healthy"
else
    echo "✗ MCP_Auth failed to start"
    exit 1
fi

# Start Finance Planner
cd ../finance_planner
source .venv/bin/activate
nohup uvicorn app.main:app --port 8000 > logs/finance_planner.log 2>&1 &
FINANCE_PID=$!
echo "Finance Planner started (PID: $FINANCE_PID)"

# Wait for Finance Planner to be ready
sleep 2
if curl -s http://127.0.0.1:8000/health > /dev/null; then
    echo "✓ Finance Planner is healthy"
else
    echo "✗ Finance Planner failed to start"
    exit 1
fi

echo ""
echo "All services running:"
echo "  MCP_Auth:        http://127.0.0.1:8001 (PID: $MCP_AUTH_PID)"
echo "  Finance Planner: http://127.0.0.1:8000 (PID: $FINANCE_PID)"
echo ""
echo "To stop services:"
echo "  kill $MCP_AUTH_PID $FINANCE_PID"
```

**Make executable and run:**
```bash
chmod +x start-services.sh
./start-services.sh
```

#### Method 4: Combined Log Monitoring

Monitor logs from both services simultaneously using multitail (if installed):

```bash
# Install multitail (macOS)
brew install multitail

# Watch both service logs
multitail -l "cd ../MCP_Auth && source .venv/bin/activate && uvicorn main:app --reload --port 8001" \
          -l "cd ../finance_planner && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000"
```

Or use GNU parallel:
```bash
# Both services with color-coded output
parallel -u ::: \
  "cd ../MCP_Auth && source .venv/bin/activate && uvicorn main:app --reload --port 8001 2>&1 | sed 's/^/[MCP_Auth] /'" \
  "cd ../finance_planner && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000 2>&1 | sed 's/^/[Finance] /'"
```

### Monitoring Logs

Set log level in `.env`:
```env
LOG_LEVEL=DEBUG  # For detailed logs
LOG_LEVEL=INFO   # For normal operation
```

View real-time logs in terminal where uvicorn is running.

## Shared Configuration Management

### Critical: SECRET_KEY Coordination

Both services MUST use the same `SECRET_KEY` for JWT token validation to work.

**Generate a shared secret key:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Set in both `.env` files:**

`../MCP_Auth/.env`:
```env
SECRET_KEY=your-generated-secret-key-here
```

`../finance_planner/.env`:
```env
SECRET_KEY=your-generated-secret-key-here  # MUST match MCP_Auth
```

### Verification Script

Create a script to verify configuration matches between services:

**Create `verify-config.sh`:**
```bash
#!/bin/bash

echo "Verifying shared configuration..."

# Extract SECRET_KEY from both .env files
MCP_KEY=$(grep "^SECRET_KEY=" ../MCP_Auth/.env 2>/dev/null | cut -d'=' -f2)
FINANCE_KEY=$(grep "^SECRET_KEY=" .env 2>/dev/null | cut -d'=' -f2)

# Check if keys exist
if [ -z "$MCP_KEY" ]; then
    echo "✗ SECRET_KEY not found in MCP_Auth/.env"
    exit 1
fi

if [ -z "$FINANCE_KEY" ]; then
    echo "✗ SECRET_KEY not found in finance_planner/.env"
    exit 1
fi

# Compare keys
if [ "$MCP_KEY" = "$FINANCE_KEY" ]; then
    echo "✓ SECRET_KEY matches between services"
else
    echo "✗ SECRET_KEY mismatch!"
    echo "  MCP_Auth:        ${MCP_KEY:0:20}..."
    echo "  Finance Planner: ${FINANCE_KEY:0:20}..."
    exit 1
fi

echo "✓ Configuration verified"
```

**Run verification:**
```bash
chmod +x verify-config.sh
./verify-config.sh
```

### Other Coordinated Settings

**CORS Origins:**
If both services need to accept requests from the same frontend:

```env
# Both .env files
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
CORS_ALLOW_CREDENTIALS=true
```

**Database Configuration:**
Ensure database connection pools don't exceed limits if both services share a database server:

```env
# finance_planner/.env
DB_POOL_SIZE=10      # Adjust based on total connections available
DB_MAX_OVERFLOW=20

# mcp_auth/.env (if applicable)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

## Health Checks and Startup Verification

### Testing Both Services are Running

**Quick health check:**
```bash
curl -s http://127.0.0.1:8001/health && echo " ✓ MCP_Auth healthy"
curl -s http://127.0.0.1:8000/health && echo " ✓ Finance Planner healthy"
```

**Detailed status check script:**

**Create `check-services.sh`:**
```bash
#!/bin/bash

check_service() {
    local name=$1
    local url=$2

    if curl -s -f "$url" > /dev/null 2>&1; then
        echo "✓ $name is running ($url)"
        return 0
    else
        echo "✗ $name is not accessible ($url)"
        return 1
    fi
}

echo "Checking Finance Stack services..."
echo ""

check_service "MCP_Auth" "http://127.0.0.1:8001/health"
MCP_STATUS=$?

check_service "Finance Planner" "http://127.0.0.1:8000/health"
FINANCE_STATUS=$?

echo ""

if [ $MCP_STATUS -eq 0 ] && [ $FINANCE_STATUS -eq 0 ]; then
    echo "✓ All services operational"
    exit 0
else
    echo "✗ Some services are down"
    echo ""
    echo "Troubleshooting:"
    if [ $MCP_STATUS -ne 0 ]; then
        echo "  - Start MCP_Auth: cd ../MCP_Auth && uvicorn main:app --reload --port 8001"
    fi
    if [ $FINANCE_STATUS -ne 0 ]; then
        echo "  - Start Finance Planner: uvicorn app.main:app --reload --port 8000"
    fi
    exit 1
fi
```

### End-to-End Integration Test

Test the complete authentication flow between services:

```bash
# 1. Register a test user in MCP_Auth
curl -X POST http://127.0.0.1:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPassword123!"}'

# 2. Login to get JWT token
TOKEN=$(curl -X POST http://127.0.0.1:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPassword123!"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 3. Use token with Finance Planner
curl -X GET http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN"

# If successful, you'll see: {"items": [], "total": 0}
# This confirms JWT validation is working between services
```

## Production Deployment Options

### Option 1: systemd (Linux Production)

systemd is the standard init system for modern Linux distributions. This setup includes automatic startup, restart on failure, and dependency management.

**1. Create MCP_Auth service file:**

`/etc/systemd/system/mcp-auth.service`:
```ini
[Unit]
Description=MCP_Auth Authentication Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/MCP_Auth
Environment="PATH=/var/www/MCP_Auth/.venv/bin"
EnvironmentFile=/var/www/MCP_Auth/.env
ExecStart=/var/www/MCP_Auth/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4

Restart=always
RestartSec=10
StandardOutput=append:/var/log/mcp_auth/access.log
StandardError=append:/var/log/mcp_auth/error.log

[Install]
WantedBy=multi-user.target
```

**2. Create Finance Planner service file:**

`/etc/systemd/system/finance-planner.service`:
```ini
[Unit]
Description=Finance Planner API Service
After=network.target postgresql.service mcp-auth.service
Requires=mcp-auth.service
Wants=postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/finance_planner
Environment="PATH=/var/www/finance_planner/.venv/bin"
EnvironmentFile=/var/www/finance_planner/.env
ExecStart=/var/www/finance_planner/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

Restart=always
RestartSec=10
StandardOutput=append:/var/log/finance_planner/access.log
StandardError=append:/var/log/finance_planner/error.log

[Install]
WantedBy=multi-user.target
```

**3. Create log directories:**
```bash
sudo mkdir -p /var/log/mcp_auth
sudo mkdir -p /var/log/finance_planner
sudo chown www-data:www-data /var/log/mcp_auth
sudo chown www-data:www-data /var/log/finance_planner
```

**4. Enable and start services:**
```bash
# Reload systemd to recognize new services
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable mcp-auth
sudo systemctl enable finance-planner

# Start services (MCP_Auth starts first due to dependency)
sudo systemctl start mcp-auth
sudo systemctl start finance-planner

# Check status
sudo systemctl status mcp-auth
sudo systemctl status finance-planner
```

**5. Manage services:**
```bash
# Restart both services
sudo systemctl restart mcp-auth finance-planner

# Stop services
sudo systemctl stop finance-planner  # Stop dependent first
sudo systemctl stop mcp-auth

# View logs
sudo journalctl -u mcp-auth -f         # Follow MCP_Auth logs
sudo journalctl -u finance-planner -f  # Follow Finance Planner logs
sudo journalctl -u mcp-auth -u finance-planner -f  # Both together
```

### Option 2: Supervisor

Supervisor is a cross-platform process manager. Good for servers without systemd.

**1. Install Supervisor:**
```bash
# Ubuntu/Debian
sudo apt-get install supervisor

# macOS
brew install supervisor
```

**2. Create supervisor configuration:**

`/etc/supervisor/conf.d/finance-stack.conf`:
```ini
[group:finance-stack]
programs=mcp-auth,finance-planner
priority=999

[program:mcp-auth]
command=/var/www/MCP_Auth/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
directory=/var/www/MCP_Auth
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/mcp_auth.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=10
environment=PATH="/var/www/MCP_Auth/.venv/bin"
priority=1

[program:finance-planner]
command=/var/www/finance_planner/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/var/www/finance_planner
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/finance_planner.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=10
environment=PATH="/var/www/finance_planner/.venv/bin"
priority=2
```

**3. Reload and start:**
```bash
# Reload supervisor configuration
sudo supervisorctl reread
sudo supervisorctl update

# Start the group (both services)
sudo supervisorctl start finance-stack:*

# Check status
sudo supervisorctl status

# Manage services
sudo supervisorctl restart finance-stack:*   # Restart both
sudo supervisorctl stop finance-stack:*      # Stop both
sudo supervisorctl tail -f mcp-auth          # View logs
```

### Option 3: Docker Compose (Future)

Docker Compose template for containerized deployment. Note: Dockerfiles don't exist yet in either project.

**Example `docker-compose.yml` (template for future use):**
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: finance_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: finance_planner
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U finance_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  mcp-auth:
    build:
      context: ../MCP_Auth
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${MCP_AUTH_DATABASE_URL}
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  finance-planner:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      mcp-auth:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

**Usage (when Dockerfiles are created):**
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop all services
docker-compose down
```

### Option 4: Manual Process Management

For simple deployments without systemd or supervisor.

**Create `start.sh`:**
```bash
#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_DIR="$SCRIPT_DIR/pids"
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$PID_DIR" "$LOG_DIR"

# Start MCP_Auth
cd ../MCP_Auth
source .venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8001 \
  >> "$LOG_DIR/mcp_auth.log" 2>&1 &
echo $! > "$PID_DIR/mcp_auth.pid"
echo "Started MCP_Auth (PID: $!)"

# Wait for MCP_Auth to be ready
sleep 3

# Start Finance Planner
cd "$SCRIPT_DIR"
source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  >> "$LOG_DIR/finance_planner.log" 2>&1 &
echo $! > "$PID_DIR/finance_planner.pid"
echo "Started Finance Planner (PID: $!)"
```

**Create `stop.sh`:**
```bash
#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_DIR="$SCRIPT_DIR/pids"

# Stop Finance Planner first
if [ -f "$PID_DIR/finance_planner.pid" ]; then
    PID=$(cat "$PID_DIR/finance_planner.pid")
    kill $PID 2>/dev/null && echo "Stopped Finance Planner (PID: $PID)"
    rm "$PID_DIR/finance_planner.pid"
fi

# Stop MCP_Auth
if [ -f "$PID_DIR/mcp_auth.pid" ]; then
    PID=$(cat "$PID_DIR/mcp_auth.pid")
    kill $PID 2>/dev/null && echo "Stopped MCP_Auth (PID: $PID)"
    rm "$PID_DIR/mcp_auth.pid"
fi
```

**Create `restart.sh`:**
```bash
#!/bin/bash

./stop.sh
sleep 2
./start.sh
```

**Usage:**
```bash
chmod +x start.sh stop.sh restart.sh

./start.sh    # Start both services
./stop.sh     # Stop both services
./restart.sh  # Restart both services
```

## Reverse Proxy Setup with nginx

For production, use nginx as a reverse proxy to:
- Serve both services on standard ports (80/443)
- Handle SSL/TLS termination
- Route requests by path
- Add security headers

### nginx Configuration

**Create `/etc/nginx/sites-available/finance-stack`:**
```nginx
upstream mcp_auth {
    server 127.0.0.1:8001;
}

upstream finance_planner {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.yourDomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourDomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.yourDomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourDomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # MCP_Auth routes (/auth/*)
    location /auth {
        proxy_pass http://mcp_auth;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers (if needed)
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;

        if ($request_method = OPTIONS) {
            return 204;
        }
    }

    # Finance Planner routes (/api/*)
    location /api {
        proxy_pass http://finance_planner;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers (if needed)
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, PATCH, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;

        if ($request_method = OPTIONS) {
            return 204;
        }
    }

    # Health checks (direct, no /api prefix)
    location /health {
        proxy_pass http://finance_planner/health;
        access_log off;
    }

    location /auth/health {
        proxy_pass http://mcp_auth/health;
        access_log off;
    }
}
```

**Enable and test:**
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/finance-stack /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

**Access services through nginx:**
```bash
# Authentication
curl https://api.yourdomain.com/auth/register
curl https://api.yourdomain.com/auth/login

# Finance Planner
curl https://api.yourdomain.com/api/accounts \
  -H "Authorization: Bearer $TOKEN"

# Health checks
curl https://api.yourdomain.com/health
curl https://api.yourdomain.com/auth/health
```

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
