# Finance Planner User Manual

Welcome to Finance Planner! This guide will help you manage your household or family finances effectively using our multi-tenant finance tracking system.

## Table of Contents

- [What is Finance Planner?](#what-is-finance-planner)
- [Key Concepts](#key-concepts)
- [Getting Started](#getting-started)
- [Managing Your Household (Tenant)](#managing-your-household-tenant)
- [Managing Accounts](#managing-accounts)
- [Tracking Transactions](#tracking-transactions)
- [Common Workflows](#common-workflows)
- [Tips & Best Practices](#tips--best-practices)
- [Troubleshooting](#troubleshooting)
- [Frequently Asked Questions](#frequently-asked-questions)

---

## What is Finance Planner?

Finance Planner is a collaborative household finance management system that allows families and households to:

- **Track multiple accounts** (checking, savings, credit cards, investments)
- **Record all transactions** with detailed categorization
- **Share finances** with family members or housemates
- **Control access** with role-based permissions
- **Stay organized** with centralized financial data
- **Import bulk data** from bank statements or CSV files

Unlike personal finance apps, Finance Planner is designed for **shared household finances** where multiple people need access to the same accounts with different permission levels.

---

## Key Concepts

### Tenants (Households)

A **Tenant** represents a family, household, or any group sharing finances. Think of it as your "family financial space" where:

- All accounts and transactions are stored
- All members can view the data (based on their role)
- Complete isolation from other households

**Examples:**
- "Smith Family" - parents and adult children managing household finances
- "Roommates 2026" - housemates splitting rent and utilities
- "Personal Finances" - individual managing their own accounts

### Roles & Permissions

Finance Planner has four permission levels:

| Role | Can View | Can Edit/Create | Can Manage Members | Use Case |
|------|----------|-----------------|-------------------|----------|
| **OWNER** | ✅ Everything | ✅ Everything | ✅ Yes (all actions) | Household head, account creator |
| **ADMIN** | ✅ Everything | ✅ Everything | ✅ Yes (limited) | Co-manager, spouse |
| **MEMBER** | ✅ Everything | ✅ Accounts & Transactions | ❌ No | Family member with full access |
| **VIEWER** | ✅ Everything | ❌ Read-only | ❌ No | Accountant, child, read-only access |

**Permission Details:**

- **OWNER** (Full Control):
  - Create/edit/delete accounts and transactions
  - Invite and remove members
  - Change member roles (including promoting to OWNER)
  - Update household name
  - There's typically one OWNER per household

- **ADMIN** (Co-Manager):
  - Create/edit/delete accounts and transactions
  - Invite members as ADMIN, MEMBER, or VIEWER
  - Remove members (except OWNER)
  - Cannot change roles or update household settings

- **MEMBER** (Full Data Access):
  - Create/edit/delete accounts and transactions
  - View all household finances
  - Cannot manage members or settings

- **VIEWER** (Read-Only):
  - View all accounts and transactions
  - Generate reports and export data
  - Cannot make any changes

### Accounts

An **Account** represents a financial account like:

- **Checking Account** - everyday spending (e.g., "Chase Checking")
- **Savings Account** - savings and emergency funds (e.g., "High-Yield Savings")
- **Credit Card** - credit card accounts (e.g., "Amex Blue Cash")
- **Investment Account** - stocks, bonds, retirement (e.g., "Vanguard 401k")
- **Loan** - mortgages, car loans, student loans (e.g., "Mortgage")
- **Other** - anything else

Accounts are **shared within your household** - all members can view them (and edit if they have MEMBER+ permission).

### Transactions

A **Transaction** is any money movement:

- **Income** (positive amounts): salary, freelance, refunds, gifts
- **Expenses** (negative amounts): groceries, rent, utilities, entertainment

Each transaction includes:
- **Amount**: Positive for income, negative for expenses
- **Date**: When it occurred
- **Category**: What type (groceries, rent, entertainment, etc.)
- **Optional Details**: merchant, description, location, tags

### Balance Tracking

Finance Planner automatically calculates account balances:

- **Initial Balance**: Set when creating an account
- **Auto-Update**: Every transaction automatically updates the balance
- **Recalculation**: Editing or deleting transactions adjusts the balance automatically

**Formula**: `Balance = Initial Balance + Sum of All Transactions`

---

## Getting Started

### Step 1: Obtain Access

Before using Finance Planner, you need:

1. **Account credentials** from your MCP_Auth service
2. **Tenant membership** - someone must invite you to a household, or you create your own

Contact your system administrator or the household owner for access.

### Step 2: Authenticate

1. Log in to the authentication service (MCP_Auth)
2. You'll receive an **access token** (JWT)
3. Select your **tenant** (household) if you belong to multiple
4. This token is valid for a limited time (typically 15 minutes)

### Step 3: Access Finance Planner

Use the access token to make API requests to Finance Planner:

```bash
# Example: List your accounts
curl -X GET "http://localhost:8000/api/accounts" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**For Frontend Users:** Your web or mobile app handles authentication automatically - just log in and select your household!

---

## Managing Your Household (Tenant)

### View Household Information

**Endpoint:** `GET /api/tenants/me`

See your current household details:

```bash
curl -X GET "http://localhost:8000/api/tenants/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "id": 1,
  "name": "Smith Family",
  "created_at": "2026-01-05T12:00:00",
  "updated_at": "2026-01-05T12:00:00"
}
```

### Update Household Name

**Endpoint:** `PATCH /api/tenants/me` (OWNER only)

Change your household name:

```bash
curl -X PATCH "http://localhost:8000/api/tenants/me" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Smith-Johnson Family"}'
```

### List All Members

**Endpoint:** `GET /api/tenants/me/members`

See who has access to your household:

```bash
curl -X GET "http://localhost:8000/api/tenants/me/members" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "auth_user_id": "user-123",
    "role": "owner",
    "created_at": "2026-01-05T12:00:00"
  },
  {
    "id": 2,
    "user_id": 2,
    "auth_user_id": "spouse-456",
    "role": "admin",
    "created_at": "2026-01-06T10:00:00"
  }
]
```

### Invite a New Member

**Endpoint:** `POST /api/tenants/me/members` (ADMIN/OWNER)

Add someone to your household:

```bash
curl -X POST "http://localhost:8000/api/tenants/me/members" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "auth_user_id": "new-member-789",
    "role": "member"
  }'
```

**Who can invite whom:**
- **OWNER** can invite anyone with any role (including OWNER)
- **ADMIN** can invite ADMIN, MEMBER, or VIEWER (not OWNER)

### Change a Member's Role

**Endpoint:** `PATCH /api/tenants/me/members/{user_id}/role` (OWNER only)

Update someone's permission level:

```bash
curl -X PATCH "http://localhost:8000/api/tenants/me/members/2/role" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

**Restrictions:**
- Only OWNER can change roles
- Cannot change your own role
- Cannot change the OWNER's role

### Remove a Member

**Endpoint:** `DELETE /api/tenants/me/members/{user_id}` (ADMIN/OWNER)

Remove someone from your household:

```bash
curl -X DELETE "http://localhost:8000/api/tenants/me/members/3" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Restrictions:**
- Cannot remove yourself
- Cannot remove the OWNER
- ADMIN and OWNER can remove others

---

## Managing Accounts

### Create an Account

**Endpoint:** `POST /api/accounts` (MEMBER+)

Add a new financial account:

```bash
curl -X POST "http://localhost:8000/api/accounts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chase Checking",
    "account_type": "checking",
    "initial_balance": 1500.00
  }'
```

**Account Types:**
- `checking` - Everyday checking accounts
- `savings` - Savings accounts
- `credit_card` - Credit cards
- `investment` - Investment/retirement accounts
- `loan` - Mortgages, car loans, etc.
- `other` - Anything else

**Response:**
```json
{
  "id": 1,
  "name": "Chase Checking",
  "account_type": "checking",
  "balance": 1500.00,
  "created_at": "2026-01-15T10:00:00"
}
```

### List All Accounts

**Endpoint:** `GET /api/accounts`

View all household accounts:

```bash
curl -X GET "http://localhost:8000/api/accounts" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "accounts": [
    {
      "id": 1,
      "name": "Chase Checking",
      "account_type": "checking",
      "balance": 1500.00,
      "created_at": "2026-01-15T10:00:00"
    },
    {
      "id": 2,
      "name": "High-Yield Savings",
      "account_type": "savings",
      "balance": 5000.00,
      "created_at": "2026-01-15T11:00:00"
    }
  ],
  "total": 2
}
```

### View Single Account

**Endpoint:** `GET /api/accounts/{id}`

Get details for one account:

```bash
curl -X GET "http://localhost:8000/api/accounts/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update an Account

**Endpoint:** `PATCH /api/accounts/{id}` (MEMBER+)

Change account name or type:

```bash
curl -X PATCH "http://localhost:8000/api/accounts/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Chase Total Checking"}'
```

**Note:** You cannot directly edit the balance - it's calculated from transactions.

### Delete an Account

**Endpoint:** `DELETE /api/accounts/{id}` (MEMBER+)

Remove an account permanently:

```bash
curl -X DELETE "http://localhost:8000/api/accounts/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**⚠️ Warning:** This permanently deletes the account AND all its transactions! Consider exporting data first.

---

## Tracking Transactions

### Create a Single Transaction

**Endpoint:** `POST /api/transactions` (MEMBER+)

Record income or an expense:

```bash
curl -X POST "http://localhost:8000/api/transactions" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "amount": -50.00,
    "date": "2026-01-15",
    "category": "groceries",
    "merchant": "Whole Foods",
    "description": "Weekly grocery shopping",
    "location": "Main St Store",
    "tags": ["food", "essential"]
  }'
```

**Key Fields:**
- `amount`: Use **negative** for expenses, **positive** for income
  - `-50.00` = $50 expense
  - `2500.00` = $2,500 income
- `date`: ISO format (YYYY-MM-DD)
- `category`: Your categorization (groceries, rent, salary, etc.)
- `merchant`: Where the transaction occurred (optional)
- `description`: Additional notes (optional)
- `tags`: Array of tags for filtering (optional)

**Derived Fields (Optional):**
- `der_category`: Normalized category for reporting (e.g., "food_grocery")
- `der_merchant`: Normalized merchant name (e.g., "wholefoods")

**Balance Update:**
The account balance automatically updates: `new_balance = old_balance + amount`

### Create Multiple Transactions (Batch)

**Endpoint:** `POST /api/transactions/batch` (MEMBER+)

Import many transactions at once (1-100 per batch):

```bash
curl -X POST "http://localhost:8000/api/transactions/batch" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "transactions": [
      {"amount": -150.00, "date": "2026-01-01", "category": "groceries", "merchant": "Safeway"},
      {"amount": -45.00, "date": "2026-01-01", "category": "gas", "merchant": "Shell"},
      {"amount": 2500.00, "date": "2026-01-01", "category": "income", "description": "Salary"},
      {"amount": -1200.00, "date": "2026-01-01", "category": "rent", "merchant": "Landlord"}
    ]
  }'
```

**Benefits:**
- **Atomic**: All transactions succeed or all fail (no partial imports)
- **Fast**: 10-50x faster than individual creates
- **Single balance update**: One calculation for entire batch

**Use Cases:**
- Importing bank statement CSV files
- Monthly transaction import
- Bulk historical data entry

**Response:**
```json
{
  "transactions": [...],
  "account_balance": 1155.00,
  "total_amount": -895.00,
  "count": 4
}
```

### List Transactions

**Endpoint:** `GET /api/transactions`

View all household transactions with powerful filtering:

```bash
# Basic list
curl -X GET "http://localhost:8000/api/transactions" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by account
curl -X GET "http://localhost:8000/api/transactions?account_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by date range
curl -X GET "http://localhost:8000/api/transactions?start_date=2026-01-01&end_date=2026-01-31" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by category
curl -X GET "http://localhost:8000/api/transactions?category=groceries" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search merchant (partial match)
curl -X GET "http://localhost:8000/api/transactions?merchant=Whole" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by tags (comma-separated, matches ANY tag)
curl -X GET "http://localhost:8000/api/transactions?tags=food,essential" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Pagination
curl -X GET "http://localhost:8000/api/transactions?limit=50&offset=0" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Complex: Date range + category + pagination
curl -X GET "http://localhost:8000/api/transactions?start_date=2026-01-01&end_date=2026-01-31&category=groceries&limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Filter Options:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `account_id` | int | Specific account | `?account_id=1` |
| `start_date` | date | From date (inclusive) | `?start_date=2026-01-01` |
| `end_date` | date | To date (inclusive) | `?end_date=2026-01-31` |
| `category` | string | Exact match | `?category=groceries` |
| `merchant` | string | Partial match | `?merchant=Whole` |
| `tags` | string | Comma-separated, ANY | `?tags=food,essential` |
| `der_category` | string | Derived category | `?der_category=food_grocery` |
| `der_merchant` | string | Derived merchant | `?der_merchant=wholefoods` |
| `limit` | int | Max results (1-1000) | `?limit=100` |
| `offset` | int | Skip first N | `?offset=50` |

**Response:**
```json
{
  "transactions": [
    {
      "id": 1,
      "account_id": 1,
      "amount": -50.00,
      "date": "2026-01-15",
      "category": "groceries",
      "merchant": "Whole Foods",
      "description": "Weekly grocery shopping",
      "tags": ["food", "essential"],
      "created_at": "2026-01-15T14:00:00"
    }
  ],
  "total": 1
}
```

### View Single Transaction

**Endpoint:** `GET /api/transactions/{id}`

Get details for one transaction:

```bash
curl -X GET "http://localhost:8000/api/transactions/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update a Transaction

**Endpoint:** `PATCH /api/transactions/{id}` (MEMBER+)

Modify transaction details:

```bash
# Update amount (balance recalculated automatically)
curl -X PATCH "http://localhost:8000/api/transactions/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": -75.00}'

# Update category/merchant (no balance change)
curl -X PATCH "http://localhost:8000/api/transactions/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category": "dining", "merchant": "Restaurant XYZ"}'

