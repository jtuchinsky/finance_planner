# Two-Terminal Quick Start Tutorial

A step-by-step guide to get Finance Planner and MCP_Auth running and test the API in **5-10 minutes**.

## What You'll Do

1. Start MCP_Auth in Terminal 1 (port 8001)
2. Start Finance Planner in Terminal 2 (port 8000)
3. Register a user and get a JWT token with tenant context from MCP_Auth
4. View your tenant information and members
5. Create and manage shared accounts within your tenant
6. Add transactions and see automatic balance updates
7. Try batch transaction import (1-100 transactions atomically)
8. (Optional) Invite family members to your tenant for collaborative finance tracking

## Prerequisites

Before starting, ensure you have:

- **Python 3.12+** installed
- **Both repositories cloned**:
  - MCP_Auth: https://github.com/jtuchinsky/MCP_Auth
  - finance_planner: https://github.com/jtuchinsky/finance_planner
- **Dependencies installed** in both projects (`uv sync` or `pip install -e .`)
- **Virtual environments created** (`.venv` directory in each project)
- **.env files configured** in both projects

**Time required:** 5-10 minutes

---

## Part 1: Environment Setup (Before Starting)

### Step 1: Verify Both Projects Exist

```bash
# Check MCP_Auth exists
ls ../MCP_Auth

# Check finance_planner exists
ls ../finance_planner
```

### Step 2: Verify .env Files Exist

```bash
# Check MCP_Auth .env
ls ../MCP_Auth/.env

# Check finance_planner .env
ls .env
```

### Step 3: **CRITICAL** - Verify SECRET_KEY Matches

The `SECRET_KEY` **MUST** be identical in both `.env` files for JWT validation to work.

```bash
# Compare SECRET_KEY in both files
echo "MCP_Auth SECRET_KEY:"
grep "^SECRET_KEY=" ../MCP_Auth/.env

echo ""
echo "Finance Planner SECRET_KEY:"
grep "^SECRET_KEY=" .env
```

**They must match!** If they don't:

```bash
# Generate a new shared key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Copy the output and set it in BOTH .env files:
# ../MCP_Auth/.env
# ./env
```

---

## Part 2: Terminal 1 - Start MCP_Auth

Open your first terminal and run these commands:

```bash
┌─ Terminal 1: MCP_Auth (Port 8001) ─────────────────────────────┐
│                                                                  │
│ # 1. Navigate to MCP_Auth directory                            │
│ cd ../MCP_Auth                                                  │
│                                                                  │
│ # 2. Activate virtual environment                              │
│ source .venv/bin/activate                                       │
│                                                                  │
│ # 3. Start the server                                          │
│ uvicorn main:app --reload --port 8001                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### What You Should See

```
INFO:     Will watch for changes in these directories: ['/path/to/MCP_Auth']
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

✅ **MCP_Auth is now running on port 8001**

**Leave this terminal running!** Open a second terminal for Finance Planner.

---

## Part 3: Terminal 2 - Start Finance Planner

Open your second terminal and run these commands:

```bash
┌─ Terminal 2: Finance Planner (Port 8000) ──────────────────────┐
│                                                                  │
│ # 1. Navigate to finance_planner directory                     │
│ cd ../finance_planner                                           │
│                                                                  │
│ # 2. Activate virtual environment                              │
│ source .venv/bin/activate                                       │
│                                                                  │
│ # 3. Start the server                                          │
│ uvicorn app.main:app --reload --port 8000                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### What You Should See

```
INFO:     Will watch for changes in these directories: ['/path/to/finance_planner']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [23456] using StatReload
INFO:     Started server process [23457]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

✅ **Finance Planner is now running on port 8000**

**Leave this terminal running!** Open a third terminal (or new tab in Terminal 2) for API calls.

---

## Part 4: Terminal 3 - Get JWT Token from MCP_Auth

Open a third terminal (or a new tab) for running API commands.

### Step 1: Verify Both Services Are Running

