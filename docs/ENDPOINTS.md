# API Endpoints Reference

Complete documentation of all REST API endpoints with sequence diagrams showing the flow through the application architecture.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Authentication Flow](#authentication-flow)
- [Tenant Endpoints](#tenant-endpoints)
  - [List User Tenants](#1-list-user-tenants)
  - [Get Current Tenant](#2-get-current-tenant)
  - [Update Tenant](#3-update-tenant)
  - [List Members](#4-list-members)
  - [Invite Member](#5-invite-member)
  - [Update Member Role](#6-update-member-role)
  - [Remove Member](#7-remove-member)
- [Account Endpoints](#account-endpoints)
  - [Create Account](#1-create-account)
  - [List Accounts](#2-list-accounts)
  - [Get Account](#3-get-account)
  - [Update Account](#4-update-account)
  - [Delete Account](#5-delete-account)
- [Transaction Endpoints](#transaction-endpoints)
  - [Create Transaction](#1-create-transaction)
  - [Create Batch Transactions](#2-create-batch-transactions)
  - [List Transactions](#3-list-transactions)
  - [Get Transaction](#4-get-transaction)
  - [Update Transaction](#5-update-transaction)
  - [Delete Transaction](#6-delete-transaction)

---

## Architecture Overview

All endpoints follow the same layered architecture:

```
Client → Route → Service → Repository → Database
         ↓
    Authentication
    (get_tenant_context)
```

**Layers:**
- **Route**: FastAPI endpoint with dependency injection (tenant context, database session)
- **Service**: Business logic, validation, orchestration, permission checks
- **Repository**: Data access with tenant-based filtering
- **Database**: SQLAlchemy ORM models and PostgreSQL/SQLite

**Common Dependencies:**
- `get_tenant_context`: JWT authentication + tenant context via MCP_Auth integration
- `get_db`: Database session management

**Multi-Tenant Architecture:**
- Tenant is the isolation boundary (not User)
- All accounts and transactions belong to a tenant (family/household)
- Users access data through TenantMembership with role-based permissions
- Four-tier role hierarchy: OWNER > ADMIN > MEMBER > VIEWER

---

## Authentication Flow

All endpoints require JWT authentication with tenant context. The authentication flow is shared across all endpoints:

```mermaid
sequenceDiagram
    participant Client
    participant Route
    participant Auth as get_tenant_context
    participant JWT as JWT Decoder
    participant UserRepo as UserRepository
    participant TenantRepo as TenantRepository
    participant MemberRepo as TenantMembershipRepository
    participant DB as Database

    Client->>Route: Request with Authorization: Bearer <token>
    Route->>Auth: Depends(get_tenant_context)
    Auth->>JWT: Decode JWT token
    JWT->>Auth: Extract user_id ('sub') and tenant_id claims

    Auth->>UserRepo: get_or_create_by_auth_id(user_id)
    UserRepo->>DB: SELECT User WHERE auth_user_id = ?

    alt User exists
        DB-->>UserRepo: Return User
    else User not found (first request)
        UserRepo->>DB: INSERT User(auth_user_id=user_id)
        DB-->>UserRepo: Return new User
    end

    UserRepo-->>Auth: Return User object

    Auth->>TenantRepo: get_by_id(tenant_id)
    TenantRepo->>DB: SELECT Tenant WHERE id = tenant_id

    alt Tenant not found
        TenantRepo-->>Auth: Return None
        Auth->>Route: 404 Tenant not found
        Route-->>Client: 404 Not Found
    end

    DB-->>TenantRepo: Return Tenant
    TenantRepo-->>Auth: Return Tenant object

    Auth->>MemberRepo: get_membership(user_id, tenant_id)
    MemberRepo->>DB: SELECT TenantMembership<br/>WHERE user_id = ? AND tenant_id = ?

    alt Membership not found
        MemberRepo-->>Auth: Return None
        Auth->>Route: 403 Not a member of tenant
        Route-->>Client: 403 Forbidden
    end

    DB-->>MemberRepo: Return TenantMembership
    MemberRepo-->>Auth: Return Membership with role

    Auth->>Auth: Build TenantContext<br/>(user, tenant, role)
    Auth-->>Route: Inject TenantContext
    Route->>Route: Process request with tenant context<br/>and role-based permissions
```

**Security Notes:**
- Invalid/expired tokens → 401 Unauthorized
- Missing tenant_id in JWT → 401 Unauthorized
- Tenant not found → 404 Not Found
- User not a member of tenant → 403 Forbidden
- Multi-tenant isolation enforced at repository layer using tenant_id
- User records auto-created on first API request
- Role-based permissions enforced at service layer

**TenantContext Structure:**
```python
TenantContext(
    user: User,           # Authenticated user
    tenant: Tenant,       # Current tenant (family/household)
    role: TenantRole     # User's role in this tenant
)
```

**Permission Checks:**
- `context.can_write()` → OWNER, ADMIN, MEMBER
- `context.can_read()` → All roles
- `context.is_admin_or_higher()` → OWNER, ADMIN
- `context.is_owner()` → OWNER only

---

# Tenant Endpoints

Base path: `/api/tenants`

## 1. List User Tenants

**Endpoint:** `GET /api/tenants`
**Authentication:** Required (no tenant context needed)
**Response:** `List[UserTenantResponse]` (200 OK)

### Business Logic

1. Lists all tenants that the authenticated user belongs to
2. Includes the user's role in each tenant
3. Does NOT require tenant_id in JWT (unlike other endpoints)
4. Useful for tenant switching functionality
5. Returns empty array if user has no tenant memberships

### Example Response

```json
[
  {
    "id": 1,
    "name": "Smith Family",
    "role": "owner",
    "created_at": "2026-01-05T12:00:00",
    "updated_at": "2026-01-05T12:00:00"
  },
  {
    "id": 2,
    "name": "Personal Finances",
    "role": "member",
    "created_at": "2026-01-06T10:00:00",
    "updated_at": "2026-01-06T10:00:00"
  }
]
```

### Use Cases

- **Tenant Switching**: List all available tenants for user to choose from
- **Multi-Tenant Dashboard**: Display all tenants user belongs to
- **Initial Login**: Determine which tenant to use if user belongs to multiple

### Security Notes

- Uses `get_current_user` dependency (not `get_tenant_context`)
- JWT token should NOT include `tenant_id` claim for this endpoint
- Users can only see tenants they are members of
- Complete multi-tenant isolation maintained

---

## 2. Get Current Tenant

**Endpoint:** `GET /api/tenants/me`
**Authentication:** Required
**Response:** `TenantResponse` (200 OK)

### Business Logic

1. Returns tenant information from authenticated context
2. All users can view their own tenant details

### Example Response

```json
{
  "id": 1,
  "name": "Smith Family",
  "created_at": "2026-01-05T12:00:00",
  "updated_at": "2026-01-05T12:00:00"
}
```

---

## 3. Update Tenant

**Endpoint:** `PATCH /api/tenants/me`
**Authentication:** Required (OWNER only)
**Request Body:** `TenantUpdate`
**Response:** `TenantResponse` (200 OK)

### Business Logic

1. Checks `context.is_owner()` permission
2. Updates tenant name
3. Returns 403 if user is not OWNER

### Example Request

```json
{
  "name": "Smith-Johnson Family"
}
```

---

## 4. List Members

**Endpoint:** `GET /api/tenants/me/members`
**Authentication:** Required
**Response:** `List[TenantMemberResponse]` (200 OK)

### Business Logic

1. Lists all members of current tenant with their roles
2. Available to all tenant members
3. Enriches with user auth_user_id for reference

### Example Response

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
    "auth_user_id": "user-456",
    "role": "member",
    "created_at": "2026-01-06T10:00:00"
  }
]
```

---

## 5. Invite Member

**Endpoint:** `POST /api/tenants/me/members`
**Authentication:** Required (ADMIN or OWNER)
**Request Body:** `TenantInviteRequest`
**Response:** `TenantMemberResponse` (201 Created)

### Business Logic

1. Checks `context.is_admin_or_higher()` permission
2. Gets or creates user by auth_user_id
3. Validates user is not already a member
4. Only OWNER can invite as OWNER role
5. Creates TenantMembership with specified role

### Example Request

```json
{
  "auth_user_id": "user-789",
  "role": "member"
}
```

### Permission Rules

- ADMIN can invite as: ADMIN, MEMBER, VIEWER
- ADMIN cannot invite as: OWNER
- OWNER can invite as: Any role

---

## 6. Update Member Role

**Endpoint:** `PATCH /api/tenants/me/members/{user_id}/role`
**Authentication:** Required (OWNER only)
**Request Body:** `TenantRoleUpdate`
**Response:** `TenantMemberResponse` (200 OK)

### Business Logic

1. Checks `context.is_owner()` permission
2. Verifies membership exists
3. Prevents changing own role
4. Prevents changing OWNER role
5. Updates membership role

### Example Request

```json
{
  "role": "admin"
}
```

### Restrictions

- Cannot change OWNER's role
- Cannot change own role
- Only OWNER can change roles

---

## 7. Remove Member

**Endpoint:** `DELETE /api/tenants/me/members/{user_id}`
**Authentication:** Required (ADMIN or OWNER)
**Response:** `TenantMemberRemoveResponse` (200 OK)

### Business Logic

1. Checks `context.is_admin_or_higher()` permission
2. Verifies membership exists
3. Prevents removing self
4. Prevents removing OWNER
5. Deletes membership

### Example Response

```json
{
  "message": "Member removed successfully",
  "removed_user_id": 2
}
```

### Restrictions

- Cannot remove OWNER
- Cannot remove self
- ADMIN and OWNER can remove others

---

# Account Endpoints

Base path: `/api/accounts`

## 1. Create Account

**Endpoint:** `POST /api/accounts`
**Authentication:** Required
**Request Body:** `AccountCreate`
**Response:** `AccountResponse` (201 Created)

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Route as AccountRoute
    participant Service as AccountService
    participant Repo as AccountRepository
    participant DB as Database

    Client->>Route: POST /api/accounts<br/>{name, account_type, initial_balance}
    Note over Route: get_tenant_context()<br/>Injects TenantContext (user, tenant, role)
    Route->>Service: create_account(data, context)

    Service->>Service: Check context.can_write()<br/>(MEMBER+ required)
    Service->>Service: Validate account_type<br/>(checking, savings, credit, investment)
    Service->>Service: Set balance = initial_balance ?? 0.0

    Service->>Repo: create(account)
    Repo->>DB: INSERT INTO accounts<br/>(tenant_id, user_id, name, type, balance)
    DB-->>Repo: Return Account with ID
    Repo->>DB: COMMIT
    Repo-->>Service: Return Account

    Service-->>Route: Return Account
    Route-->>Client: 201 Created<br/>AccountResponse
```

### Business Logic

1. Checks `context.can_write()` permission (OWNER, ADMIN, MEMBER)
2. Validates `account_type` against allowed values
3. Sets `initial_balance` to 0.0 if not provided
4. Associates account with current tenant (shared with all members)
5. Records creating user for audit trail
6. Returns created account with generated ID

### Permission Requirements

- **Required role**: MEMBER or higher
- **Forbidden for**: VIEWER (read-only)

### Validation Rules

- `name`: Required, 1-255 characters
- `account_type`: Must be one of: `checking`, `savings`, `credit`, `investment`
- `initial_balance`: Optional, defaults to 0.0

---

## 2. List Accounts

**Endpoint:** `GET /api/accounts`
**Authentication:** Required
**Query Parameters:** None
**Response:** `AccountListResponse` (200 OK)

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Route as AccountRoute
    participant Service as AccountService
    participant Repo as AccountRepository
    participant DB as Database

    Client->>Route: GET /api/accounts
    Note over Route: get_tenant_context()<br/>Injects TenantContext (user, tenant, role)
    Route->>Service: get_tenant_accounts(context)

    Service->>Repo: get_by_tenant(context.tenant.id)
    Repo->>DB: SELECT * FROM accounts<br/>WHERE tenant_id = ?<br/>ORDER BY created_at DESC
    DB-->>Repo: Return list of Accounts
    Repo-->>Service: Return Accounts[]

    Service-->>Route: Return Accounts[]
    Route->>Route: Build AccountListResponse<br/>{accounts, total}
    Route-->>Client: 200 OK<br/>{accounts: [...], total: N}
```

### Business Logic

1. Fetches all accounts belonging to current tenant (shared with all members)
2. Results ordered by creation date (newest first)
3. Returns total count for pagination/UI
4. All tenant members can view accounts (including VIEWER)

### Multi-Tenant Isolation

- Repository enforces `WHERE tenant_id = ?` filter
- Users can see all accounts within their tenant (shared family/household)
- Complete isolation between different tenants
- No cross-tenant data leakage possible
- Permission checks ensure VIEWER cannot modify data

---

## 3. Get Account

**Endpoint:** `GET /api/accounts/{account_id}`
**Authentication:** Required
**Path Parameters:** `account_id` (integer)
**Response:** `AccountResponse` (200 OK)

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Route as AccountRoute
    participant Service as AccountService
    participant Repo as AccountRepository
    participant DB as Database

    Client->>Route: GET /api/accounts/123
    Note over Route: get_current_user()<br/>Injects authenticated User
    Route->>Service: get_account(account_id=123, user)

    Service->>Repo: get_by_id_and_user(account_id=123, user_id)
    Repo->>DB: SELECT * FROM accounts<br/>WHERE id = 123 AND user_id = ?

    alt Account found and owned by user
        DB-->>Repo: Return Account
        Repo-->>Service: Return Account
        Service-->>Route: Return Account
        Route-->>Client: 200 OK<br/>AccountResponse
    else Account not found or unauthorized
        DB-->>Repo: Return None
        Repo-->>Service: Return None
        Service->>Service: Raise NotFoundException
        Service-->>Route: 404 Not Found
        Route-->>Client: 404 Not Found<br/>{detail: "Account not found"}
    end
```

### Business Logic

1. Fetches account by ID with user ownership check
2. Returns 404 if account doesn't exist OR user doesn't own it (security)
3. Single database query with composite filter

### Security Note

Returns same error (404) whether account doesn't exist or belongs to another user. This prevents information disclosure about account IDs.

---

## 4. Update Account

**Endpoint:** `PATCH /api/accounts/{account_id}`
**Authentication:** Required
**Path Parameters:** `account_id` (integer)
**Request Body:** `AccountUpdate` (partial)
**Response:** `AccountResponse` (200 OK)

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Route as AccountRoute
    participant Service as AccountService
    participant Repo as AccountRepository
    participant DB as Database

    Client->>Route: PATCH /api/accounts/123<br/>{name: "New Name"}
    Note over Route: get_current_user()<br/>Injects authenticated User
    Route->>Service: update_account(account_id=123, data, user)

    Service->>Repo: get_by_id_and_user(account_id=123, user_id)
    Repo->>DB: SELECT * FROM accounts<br/>WHERE id = 123 AND user_id = ?

    alt Account found
        DB-->>Repo: Return Account
        Repo-->>Service: Return Account

        Service->>Service: Apply partial updates<br/>ONLY for fields in request
        Note over Service: balance updates NOT allowed<br/>(managed by transactions)

        Service->>Repo: update(account)
        Repo->>DB: UPDATE accounts SET ...<br/>WHERE id = 123
        Repo->>DB: COMMIT
        DB-->>Repo: Return updated Account
        Repo-->>Service: Return Account

        Service-->>Route: Return Account
        Route-->>Client: 200 OK<br/>AccountResponse
    else Account not found
        Service->>Service: Raise NotFoundException
        Service-->>Route: 404 Not Found
        Route-->>Client: 404 Not Found
    end
```

### Business Logic

1. Verifies account ownership before update
2. Applies ONLY fields present in request (partial update)
3. `balance` field is read-only (managed by transaction operations)
4. Validates `account_type` if provided

### Allowed Updates

- `name`: String, 1-255 characters
- `account_type`: Must be valid type

---

## 5. Delete Account

**Endpoint:** `DELETE /api/accounts/{account_id}`
**Authentication:** Required
**Path Parameters:** `account_id` (integer)
**Response:** 204 No Content

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Route as AccountRoute
    participant Service as AccountService
    participant Repo as AccountRepository
    participant DB as Database

    Client->>Route: DELETE /api/accounts/123
    Note over Route: get_current_user()<br/>Injects authenticated User
    Route->>Service: delete_account(account_id=123, user)

    Service->>Repo: get_by_id_and_user(account_id=123, user_id)
    Repo->>DB: SELECT * FROM accounts<br/>WHERE id = 123 AND user_id = ?

    alt Account found
        DB-->>Repo: Return Account
        Repo-->>Service: Return Account

        Service->>Repo: delete(account)
        Repo->>DB: DELETE FROM transactions<br/>WHERE account_id = 123
        Note over DB: CASCADE DELETE<br/>removes all transactions
        Repo->>DB: DELETE FROM accounts<br/>WHERE id = 123
        Repo->>DB: COMMIT
        Repo-->>Service: Success

        Service-->>Route: Success
        Route-->>Client: 204 No Content
    else Account not found
        Service->>Service: Raise NotFoundException
        Service-->>Route: 404 Not Found
        Route-->>Client: 404 Not Found
    end
```

### Business Logic

1. Verifies account ownership before deletion
2. **CASCADE DELETE**: Automatically deletes all associated transactions
3. Atomic operation (single transaction)
4. Returns 204 No Content on success (no response body)

### Warning

Deletion is **permanent** and removes all transaction history for the account. Consider implementing soft deletes or archiving for production systems.

---

# Transaction Endpoints

Base path: `/api/transactions`

## 1. Create Transaction

**Endpoint:** `POST /api/transactions`
**Authentication:** Required
**Request Body:** `TransactionCreate`
**Response:** `TransactionResponse` (201 Created)

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Route as TransactionRoute
    participant Service as TransactionService
    participant TxnRepo as TransactionRepository
    participant AcctRepo as AccountRepository
    participant DB as Database

    Client->>Route: POST /api/transactions<br/>{account_id, amount, date, category, ...}
    Note over Route: get_current_user()<br/>Injects authenticated User
    Route->>Service: create_transaction(data, user)

    Service->>AcctRepo: get_by_id_and_user(account_id, user_id)
    AcctRepo->>DB: SELECT * FROM accounts<br/>WHERE id = ? AND user_id = ?

    alt Account found
        DB-->>AcctRepo: Return Account
        AcctRepo-->>Service: Return Account

        Service->>TxnRepo: create(transaction)
        TxnRepo->>DB: INSERT INTO transactions<br/>(account_id, amount, date, ...)
        TxnRepo->>DB: COMMIT
        DB-->>TxnRepo: Return Transaction with ID
        TxnRepo-->>Service: Return Transaction

        Service->>Service: Calculate new balance<br/>balance += amount
        Service->>AcctRepo: update(account)
        AcctRepo->>DB: UPDATE accounts SET balance = ?<br/>WHERE id = ?
        AcctRepo->>DB: COMMIT
        DB-->>AcctRepo: Return updated Account
        AcctRepo-->>Service: Return Account

        Service-->>Route: Return Transaction
        Route-->>Client: 201 Created<br/>TransactionResponse
    else Account not found
        Service->>Service: Raise NotFoundException
        Service-->>Route: 404 Not Found
        Route-->>Client: 404 Not Found
    end
```

### Business Logic

1. Verifies account ownership before creating transaction
2. Creates transaction record
3. Updates account balance automatically (`balance += amount`)
4. Positive amounts = income/deposits, negative = expenses/withdrawals
5. Two separate commits (transaction, then balance update)

### Validation Rules

- `account_id`: Must exist and be owned by user
- `amount`: Required (float, positive or negative)
- `date`: Required (ISO date format)
- `category`: Required, 1-100 characters
- `description`: Optional, max 1000 characters
- `merchant`: Optional, max 255 characters
- `location`: Optional, max 255 characters
- `tags`: Optional array of strings
- `der_category`: Optional derived category, max 100 characters
- `der_merchant`: Optional derived merchant, max 255 characters

---

## 2. Create Batch Transactions

**Endpoint:** `POST /api/transactions/batch`
**Authentication:** Required
**Request Body:** `TransactionBatchCreate`
**Response:** `TransactionBatchResponse` (201 Created)

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Route as TransactionRoute
    participant Service as TransactionService
    participant TxnRepo as TransactionRepository
    participant AcctRepo as AccountRepository
    participant DB as Database

    Client->>Route: POST /api/transactions/batch<br/>{account_id, transactions: [...]}
    Note over Route: get_current_user()<br/>Injects authenticated User
    Route->>Service: create_transaction_batch(batch_data, user)

    Service->>AcctRepo: get_by_id_and_user(account_id, user_id)
    AcctRepo->>DB: SELECT * FROM accounts<br/>WHERE id = ? AND user_id = ?

    alt Account found
        DB-->>AcctRepo: Return Account
        AcctRepo-->>Service: Return Account

        Service->>Service: Validate batch size (1-100)
        Service->>Service: Calculate total_amount = sum(amounts)
        Service->>Service: Build Transaction objects

        Note over Service: BEGIN ATOMIC OPERATION
        Service->>TxnRepo: create_bulk(transactions)
        TxnRepo->>DB: INSERT INTO transactions<br/>VALUES (txn1), (txn2), ..., (txnN)
        TxnRepo->>DB: FLUSH (assign IDs, no commit)
        DB-->>TxnRepo: Return Transactions with IDs
        TxnRepo-->>Service: Return Transactions[]

        Service->>Service: Update balance once<br/>balance += total_amount
        Service->>AcctRepo: update_no_commit(account)
        AcctRepo->>DB: UPDATE accounts SET balance = ?
        AcctRepo->>DB: FLUSH (no commit)

        Service->>DB: COMMIT (all operations)
        Note over Service: END ATOMIC OPERATION

        Service->>DB: Refresh all objects
        Service-->>Route: Return (transactions, balance)
        Route->>Route: Build TransactionBatchResponse
        Route-->>Client: 201 Created<br/>{transactions, account_balance, total_amount, count}

    else Account not found
        Service->>Service: Raise NotFoundException
        Service-->>Route: 404 Not Found
        Route-->>Client: 404 Not Found
    end

    Note over Service,DB: On ANY error:<br/>ROLLBACK entire batch
```

### Business Logic

1. Verifies account ownership
2. Validates batch size: minimum 1, maximum 100 transactions
3. **ATOMIC OPERATION**: All transactions committed together
4. Balance updated exactly once with `sum(amounts)`
5. Single database transaction for entire batch
6. On any failure, entire batch is rolled back (all-or-nothing)

### Validation Rules

- `account_id`: Must exist and be owned by user
- `transactions`: Array with 1-100 items (enforced by Pydantic)
- Each transaction follows same validation as single create
- All transactions share the same `account_id`

### Performance Benefits

- Bulk insert with `db.add_all()` instead of N individual inserts
- Single balance update instead of N updates
- Single database transaction instead of 2N transactions
- Significant performance improvement for large batches

### Example Request

```json
{
  "account_id": 123,
  "transactions": [
    {"amount": -50.00, "date": "2026-01-03", "category": "groceries", "merchant": "Whole Foods"},
    {"amount": -30.00, "date": "2026-01-03", "category": "gas", "merchant": "Shell"},
    {"amount": 100.00, "date": "2026-01-03", "category": "income", "description": "Freelance work"}
  ]
}
```

### Example Response

```json
{
  "transactions": [
    {"id": 1, "amount": -50.00, "category": "groceries", ...},
    {"id": 2, "amount": -30.00, "category": "gas", ...},
    {"id": 3, "amount": 100.00, "category": "income", ...}
  ],
  "account_balance": 1020.00,
  "total_amount": 20.00,
  "count": 3
}
```

---

## 3. List Transactions

**Endpoint:** `GET /api/transactions`
**Authentication:** Required
**Query Parameters:** Multiple filters (see below)
**Response:** `TransactionListResponse` (200 OK)

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Route as TransactionRoute
    participant Service as TransactionService
    participant TxnRepo as TransactionRepository
    participant DB as Database

    Client->>Route: GET /api/transactions?account_id=123&category=groceries&limit=50
    Note over Route: get_current_user()<br/>Injects authenticated User
    Route->>Route: Parse query parameters<br/>(tags comma-separated)
    Route->>Service: get_transactions(user, filters...)

    Service->>TxnRepo: get_filtered(user_id, filters)
    TxnRepo->>DB: SELECT txn.* FROM transactions txn<br/>JOIN accounts acc ON txn.account_id = acc.id<br/>WHERE acc.user_id = ?<br/>AND [apply all filters]<br/>ORDER BY date DESC<br/>LIMIT ? OFFSET ?

    Note over DB: Filters applied:<br/>- account_id<br/>- date range<br/>- category<br/>- merchant (LIKE)<br/>- tags (ANY match)<br/>- der_category<br/>- der_merchant (LIKE)

    DB-->>TxnRepo: Return Transactions[]
    TxnRepo->>DB: SELECT COUNT(*) with same filters
    DB-->>TxnRepo: Return total count
    Repo-->>Service: Return (transactions, total)

    Service-->>Route: Return (transactions, total)
    Route->>Route: Build TransactionListResponse
    Route-->>Client: 200 OK<br/>{transactions: [...], total: N}
```

### Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `account_id` | int | Filter by account | `?account_id=123` |
| `start_date` | date | Start date (inclusive) | `?start_date=2026-01-01` |
| `end_date` | date | End date (inclusive) | `?end_date=2026-01-31` |
| `category` | string | Exact category match | `?category=groceries` |
| `merchant` | string | Partial merchant match | `?merchant=Whole` |
| `tags` | string | Comma-separated, ANY match | `?tags=food,essential` |
| `der_category` | string | Exact derived category | `?der_category=shopping` |
| `der_merchant` | string | Partial derived merchant | `?der_merchant=amazon` |
| `limit` | int | Max results (1-1000) | `?limit=50` |
| `offset` | int | Pagination offset | `?offset=100` |

### Business Logic

1. Joins transactions with accounts to enforce user ownership
2. Applies all provided filters (AND logic)
3. Tags use ANY match (OR logic within tags)
4. Merchant/der_merchant use partial matching (LIKE)
5. Returns total count for pagination
6. Results sorted by date (newest first)

### Multi-Tenant Security

- Always joins with accounts table: `JOIN accounts ON transactions.account_id = accounts.id`
- Filters by `accounts.tenant_id = context.tenant.id`
- Users can see transactions from all tenant accounts (shared family/household)
- Complete isolation between different tenants
- Permission checks ensure VIEWER cannot modify transactions

---

## 4. Get Transaction

**Endpoint:** `GET /api/transactions/{transaction_id}`
**Authentication:** Required
**Path Parameters:** `transaction_id` (integer)
**Response:** `TransactionResponse` (200 OK)

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Route as TransactionRoute
    participant Service as TransactionService
    participant TxnRepo as TransactionRepository
    participant DB as Database

    Client->>Route: GET /api/transactions/456
    Note over Route: get_current_user()<br/>Injects authenticated User
    Route->>Service: get_transaction(transaction_id=456, user)

    Service->>TxnRepo: get_by_id_and_user(transaction_id=456, user_id)
    TxnRepo->>DB: SELECT txn.* FROM transactions txn<br/>JOIN accounts acc ON txn.account_id = acc.id<br/>WHERE txn.id = 456 AND acc.user_id = ?

    alt Transaction found
        DB-->>TxnRepo: Return Transaction
        TxnRepo-->>Service: Return Transaction
        Service-->>Route: Return Transaction
        Route-->>Client: 200 OK<br/>TransactionResponse
    else Transaction not found or unauthorized
        DB-->>TxnRepo: Return None
        TxnRepo-->>Service: Return None
        Service->>Service: Raise NotFoundException
        Service-->>Route: 404 Not Found
        Route-->>Client: 404 Not Found
    end
```

### Business Logic

1. Fetches transaction by ID with user ownership check via account join
2. Returns 404 if transaction doesn't exist OR user doesn't own the account
3. Single database query with join

### Security Note

Returns same error (404) whether transaction doesn't exist or belongs to another user's account. Prevents information disclosure.

---

## 5. Update Transaction

**Endpoint:** `PATCH /api/transactions/{transaction_id}`
**Authentication:** Required
**Path Parameters:** `transaction_id` (integer)
**Request Body:** `TransactionUpdate` (partial)
**Response:** `TransactionResponse` (200 OK)

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Route as TransactionRoute
    participant Service as TransactionService
    participant TxnRepo as TransactionRepository
    participant AcctRepo as AccountRepository
    participant DB as Database

    Client->>Route: PATCH /api/transactions/456<br/>{amount: -75.00}
    Note over Route: get_current_user()<br/>Injects authenticated User
    Route->>Service: update_transaction(transaction_id=456, data, user)

    Service->>TxnRepo: get_by_id_and_user(transaction_id=456, user_id)
    TxnRepo->>DB: SELECT txn.* FROM transactions txn<br/>JOIN accounts acc ON txn.account_id = acc.id<br/>WHERE txn.id = 456 AND acc.user_id = ?

    alt Transaction found
        DB-->>TxnRepo: Return Transaction
        TxnRepo-->>Service: Return Transaction

        Service->>AcctRepo: get_by_id(transaction.account_id)
        AcctRepo->>DB: SELECT * FROM accounts WHERE id = ?
        DB-->>AcctRepo: Return Account
        AcctRepo-->>Service: Return Account

        alt Amount changed
            Service->>Service: Calculate balance delta<br/>delta = new_amount - old_amount
            Service->>Service: Update transaction fields
            Service->>TxnRepo: update(transaction)
            TxnRepo->>DB: UPDATE transactions SET ...<br/>WHERE id = 456
            TxnRepo->>DB: COMMIT

            Service->>Service: Update account balance<br/>balance += delta
            Service->>AcctRepo: update(account)
            AcctRepo->>DB: UPDATE accounts SET balance = ?
            AcctRepo->>DB: COMMIT
        else Amount unchanged
            Service->>Service: Update transaction fields
            Service->>TxnRepo: update(transaction)
            TxnRepo->>DB: UPDATE transactions SET ...<br/>WHERE id = 456
            TxnRepo->>DB: COMMIT
            Note over Service: Skip balance update
        end

        Service-->>Route: Return Transaction
        Route-->>Client: 200 OK<br/>TransactionResponse

    else Transaction not found
        Service->>Service: Raise NotFoundException
        Service-->>Route: 404 Not Found
        Route-->>Client: 404 Not Found
    end
```

### Business Logic

1. Verifies transaction ownership via account join
2. Applies ONLY fields present in request (partial update)
3. **Smart Balance Recalculation**:
   - If `amount` changed: calculates delta and updates account balance
   - If `amount` unchanged: skips balance update for efficiency
4. Balance delta = `new_amount - old_amount`
5. Other fields (category, merchant, etc.) don't affect balance

### Allowed Updates

All fields are optional (partial update):
- `amount`: Triggers balance recalculation
- `date`, `category`, `description`, `merchant`, `location`, `tags`
- `der_category`, `der_merchant`

---

## 6. Delete Transaction

**Endpoint:** `DELETE /api/transactions/{transaction_id}`
**Authentication:** Required
**Path Parameters:** `transaction_id` (integer)
**Response:** 204 No Content

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Route as TransactionRoute
    participant Service as TransactionService
    participant TxnRepo as TransactionRepository
    participant AcctRepo as AccountRepository
    participant DB as Database

    Client->>Route: DELETE /api/transactions/456
    Note over Route: get_current_user()<br/>Injects authenticated User
    Route->>Service: delete_transaction(transaction_id=456, user)

    Service->>TxnRepo: get_by_id_and_user(transaction_id=456, user_id)
    TxnRepo->>DB: SELECT txn.* FROM transactions txn<br/>JOIN accounts acc ON txn.account_id = acc.id<br/>WHERE txn.id = 456 AND acc.user_id = ?

    alt Transaction found
        DB-->>TxnRepo: Return Transaction
        TxnRepo-->>Service: Return Transaction

        Service->>AcctRepo: get_by_id(transaction.account_id)
        AcctRepo->>DB: SELECT * FROM accounts WHERE id = ?
        DB-->>AcctRepo: Return Account
        AcctRepo-->>Service: Return Account

        Service->>TxnRepo: delete(transaction)
        TxnRepo->>DB: DELETE FROM transactions<br/>WHERE id = 456
        TxnRepo->>DB: COMMIT
        TxnRepo-->>Service: Success

        Service->>Service: Reverse balance change<br/>balance -= transaction.amount
        Service->>AcctRepo: update(account)
        AcctRepo->>DB: UPDATE accounts SET balance = ?
        AcctRepo->>DB: COMMIT
        AcctRepo-->>Service: Success

        Service-->>Route: Success
        Route-->>Client: 204 No Content

    else Transaction not found
        Service->>Service: Raise NotFoundException
        Service-->>Route: 404 Not Found
        Route-->>Client: 404 Not Found
    end
```

### Business Logic

1. Verifies transaction ownership via account join
2. Deletes transaction record
3. **Automatic Balance Correction**: `balance -= transaction.amount`
4. Two separate commits (transaction delete, then balance update)
5. Returns 204 No Content on success (no response body)

### Example

If deleting a transaction with `amount = -50.00` (expense):
- Balance adjustment: `balance -= (-50.00)` → balance increases by 50.00
- This reverses the original expense

---

## Error Responses

All endpoints use consistent error format:

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```
**Cause:** Missing, invalid, or expired JWT token

### 404 Not Found
```json
{
  "detail": "Account not found"
}
```
**Cause:** Resource doesn't exist OR user doesn't have access (security)

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "category"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```
**Cause:** Pydantic validation failed (invalid request body)

### 400 Bad Request
```json
{
  "detail": "Batch must contain at least 1 transaction"
}
```
**Cause:** Business logic validation failed

---

## Performance Considerations

### Database Indexes

Recommended indexes for optimal query performance:

```sql
-- Multi-tenant security (critical)
CREATE INDEX idx_accounts_tenant_id ON accounts(tenant_id);
CREATE UNIQUE INDEX idx_tenant_memberships_tenant_user ON tenant_memberships(tenant_id, user_id);
CREATE INDEX idx_transactions_account_id ON transactions(account_id);

-- Transaction filtering
CREATE INDEX idx_transactions_date ON transactions(date DESC);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_transactions_merchant ON transactions(merchant);
CREATE INDEX idx_transactions_der_category ON transactions(der_category);

-- Composite for common queries
CREATE INDEX idx_transactions_account_date ON transactions(account_id, date DESC);
CREATE INDEX idx_transactions_account_category ON transactions(account_id, category);
CREATE INDEX idx_transactions_account_der_category ON transactions(account_id, der_category);
```

### Batch Operations

For importing large datasets:
- Use `POST /api/transactions/batch` instead of individual creates
- Maximum 100 transactions per batch
- For >100, chunk into multiple batch requests
- Performance gain: ~10-50x faster than individual inserts

### Query Optimization

- List endpoints use LIMIT/OFFSET pagination
- Default limit: 100 transactions
- Maximum limit: 1000 transactions
- Use filters to reduce result set size

---

## Testing

All endpoints have comprehensive test coverage. See `tests/test_accounts.py`, `tests/test_transactions.py`, and `tests/test_tenant_management.py`.

**Test Suite:**
- 106/106 tests passing
  - 82 account/transaction tests
  - 24 tenant management tests
- Coverage includes: success cases, validation, multi-tenant security, role-based permissions, atomicity, error handling

**Run Tests:**
```bash
pytest
pytest tests/test_accounts.py -v
pytest tests/test_transactions.py::TestBatchTransactionCreation -v
pytest tests/test_tenant_management.py -v
```

---

## OpenAPI Documentation

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Features:
- Try-it-out functionality for all endpoints
- Request/response schema validation
- Authentication token configuration
- Example requests and responses