# Update multiple fields
curl -X PATCH "http://localhost:8000/api/transactions/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": -60.00,
    "category": "groceries",
    "tags": ["food", "weekly"]
  }'
```

**Smart Balance Recalculation:**
- If you change `amount`: Balance updates automatically
- If you change other fields: Balance stays the same
- Formula: `balance_change = new_amount - old_amount`

### Delete a Transaction

**Endpoint:** `DELETE /api/transactions/{id}` (MEMBER+)

Remove a transaction:

```bash
curl -X DELETE "http://localhost:8000/api/transactions/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Balance Update:**
The account balance automatically adjusts: `balance -= transaction.amount`

**Example:** Deleting a -$50 expense increases balance by $50 (reverses the expense)

---

## Common Workflows

### Workflow 1: Setting Up Your Household

**Goal:** Create a household and add family members

**Steps:**

1. **Create your tenant** (handled by initial setup or admin)

2. **Add your first account:**
   ```bash
   curl -X POST "http://localhost:8000/api/accounts" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Family Checking",
       "account_type": "checking",
       "initial_balance": 5000.00
     }'
   ```

3. **Invite your spouse as ADMIN:**
   ```bash
   curl -X POST "http://localhost:8000/api/tenants/me/members" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "auth_user_id": "spouse-user-id",
       "role": "admin"
     }'
   ```