```bash
# Check MCP_Auth health
curl http://127.0.0.1:8001/health

# Check Finance Planner health
curl http://127.0.0.1:8000/health
```

**Expected output:** Both should return status messages or HTTP 200.

### Step 2: Register a User (First Time Only)

```bash
curl -X POST http://127.0.0.1:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "DemoPass123!"
  }'
```

**Expected Response (Success):**
```json
{
  "id": 1,
  "email": "demo@example.com",
  "is_active": true,
  "created_at": "2025-12-29T...",
  "updated_at": "2025-12-29T..."
}
```

**What happens behind the scenes:**
- A new user is created in MCP_Auth
- A new **tenant** (family/household) is automatically created for you
- You are assigned as the **OWNER** of that tenant
- The tenant_id will be included in all JWT tokens

**If user already exists:**
```json
{
  "detail": "Email already registered"
}
```

✅ **This is fine!** Skip to Step 3 if the user already exists.

### Step 3: Login to Get Access Token

```bash
curl -X POST http://127.0.0.1:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "DemoPass123!"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidGVuYW50X2lkIjoiMSIsImV4cCI6MTczNTQ5...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

**What's in the JWT token:**
```json
{
  "sub": "1",           // User ID
  "tenant_id": "1",     // Your tenant ID (family/household)
  "exp": 1735498765     // Expiration timestamp
}
```

The `tenant_id` claim ensures you can only access data belonging to your tenant (family/household).

### Step 4: Store Token in Environment Variable

**Option 1: Manual copy-paste**

Copy the `access_token` value from the response and run:

```bash
export TOKEN="paste-your-token-here"
```

**Option 2: Automatic extraction (recommended)**

```bash
TOKEN=$(curl -X POST http://127.0.0.1:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "DemoPass123!"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

### Step 5: Verify Token is Set

```bash
echo $TOKEN
```

**Expected output:** A long JWT string starting with `eyJ...`

✅ **You now have a valid JWT token!** Token expires in 15 minutes.

---

## Part 5: Tenant Management - View Your Household

Finance Planner uses a multi-tenant architecture where each tenant represents a family or household. All members of a tenant share the same accounts and transactions.

### Test 1: View Your Tenant Information

```bash
curl -X GET http://127.0.0.1:8000/api/tenants/me \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "id": 1,
  "name": "demo@example.com's Tenant",
  "created_at": "2026-01-05T12:00:00",
  "updated_at": "2026-01-05T12:00:00"
}
```

✅ **This shows your tenant (family/household) details!**

### Test 2: View All Tenant Members

```bash
curl -X GET http://127.0.0.1:8000/api/tenants/me/members \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "auth_user_id": "1",
    "role": "owner",
    "created_at": "2026-01-05T12:00:00"
  }
]
```

**Role Hierarchy:**
- **OWNER** (you) - Full control: manage members, change roles, all data operations
- **ADMIN** - Invite/remove members, all data operations
- **MEMBER** - Create/edit/delete accounts & transactions
- **VIEWER** - Read-only access to all data

✅ **You are the OWNER of your tenant!** You can invite family members later.

---

## Part 6: Workflow 1 - Create and Manage Accounts

Now let's create accounts that all tenant members can access.

### Test 1: List Accounts (Should Be Empty Initially)

```bash
curl -X GET http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "items": [],
  "total": 0
}
```

✅ **This proves:** Your JWT token is valid and authentication is working!

### Test 2: Create a Checking Account

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

**Expected Response:**
```json
{
  "id": 1,
  "tenant_id": 1,
  "user_id": 1,
  "name": "Chase Checking",
  "account_type": "checking",
  "balance": 5000.0,
  "created_at": "2025-12-29T12:00:00",
  "updated_at": "2025-12-29T12:00:00"
}
```

✅ **Account created successfully!** This account is now shared with all members of your tenant.

**Common Issues:**

- **307 Temporary Redirect**: Try adding or removing a trailing slash:
  ```bash
  # Try WITHOUT trailing slash
  curl -X POST http://127.0.0.1:8000/api/accounts \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "Chase Checking", "account_type": "checking", "initial_balance": 5000.00}'

  # OR try WITH trailing slash
  curl -X POST http://127.0.0.1:8000/api/accounts/ \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "Chase Checking", "account_type": "checking", "initial_balance": 5000.00}'
  ```

- **401 Unauthorized**: Your token may be expired or invalid. Get a fresh token (Part 4, Step 3-4)

- **Field validation error**: Check that `account_type` is one of: `checking`, `savings`, `credit_card`, `investment`, `loan`, `other`

### Test 3: Create a Savings Account

```bash
curl -X POST http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High-Yield Savings",
    "account_type": "savings",
    "initial_balance": 10000.00
  }'
```

**Expected Response:**
```json
{
  "id": 2,
  "tenant_id": 1,
  "user_id": 1,
  "name": "High-Yield Savings",
  "account_type": "savings",
  "balance": 10000.0,
  "created_at": "2025-12-29T12:01:00",
  "updated_at": "2025-12-29T12:01:00"
}
```

### Test 4: List All Accounts (Should Show 2)

```bash
curl -X GET http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "items": [
    {
      "id": 1,
      "tenant_id": 1,
      "user_id": 1,
      "name": "Chase Checking",
      "account_type": "checking",
      "balance": 5000.0,
      "created_at": "2025-12-29T12:00:00",
      "updated_at": "2025-12-29T12:00:00"
    },
    {
      "id": 2,
      "tenant_id": 1,
      "user_id": 1,
      "name": "High-Yield Savings",
      "account_type": "savings",
      "balance": 10000.0,
      "created_at": "2025-12-29T12:01:00",
      "updated_at": "2025-12-29T12:01:00"
    }
  ],
  "total": 2
}
```

✅ **Both accounts visible to all tenant members!** Total balance: $15,000.00

### Test 5: Get Specific Account Details

```bash
curl -X GET http://127.0.0.1:8000/api/accounts/1 \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "id": 1,
  "tenant_id": 1,
  "user_id": 1,
  "name": "Chase Checking",
  "account_type": "checking",
  "balance": 5000.0,
  "created_at": "2025-12-29T12:00:00",
  "updated_at": "2025-12-29T12:00:00"
}
```

### Test 6: Update Account Name

```bash
curl -X PATCH http://127.0.0.1:8000/api/accounts/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chase Checking - Personal"
  }'
```

**Expected Response:**
```json
{
  "id": 1,
  "tenant_id": 1,
  "user_id": 1,
  "name": "Chase Checking - Personal",
  "account_type": "checking",
  "balance": 5000.0,
  "created_at": "2025-12-29T12:00:00",
  "updated_at": "2025-12-29T12:05:00"
}
```

✅ **Account name updated!** Note the `updated_at` timestamp changed. All tenant members will see the new name.

### Test 7: Delete an Account

```bash
curl -X DELETE http://127.0.0.1:8000/api/accounts/2 \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "message": "Account deleted successfully"
}
```

**Verify deletion:**
```bash
curl -X GET http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "items": [
    {
      "id": 1,
      "tenant_id": 1,
      "user_id": 1,
      "name": "Chase Checking - Personal",
      "account_type": "checking",
      "balance": 5000.0,
      "created_at": "2025-12-29T12:00:00",
      "updated_at": "2025-12-29T12:05:00"
    }
  ],
  "total": 1
}
```

✅ **Savings account deleted!** Only checking account remains.

---

## Part 7: Workflow 2 - Transaction Management

Now let's add some transactions and see automatic balance updates!

### Test 1: Add a Grocery Transaction (Expense)

```bash
curl -X POST http://127.0.0.1:8000/api/transactions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "amount": -150.00,
    "date": "2026-01-03",
    "category": "groceries",
    "merchant": "Whole Foods",
    "description": "Weekly grocery shopping"
  }'
```

**Expected Response:**
```json
{
  "id": 1,
  "account_id": 1,
  "amount": -150.0,
  "date": "2026-01-03",
  "category": "groceries",
  "merchant": "Whole Foods",
  "description": "Weekly grocery shopping",
  "location": null,
  "tags": [],
  "der_category": null,
  "der_merchant": null,
  "created_at": "2026-01-03T12:00:00",
  "updated_at": "2026-01-03T12:00:00"
}
```

**Check updated balance:**
```bash
curl -X GET http://127.0.0.1:8000/api/accounts/1 \
  -H "Authorization: Bearer $TOKEN"
```

**Expected balance:** `4850.00` (5000.00 - 150.00)

✅ **Balance automatically updated!**

### Test 2: Add Income Transaction

```bash
curl -X POST http://127.0.0.1:8000/api/transactions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "amount": 2500.00,
    "date": "2026-01-01",
    "category": "income",
    "description": "Monthly salary deposit"
  }'
```

**Expected balance after this:** `7350.00` (4850.00 + 2500.00)

### Test 3: List All Transactions

```bash
curl -X GET "http://127.0.0.1:8000/api/transactions?account_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "transactions": [
    {
      "id": 2,
      "account_id": 1,
      "amount": 2500.0,
      "date": "2026-01-01",
      "category": "income",
      "description": "Monthly salary deposit",
      ...
    },
    {
      "id": 1,
      "account_id": 1,
      "amount": -150.0,
      "date": "2026-01-03",
      "category": "groceries",
      ...
    }
  ],
  "total": 2,
  "limit": 100,
  "offset": 0
}
```

### Test 4: Batch Transaction Import (NEW!)

Import multiple transactions at once (1-100 transactions atomically):

```bash
curl -X POST http://127.0.0.1:8000/api/transactions/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "transactions": [
      {"amount": -50.00, "date": "2026-01-02", "category": "gas", "merchant": "Shell"},
      {"amount": -30.00, "date": "2026-01-02", "category": "dining", "merchant": "Chipotle"},
      {"amount": -80.00, "date": "2026-01-03", "category": "utilities", "merchant": "PG&E"},
      {"amount": -1200.00, "date": "2026-01-01", "category": "rent", "merchant": "Landlord"}
    ]
  }'
```

**Expected Response:**
```json
{
  "transactions": [
    { "id": 3, "amount": -50.0, "category": "gas", ... },
    { "id": 4, "amount": -30.0, "category": "dining", ... },
    { "id": 5, "amount": -80.0, "category": "utilities", ... },
    { "id": 6, "amount": -1200.0, "category": "rent", ... }
  ],
  "account_balance": 5990.0,
  "total_amount": -1360.0,
  "count": 4
}
```

✅ **4 transactions created atomically!** Balance updated once: `5990.00`

**Benefits of batch import:**
- ⚡ Much faster than individual transactions (single database commit)
- 🔒 All-or-nothing atomicity (if one fails, all rollback)
- 📊 Perfect for importing CSV data or historical transactions
- 🎯 Supports 1-100 transactions per batch

### Test 5: Filter Transactions by Category

```bash
curl -X GET "http://127.0.0.1:8000/api/transactions?category=groceries" \
  -H "Authorization: Bearer $TOKEN"
```

### Test 6: Filter by Date Range

```bash
curl -X GET "http://127.0.0.1:8000/api/transactions?start_date=2026-01-01&end_date=2026-01-31" \
  -H "Authorization: Bearer $TOKEN"
```

### Test 7: Update Transaction Amount

```bash
curl -X PATCH http://127.0.0.1:8000/api/transactions/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": -175.00
  }'
```

✅ **Balance automatically recalculated!** Old amount removed, new amount added.

### Test 8: Delete Transaction

```bash
curl -X DELETE http://127.0.0.1:8000/api/transactions/1 \
  -H "Authorization: Bearer $TOKEN"
```

✅ **Transaction deleted and balance updated automatically!**

---

## Part 8: Troubleshooting Common Issues

### Issue 1: 307 Temporary Redirect

**Error seen in Terminal 1 or 2:**
```
127.0.0.1:62647 - "POST /api/accounts HTTP/1.1" 307 Temporary Redirect
```

**Cause:** FastAPI trailing slash mismatch. The endpoint may be defined with or without a trailing slash.

**Solution:** Try both URL formats:

```bash
# WITHOUT trailing slash
curl -X POST http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "account_type": "checking", "initial_balance": 100}'

# WITH trailing slash
curl -X POST http://127.0.0.1:8000/api/accounts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "account_type": "checking", "initial_balance": 100}'
```

**Pro tip:** Use the interactive API docs at http://127.0.0.1:8000/docs to see the exact URL format.

### Issue 2: 401 Unauthorized

**Error:**
```json
{
  "detail": "Could not validate credentials"
}
```

**Causes:**

1. **Token not set or expired** (tokens expire after 15 minutes)
   ```bash
   # Check if token is set
   echo $TOKEN

   # Get a fresh token
   TOKEN=$(curl -X POST http://127.0.0.1:8001/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "demo@example.com", "password": "DemoPass123!"}' \
     | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
   ```

2. **SECRET_KEY mismatch** between MCP_Auth and Finance Planner
   ```bash
   # Verify keys match
   grep "^SECRET_KEY=" ../MCP_Auth/.env
   grep "^SECRET_KEY=" .env
   ```

   If they don't match, set them to the same value and restart both services.

3. **Missing tenant_id in JWT token** (if you're using an old MCP_Auth version)

   Finance Planner requires JWT tokens with a `tenant_id` claim. Verify your token contains it:
   ```bash
   # Decode token (requires jq or use https://jwt.io)
   echo $TOKEN | cut -d'.' -f2 | base64 -d | python3 -m json.tool
   ```

   Expected output should include:
   ```json
   {
     "sub": "1",
     "tenant_id": "1",
     "exp": ...
   }
   ```

   If `tenant_id` is missing, update MCP_Auth to the latest version that includes multi-tenant support.

4. **Missing "Bearer" prefix**
   ```bash
   # ✅ Correct
   curl -H "Authorization: Bearer $TOKEN" ...

   # ❌ Wrong
   curl -H "Authorization: $TOKEN" ...
   ```

### Issue 3: MCP_Auth Not Running

**Error:**
```
curl: (7) Failed to connect to 127.0.0.1 port 8001: Connection refused
```

**Solution:** Start MCP_Auth in Terminal 1 (see Part 2)

**Verify it's running:**
```bash
curl http://127.0.0.1:8001/health
```

### Issue 4: Finance Planner Not Running

**Error:**
```
curl: (7) Failed to connect to 127.0.0.1 port 8000: Connection refused
```

**Solution:** Start Finance Planner in Terminal 2 (see Part 3)

**Verify it's running:**
```bash
curl http://127.0.0.1:8000/health
```

### Issue 5: Token Expired

**Error:**
```json
{
  "detail": "Token has expired"
}
```

**Solution:** Get a fresh token (they expire after 15 minutes):

```bash
TOKEN=$(curl -X POST http://127.0.0.1:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "DemoPass123!"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo $TOKEN
```

---

## Part 9: Complete Example Session

Here's a full copy-paste example showing the entire workflow:

```bash
#──────────────────────────────────────────────────────────────────
# Terminal 1 - MCP_Auth
#──────────────────────────────────────────────────────────────────
cd ../MCP_Auth
source .venv/bin/activate
uvicorn main:app --reload --port 8001
# Leave running...


#──────────────────────────────────────────────────────────────────
# Terminal 2 - Finance Planner
#──────────────────────────────────────────────────────────────────
cd ../finance_planner
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
# Leave running...


#──────────────────────────────────────────────────────────────────
# Terminal 3 - API Calls
#──────────────────────────────────────────────────────────────────

# 1. Verify both services are healthy
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8000/health

# 2. Register a user (first time only)
curl -X POST http://127.0.0.1:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "DemoPass123!"}'

# 3. Login and store token
TOKEN=$(curl -X POST http://127.0.0.1:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "DemoPass123!"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 4. Verify token is set
echo $TOKEN

# 5. List accounts (should be empty)
curl -X GET http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN"

# 6. Create checking account
curl -X POST http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Checking",
    "account_type": "checking",
    "initial_balance": 1000.00
  }'

# 7. Create savings account
curl -X POST http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Savings",
    "account_type": "savings",
    "initial_balance": 5000.00
  }'

# 8. List all accounts (should show 2)
curl -X GET http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN"

# 9. Get specific account
curl -X GET http://127.0.0.1:8000/api/accounts/1 \
  -H "Authorization: Bearer $TOKEN"

# 10. Update account name
curl -X PATCH http://127.0.0.1:8000/api/accounts/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Primary Checking"}'

# 11. Delete an account
curl -X DELETE http://127.0.0.1:8000/api/accounts/2 \
  -H "Authorization: Bearer $TOKEN"

# 12. Verify deletion
curl -X GET http://127.0.0.1:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN"
```

---

## Part 10: Next Steps

Congratulations! You've successfully:
- ✅ Started both MCP_Auth and Finance Planner
- ✅ Registered a user and obtained a JWT token with tenant_id
- ✅ Viewed your tenant information and role
- ✅ Created, listed, updated, and deleted shared accounts
- ✅ Added transactions with automatic balance updates
- ✅ Tried batch transaction import (1-100 transactions atomically)

### Explore More

**Interactive API Documentation:**
Visit http://127.0.0.1:8000/docs for Swagger UI where you can:
- Try all endpoints in your browser
- See request/response schemas
- Test with the "Try it out" button

**Tenant Management:**
Invite family members to collaborate on finances:
```bash
# Invite a family member (ADMIN/OWNER only)
curl -X POST http://127.0.0.1:8000/api/tenants/me/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"auth_user_id": "spouse-user-id", "role": "member"}'

# Update a member's role (OWNER only)
curl -X PATCH http://127.0.0.1:8000/api/tenants/me/members/2/role \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'

# Remove a member (ADMIN/OWNER only)
curl -X DELETE http://127.0.0.1:8000/api/tenants/me/members/2 \
  -H "Authorization: Bearer $TOKEN"
```

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for complete tenant management documentation.

**Transaction Management:**
See [RUNNING.md - Workflow 2](RUNNING.md#workflow-2-create-and-track-transactions) for:
- Creating income/expense transactions
- Automatic balance updates
- Transaction filtering and search
- Date ranges, categories, merchants, tags

**Advanced Filtering:**
See [RUNNING.md - Workflow 3](RUNNING.md#workflow-3-filter-and-search-transactions) for:
- Filter by date range, category, merchant
- Tag-based filtering
- Pagination and sorting

**Production Deployment:**
See [RUNNING.md - Production Deployment Options](RUNNING.md#production-deployment-options) for:
- systemd setup (Linux)
- Supervisor configuration
- Docker Compose
- nginx reverse proxy

**Troubleshooting:**
See [RUNNING.md - Common Issues](RUNNING.md#common-issues-and-troubleshooting) for:
- Multi-service specific issues
- SECRET_KEY problems
- Database connection issues
- Complete troubleshooting guide

---

## Summary

**Terminal 1:** MCP_Auth running on port 8001
**Terminal 2:** Finance Planner running on port 8000
**Terminal 3:** API testing with curl commands

**Key Points:**
- SECRET_KEY must match in both .env files
- JWT tokens expire after 15 minutes and must include `tenant_id` claim
- MCP_Auth must start before Finance Planner
- Use `Authorization: Bearer $TOKEN` header for all Finance Planner API calls
- Watch for 307 redirects (trailing slash issues)

**Multi-Tenant Architecture:**
- Each user belongs to a tenant (family/household)
- All accounts and transactions are shared within the tenant
- Role-based access control: OWNER > ADMIN > MEMBER > VIEWER
- You are the OWNER of your tenant with full control

**Questions or issues?** Check [RUNNING.md](RUNNING.md) for comprehensive documentation.