4. **Add other family members as MEMBER or VIEWER**

5. **Start tracking transactions!**

### Workflow 2: Monthly Budget Import

**Goal:** Import bank statement CSV into Finance Planner

**Steps:**

1. **Export CSV from your bank** (example format):
   ```csv
   date,amount,category,merchant,description
   2026-01-05,-150.00,groceries,Safeway,Weekly shopping
   2026-01-05,-45.00,gas,Shell,Gas fillup
   2026-01-10,2500.00,income,Employer,January salary
   ```

2. **Convert CSV to JSON format:**
   ```python
   import csv
   import json

   transactions = []
   with open('bank_statement.csv', 'r') as f:
       reader = csv.DictReader(f)
       for row in reader:
           transactions.append({
               "amount": float(row['amount']),
               "date": row['date'],
               "category": row['category'],
               "merchant": row.get('merchant'),
               "description": row.get('description')
           })

   # Split into batches of 100 (API limit)
   batch_size = 100
   for i in range(0, len(transactions), batch_size):
       batch = transactions[i:i+batch_size]
       print(json.dumps({"account_id": 1, "transactions": batch}))
   ```

3. **Import each batch:**
   ```bash
   curl -X POST "http://localhost:8000/api/transactions/batch" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d @batch1.json
   ```

4. **Verify balance matches your bank**

### Workflow 3: Monthly Spending Report

**Goal:** Analyze spending by category for a month

**Steps:**

1. **Fetch all transactions for the month:**
   ```bash
   curl -X GET "http://localhost:8000/api/transactions?start_date=2026-01-01&end_date=2026-01-31&limit=1000" \
     -H "Authorization: Bearer $TOKEN" \
     > january_transactions.json
   ```

2. **Process locally or with script:**
   ```python
   import json
   from collections import defaultdict

   with open('january_transactions.json') as f:
       data = json.load(f)

   spending = defaultdict(float)
   income = 0

   for txn in data['transactions']:
       amount = txn['amount']
       category = txn['category']

       if amount < 0:
           spending[category] += abs(amount)
       else:
           income += amount

   print(f"Income: ${income:.2f}")
   print("\nSpending by Category:")
   for category, amount in sorted(spending.items(), key=lambda x: -x[1]):
       print(f"  {category:20s} ${amount:>10.2f}")
   print(f"\nTotal Spending: ${sum(spending.values()):.2f}")
   print(f"Net: ${income - sum(spending.values()):.2f}")
   ```

**Output:**
```
Income: $5000.00

Spending by Category:
  rent                 $  1200.00
  groceries            $   450.00
  utilities            $   200.00
  gas                  $   150.00
  dining               $   120.00

Total Spending: $2120.00
Net: $2880.00
```

### Workflow 4: Account Reconciliation

**Goal:** Fix account balance discrepancy

**Steps:**

1. **Check current balance:**
   ```bash
   curl -X GET "http://localhost:8000/api/accounts/1" \
     -H "Authorization: Bearer $TOKEN"
   ```

2. **Compare with bank balance:**
   - Finance Planner shows: $1,450.00
   - Bank shows: $1,500.00
   - Difference: $50.00

3. **Find missing transaction or create adjustment:**
   ```bash
   # Option 1: Add missing transaction
   curl -X POST "http://localhost:8000/api/transactions" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "account_id": 1,
       "amount": 50.00,
       "date": "2026-01-15",
       "category": "adjustment",
       "description": "Reconciliation adjustment - interest payment"
     }'

   # Option 2: Create adjustment transaction
   curl -X POST "http://localhost:8000/api/transactions" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "account_id": 1,
       "amount": 50.00,
       "date": "2026-01-15",
       "category": "adjustment",
       "description": "Balance reconciliation"
     }'
   ```

4. **Verify balance now matches**

### Workflow 5: Granting Temporary Access

**Goal:** Give your accountant read-only access for tax season

**Steps:**

1. **Invite accountant as VIEWER:**
   ```bash
   curl -X POST "http://localhost:8000/api/tenants/me/members" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "auth_user_id": "accountant-user-id",
       "role": "viewer"
     }'
   ```

2. **Accountant can now view (but not edit) all data**

3. **After tax season, remove access:**
   ```bash
   # First, find their user_id
   curl -X GET "http://localhost:8000/api/tenants/me/members" \
     -H "Authorization: Bearer $TOKEN"

   # Then remove them
   curl -X DELETE "http://localhost:8000/api/tenants/me/members/5" \
     -H "Authorization: Bearer $TOKEN"
   ```

---

## Tips & Best Practices

### Categorization Strategy

**Use consistent categories:**
- `groceries` - Food shopping
- `dining` - Restaurants and takeout
- `rent` - Monthly rent/mortgage
- `utilities` - Electric, gas, water, internet
- `transportation` - Gas, public transit, car maintenance
- `entertainment` - Movies, concerts, hobbies
- `healthcare` - Medical, dental, pharmacy
- `income` - Salary, freelance, gifts
- `adjustment` - Corrections and reconciliations

**Use tags for cross-cutting concerns:**
- `essential` vs `discretionary`
- `tax-deductible`
- `reimbursable`
- `subscription`

### Data Entry Habits

1. **Record transactions promptly** - Don't wait until end of month
2. **Use batch import for historical data** - Much faster than manual entry
3. **Reconcile monthly** - Compare with bank statements
4. **Add notes to unusual transactions** - Future you will thank you
5. **Use derived fields** - Normalize merchants for better reporting

### Account Structure

**Recommended setup:**
- One account per real financial account
- Avoid creating "virtual" accounts for categories
- Use tags/categories for budget tracking instead
- Keep closed accounts as long as history is valuable

### Member Management

**Role assignment guidelines:**
- **OWNER**: Primary household manager (usually 1 person)
- **ADMIN**: Spouse or co-manager who shares responsibilities
- **MEMBER**: Adult children or others who contribute to finances
- **VIEWER**: Accountants, financial advisors, or children learning finances

### Security Best Practices

1. **Protect your access token** - It's like your password
2. **Log out on shared devices** - Tokens expire after 15 minutes
3. **Use VIEWER role** for read-only access needs
4. **Regularly review members** - Remove those who no longer need access
5. **Don't share your role** - Each person should have their own account

### Performance Tips

1. **Use batch operations** for bulk imports (10-50x faster)
2. **Limit transaction queries** - Use date ranges and filters
3. **Paginate large result sets** - Don't fetch all transactions at once
4. **Use derived fields** for reporting - Pre-normalize data for speed

---

## Troubleshooting

### "Could not validate credentials" (401 Error)

**Problem:** Your access token is invalid or expired.

**Solutions:**
1. **Re-authenticate** with MCP_Auth to get a new token
2. **Check token format** - Must be `Authorization: Bearer <token>`
3. **Verify SECRET_KEY** - Finance Planner and MCP_Auth must match
4. **Check token expiration** - Tokens typically expire after 15 minutes

### "Tenant not found" (404 Error)

**Problem:** The tenant_id in your JWT doesn't exist.

**Solutions:**
1. **Verify tenant exists** - Check with administrator
2. **Re-authenticate** - Get a fresh token with correct tenant_id
3. **Switch tenants** if you belong to multiple households

### "Not a member of tenant" (403 Error)

**Problem:** Your user is not a member of the tenant in the token.

**Solutions:**
1. **Request invitation** - Ask tenant OWNER/ADMIN to invite you
2. **Verify membership** - Contact administrator to check status
3. **Re-authenticate** - Ensure you're using the right tenant_id

### "Account not found" (404 Error)

**Problem:** Account doesn't exist or you don't have access.

**Solutions:**
1. **List all accounts** - Verify account exists in your household
2. **Check account ID** - Ensure you're using the correct ID
3. **Verify tenant context** - Make sure you're in the right household

### "Forbidden" (403 Error) When Creating/Editing

**Problem:** Your role doesn't have write permissions.

**Solutions:**
1. **Check your role** - VIEWER is read-only
2. **Request role upgrade** - Ask OWNER to promote you to MEMBER
3. **Use correct endpoint** - Read endpoints don't require write permissions

### Balance Doesn't Match Bank

**Problem:** Finance Planner balance differs from bank statement.

**Solutions:**
1. **Check for missing transactions** - Did you record everything?
2. **Look for duplicates** - Did you import the same transaction twice?
3. **Verify initial balance** - Was it set correctly?
4. **Check pending transactions** - Bank might include pending, you might not
5. **Create reconciliation adjustment** - Add adjustment transaction for difference

### Batch Import Failed Partially

**Problem:** Some transactions imported, others didn't.

**Good News:** This shouldn't happen! Batch operations are atomic (all-or-nothing).

**If it does happen:**
1. **Check API response** - Look for error details
2. **Verify data format** - Ensure all transactions have required fields
3. **Check batch size** - Maximum 100 transactions per batch
4. **Retry** - The failed batch can be retried without duplicates

### Can't Remove a Member

**Problem:** Delete member request fails.

**Possible Reasons:**
1. **Trying to remove OWNER** - Not allowed
2. **Trying to remove yourself** - Not allowed
3. **Insufficient permissions** - Need ADMIN or OWNER role
4. **Member doesn't exist** - Verify user_id

### Transaction Update Didn't Change Balance

**Problem:** Updated transaction but balance stayed the same.

**Explanation:** Balance only updates when you change the `amount` field.

**Solution:** If you need to change the balance, update the transaction's `amount` field.

---

## Frequently Asked Questions

### General Questions

**Q: Can I belong to multiple households?**

A: Yes! You can be a member of multiple tenants (e.g., personal finances + family finances). When authenticating, you'll select which tenant context to use.

**Q: Is my data private from other households?**

A: Absolutely! Multi-tenant isolation ensures complete data separation. Other households cannot see your data, even if they're on the same server.

**Q: What happens if I delete an account?**

A: The account AND all its transactions are permanently deleted. This is a destructive operation - consider exporting data first.

**Q: Can I restore deleted transactions?**

A: No, deletions are permanent. Consider implementing soft-deletes or backups for production systems.

**Q: How often should I reconcile with my bank?**

A: Monthly reconciliation is recommended. Weekly is even better for catching errors early.

### Permission Questions

**Q: Can a VIEWER create reports?**

A: VIEWER can view all data and perform read operations, but reporting typically happens client-side (in your app or scripts).

**Q: Can an ADMIN promote someone to OWNER?**

A: No, only the current OWNER can change roles or promote members to OWNER.

**Q: Can I have multiple OWNERs?**

A: Yes! The current OWNER can promote other members to OWNER. This is useful for co-equal household managers.

**Q: What if the OWNER leaves?**

A: Before leaving, the OWNER should promote another member to OWNER. If the OWNER leaves without doing this, you'll need administrator intervention to promote someone.

### Transaction Questions

**Q: Should I use negative amounts for expenses?**

A: Yes! Use negative for expenses (-$50), positive for income ($2,500). This makes the balance calculation intuitive.

**Q: What's the difference between category and der_category?**

A: `category` is your free-form categorization. `der_category` is normalized/derived for consistent reporting (e.g., "groceries" → "food_grocery").

**Q: Can I split a transaction across categories?**

A: Not directly. Create separate transactions for each category split (e.g., $100 grocery trip = $80 groceries + $20 household items).

**Q: How do I track refunds?**

A: Create a positive transaction in the same category as the original expense.

**Q: Can I attach receipts to transactions?**

A: Not yet! This is a planned feature. For now, use the `description` field to note receipt location.

### Account Questions

**Q: Should I create separate accounts for budgets?**

A: No, accounts represent real financial accounts. Use categories and tags for budget tracking instead.

**Q: Can I merge two accounts?**

A: Not directly. You'd need to:
1. Move transactions from Account A to Account B (update account_id)
2. Delete Account A
3. Adjust balance if needed

**Q: How do I handle joint accounts?**

A: Create one account and all household members (based on role) can access it. That's the point of multi-tenant!

**Q: What if I close a bank account?**

A: You can either:
1. Delete it (loses all history)
2. Keep it and stop adding transactions (preserves history)
3. Update the name to "Closed - Chase Checking"

### Technical Questions

**Q: How long are access tokens valid?**

A: Typically 15 minutes. Your app should handle automatic refresh or re-authentication.

**Q: What's the maximum batch size?**

A: 100 transactions per batch. For larger imports, split into multiple batches.

**Q: Can I access the API from my own app?**

A: Yes! Finance Planner is a REST API designed for client applications. See the OpenAPI docs at `/docs`.

**Q: Is there rate limiting?**

A: Not currently implemented, but may be added for production deployments.

**Q: Can I export all my data?**

A: Yes, use the list endpoints with no filters to retrieve all data. Consider adding an export feature to your client app.

---

## Need More Help?

### Resources

- **API Documentation**: http://localhost:8000/docs
- **Technical Documentation**: See `docs/ENDPOINTS.md` for detailed API reference
- **Developer Guide**: See `CLAUDE.md` for development information
- **Deployment Guide**: See `docs/RUNNING.md` for server setup

### Support

For technical support or questions:
1. Check this manual first
2. Review the API documentation at `/docs`
3. Contact your system administrator
4. File an issue on GitHub (if applicable)

---

**Version:** 1.0
**Last Updated:** January 2026
**Compatible with:** Finance Planner v1.0+