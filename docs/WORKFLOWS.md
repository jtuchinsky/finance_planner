# Authentication & Authorization Workflows

Technical documentation for Finance Planner's authentication and authorization system.

## Table of Contents

- [Overview](#overview)
- [The Front Door Workflow](#the-front-door-workflow)
- [Detailed Implementation](#detailed-implementation)
- [Request Flow Diagrams](#request-flow-diagrams)
- [Code Examples](#code-examples)
- [Error Handling](#error-handling)
- [Testing Strategy](#testing-strategy)
- [Security Considerations](#security-considerations)
- [Integration with MCP_Auth](#integration-with-mcpauth)

---

## Overview

Finance Planner implements a **multi-tenant, role-based authentication and authorization system** that:

1. **Validates JWT tokens** from MCP_Auth using shared SECRET_KEY
2. **Auto-creates user records** on first API request
3. **Enforces tenant membership** through TenantMembership table
4. **Applies RBAC permissions** via four-tier role hierarchy (OWNER/ADMIN/MEMBER/VIEWER)
5. **Ensures tenant isolation** at repository and service layers

### Key Principles

- **Stateless Authentication**: JWT tokens contain all required context
- **Zero Trust**: Every request validates token, membership, and permissions
- **Fail Secure**: Authorization failures return 403/404 (never leak information)
- **Tenant Isolation**: Data queries always filtered by tenant_id
- **RBAC Enforcement**: Permissions checked in service layer before data access

---

## The Front Door Workflow

This is the **canonical request path** for every protected endpoint in Finance Planner.

### High-Level Flow

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  MCP_Auth   │      │   Client    │      │  Finance    │
│             │      │             │      │  Planner    │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       │  1. Login          │                    │
       │◄───────────────────┤                    │
       │                    │                    │
       │  2. JWT Token      │                    │
       │   {sub, tenant_id} │                    │
       ├───────────────────►│                    │
       │                    │                    │
       │                    │  3. API Request    │
       │                    │    + JWT Token     │
       │                    ├───────────────────►│
       │                    │                    │
       │                    │                    │  4. Validate JWT
       │                    │                    │     (HS256 + SECRET_KEY)
       │                    │                    ├─────┐
       │                    │                    │     │
       │                    │                    │◄────┘
       │                    │                    │
       │                    │                    │  5. Extract Claims
       │                    │                    │     (sub, tenant_id)
       │                    │                    ├─────┐
       │                    │                    │     │
       │                    │                    │◄────┘
       │                    │                    │
       │                    │                    │  6. Get/Create User
       │                    │                    ├─────┐
       │                    │                    │     │
       │                    │                    │◄────┘
       │                    │                    │
       │                    │                    │  7. Verify Tenant
       │                    │                    ├─────┐
       │                    │                    │     │
       │                    │                    │◄────┘
       │                    │                    │
       │                    │                    │  8. Check Membership
       │                    │                    ├─────┐
       │                    │                    │     │
       │                    │                    │◄────┘
       │                    │                    │
       │                    │                    │  9. Build TenantContext
       │                    │                    │     (user, tenant, role)
       │                    │                    ├─────┐
       │                    │                    │     │
       │                    │                    │◄────┘
       │                    │                    │
       │                    │ 10. Response       │
       │                    │◄───────────────────┤
       │                    │                    │
```

### Step-by-Step Breakdown

#### 1. User Authenticates with MCP_Auth

**External System** - User logs in to MCP_Auth service.

**MCP_Auth Returns JWT:**
```json
{
  "sub": "auth-user-123",
  "tenant_id": 1,
  "exp": 1737000000,
  "iat": 1736999400
}
```

**Claims:**
- `sub` (subject): User's auth_user_id from MCP_Auth
- `tenant_id`: Which tenant the user is accessing (family/household)
- `exp` (expiration): Token validity timestamp (typically 15 minutes)
- `iat` (issued at): When token was created

#### 2. Client Makes API Request

**HTTP Request:**
```http
GET /api/accounts HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Required Header:**
- `Authorization: Bearer <jwt_token>`

#### 3. FastAPI Route with Dependency Injection

**Route Handler:**
```python
# app/routes/account_routes.py
@router.get("/", response_model=AccountListResponse)
async def list_accounts(
    context: TenantContext = Depends(get_tenant_context),  # ← THE GATE
    db: Session = Depends(get_db)
):
    service = AccountService(db)
    accounts = service.get_tenant_accounts(context)
    return AccountListResponse(accounts=accounts, total=len(accounts))
```

**Key Point:** The `Depends(get_tenant_context)` dependency executes BEFORE the route handler, acting as the "front door" that validates everything.

#### 4. JWT Validation (HS256 + SECRET_KEY)

**File:** `app/core/security.py`

```python
def decode_jwt(token: str) -> dict:
    """
    Decode and validate JWT token using shared SECRET_KEY.

    Validates:
    - Signature (HS256 algorithm)
    - Expiration timestamp
    - Required claims (sub, exp)

    Raises UnauthorizedException if invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,  # ← MUST match MCP_Auth
            algorithms=["HS256"]
        )

        # Validate required claims
        if payload.get("exp") is None:
            raise UnauthorizedException("Token missing expiration")

        if payload.get("sub") is None:
            raise UnauthorizedException("Token missing user identifier")

        return payload

    except JWTError as e:
        raise UnauthorizedException(f"Invalid token: {str(e)}")
```

**What Gets Validated:**
- ✅ JWT signature matches SECRET_KEY
- ✅ Token has not expired
- ✅ Token contains required `sub` claim
- ✅ Token contains required `exp` claim

**Failure:** Returns 401 Unauthorized

#### 5. Extract Claims (sub, tenant_id)

**File:** `app/core/security.py`

```python
def extract_user_and_tenant(token: str) -> tuple[str, str]:
    """
    Extract both user_id and tenant_id from JWT.

    Returns:
        Tuple of (auth_user_id, tenant_id)

    Raises:
        UnauthorizedException if either claim is missing
    """
    payload = decode_jwt(token)  # Validated in step 4

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    if not user_id or not tenant_id:
        raise UnauthorizedException("Invalid token claims")

    return user_id, tenant_id
```

**Extracted Values:**
- `auth_user_id` (from `sub`) → "auth-user-123"
- `tenant_id` → 1

**Failure:** Returns 401 Unauthorized if claims missing

#### 6. Get or Auto-Create User

**File:** `app/repositories/user_repository.py`

```python
def get_or_create_by_auth_id(self, auth_user_id: str) -> User:
    """
    Get user by auth_user_id or create if doesn't exist.

    This is called automatically when a user makes their first API
    request with a valid JWT from MCP_Auth.

    Args:
        auth_user_id: User ID from MCP_Auth JWT 'sub' claim

    Returns:
        User object (either existing or newly created)
    """
    # Try to find existing user
    user = self.db.query(User).filter(
        User.auth_user_id == auth_user_id
    ).first()

    if not user:
        # First request - auto-create user record
        user = User(auth_user_id=auth_user_id)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

    return user
```

**Behavior:**
- **First Request:** Creates User record in finance_planner database
- **Subsequent Requests:** Returns existing User
- **No Duplicates:** auth_user_id is unique constraint

**Database Operation:**
```sql
-- First request
INSERT INTO users (auth_user_id, created_at, updated_at)
VALUES ('auth-user-123', NOW(), NOW());

-- Subsequent requests
SELECT * FROM users WHERE auth_user_id = 'auth-user-123';
```

#### 7. Verify Tenant Exists

**File:** `app/dependencies.py`

```python
# Verify tenant exists
tenant_repo = TenantRepository(db)
tenant = tenant_repo.get_by_id(tenant_id)

if not tenant:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Tenant {tenant_id} not found"
    )
```

**Purpose:** Ensure the tenant_id in the JWT corresponds to a real tenant.

**Failure:** Returns 404 Not Found if tenant doesn't exist

#### 8. Check Membership (The Gate)

**File:** `app/dependencies.py`

```python
# Verify user has membership in this tenant
membership_repo = TenantMembershipRepository(db)
membership = membership_repo.get_membership(user.id, tenant_id)

if not membership:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"User not member of tenant {tenant_id}"
    )
```

**Database Query:**
```sql
SELECT * FROM tenant_memberships
WHERE user_id = ? AND tenant_id = ?;
```

**Purpose:** The membership gate ensures the user actually belongs to the tenant they're trying to access.

**Failure:** Returns 403 Forbidden if user is not a member

**This is Critical:** Even with a valid JWT, users can only access tenants they're members of.

#### 9. Build TenantContext

**File:** `app/dependencies.py`

```python
return TenantContext(
    user=user,           # User object from step 6
    tenant=tenant,       # Tenant object from step 7
    role=membership.role # Role from step 8 (OWNER/ADMIN/MEMBER/VIEWER)
)
```

**TenantContext Structure:**
```python
@dataclass
class TenantContext:
    user: User          # Authenticated user
    tenant: Tenant      # Current tenant (family/household)
    role: TenantRole    # User's role in this tenant

    # Helper methods for RBAC
    def can_write(self) -> bool
    def is_admin_or_higher(self) -> bool
    def is_owner(self) -> bool
```

**What's Injected:** The route handler receives this complete context object.

#### 10. Service Layer (RBAC + Business Logic)

**File:** `app/services/account_service.py`

```python
def create_account(self, data: AccountCreate, context: TenantContext) -> Account:
    """Create new account for tenant."""

    # RBAC check - MEMBER or higher required
    if not context.can_write():
        raise ForbiddenException("Insufficient permissions to create accounts")

    # Business logic
    account = Account(
        tenant_id=context.tenant.id,  # Tenant association
        user_id=context.user.id,      # Audit trail
        name=data.name,
        account_type=data.account_type,
        balance=data.initial_balance or 0.00
    )

    return self.repo.create(account)
```

**Permission Enforcement:**
- VIEWER (read-only) → Cannot create accounts
- MEMBER/ADMIN/OWNER → Can create accounts

**Failure:** Returns 403 Forbidden if insufficient permissions

#### 11. Repository Layer (Tenant-Filtered Queries)

**File:** `app/repositories/account_repository.py`

```python
def get_by_tenant(self, tenant_id: int) -> list[Account]:
    """Get all accounts for a tenant."""
    return (
        self.db.query(Account)
        .filter(Account.tenant_id == tenant_id)  # ← TENANT ISOLATION
        .order_by(Account.created_at.desc())
        .all()
    )
```

**SQL Query:**
```sql
SELECT * FROM accounts
WHERE tenant_id = 1  -- ← Prevents cross-tenant data access
ORDER BY created_at DESC;
```

**Multi-Tenant Isolation:**
- Every query filters by `tenant_id`
- Users can ONLY see data from their tenant
- Complete separation between tenants
- No possibility of data leakage

---

## Detailed Implementation

### get_tenant_context Dependency

**File:** `app/dependencies.py:50-110`

This is the core "front door" dependency that all protected endpoints use.

```python
async def get_tenant_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> TenantContext:
    """
    FastAPI dependency to validate JWT and build tenant context.

    Flow:
    1. Extract token from Authorization: Bearer <token>
    2. Validate JWT and extract user_id and tenant_id
    3. Get or auto-create User record
    4. Verify Tenant exists
    5. Verify User has membership in Tenant
    6. Return TenantContext with user, tenant, and role

    Raises:
        HTTPException 401: If token invalid or expired
        HTTPException 403: If user not member of tenant
        HTTPException 404: If tenant not found
    """
    try:
        # Step 1: Extract token
        token = credentials.credentials

        # Steps 2-3: Validate JWT and extract claims
        auth_user_id, tenant_id_str = extract_user_and_tenant(token)
        tenant_id = int(tenant_id_str)

        # Step 4: Get or create user
        user_repo = UserRepository(db)
        user = user_repo.get_or_create_by_auth_id(auth_user_id)

        # Step 5: Verify tenant exists
        tenant_repo = TenantRepository(db)
        tenant = tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found",
            )

        # Step 6: Verify user has membership in this tenant
        membership_repo = TenantMembershipRepository(db)
        membership = membership_repo.get_membership(user.id, tenant_id)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User not member of tenant {tenant_id}",
            )

        # Step 7: Build and return context
        return TenantContext(user=user, tenant=tenant, role=membership.role)

    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tenant_id: {str(e)}",
        )
```

### TenantContext Permission Helpers

**File:** `app/models/tenant_context.py`

```python
@dataclass
class TenantContext:
    user: User
    tenant: Tenant
    role: TenantRole

    def has_permission(self, required_role: TenantRole) -> bool:
        """
        Check if user's role meets or exceeds required role.

        Role hierarchy: OWNER (4) > ADMIN (3) > MEMBER (2) > VIEWER (1)
        """
        role_hierarchy = {
            TenantRole.OWNER: 4,
            TenantRole.ADMIN: 3,
            TenantRole.MEMBER: 2,
            TenantRole.VIEWER: 1,
        }
        return role_hierarchy[self.role] >= role_hierarchy[required_role]

    def is_owner(self) -> bool:
        """Check if user is the tenant owner."""
        return self.role == TenantRole.OWNER

    def is_admin_or_higher(self) -> bool:
        """Check if user is admin or owner."""
        return self.role in (TenantRole.OWNER, TenantRole.ADMIN)

    def can_write(self) -> bool:
        """Check if user has write permissions (MEMBER or higher)."""
        return self.role in (TenantRole.OWNER, TenantRole.ADMIN, TenantRole.MEMBER)

    def can_read(self) -> bool:
        """Check if user has read permissions (all roles can read)."""
        return True
```

**Usage in Services:**
```python
# Require OWNER
if not context.is_owner():
    raise ForbiddenException("Only owner can perform this action")

# Require ADMIN or higher
if not context.is_admin_or_higher():
    raise ForbiddenException("Admin privileges required")

# Require MEMBER or higher (can write)
if not context.can_write():
    raise ForbiddenException("Read-only access")
```

---

## Request Flow Diagrams

### Complete Authentication Flow (Successful Request)

```
┌─────────┐
│ Client  │
└────┬────┘
     │
     │ GET /api/accounts
     │ Authorization: Bearer <jwt>
     │
     ▼
┌─────────────────────────────────────┐
│ FastAPI HTTPBearer Security         │
│ - Extracts token from header        │
│ - Validates Bearer prefix           │
└────┬────────────────────────────────┘
     │
     │ credentials.credentials = <jwt>
     │
     ▼
┌─────────────────────────────────────┐
│ get_tenant_context() Dependency     │
│                                     │
│ Step 1: decode_jwt(token)           │
│   ✓ Validate signature (HS256)     │
│   ✓ Check expiration                │
│   ✓ Verify 'sub' claim exists      │
└────┬────────────────────────────────┘
     │
     │ Valid JWT payload
     │
     ▼
┌─────────────────────────────────────┐
│ Step 2: extract_user_and_tenant()  │
│   ✓ Extract sub → auth_user_id     │
│   ✓ Extract tenant_id claim        │
└────┬────────────────────────────────┘
     │
     │ auth_user_id="user-123"
     │ tenant_id=1
     │
     ▼
┌─────────────────────────────────────┐
│ Step 3: UserRepository              │
│   get_or_create_by_auth_id()        │
│                                     │
│   IF user exists:                   │
│     → Return existing User          │
│   ELSE:                              │
│     → Create new User               │
│     → Commit to database            │
│     → Return new User               │
└────┬────────────────────────────────┘
     │
     │ User object
     │
     ▼
┌─────────────────────────────────────┐
│ Step 4: TenantRepository            │
│   get_by_id(tenant_id)              │
│                                     │
│   IF tenant exists:                 │
│     → Return Tenant                 │
│   ELSE:                              │
│     → HTTPException 404             │
└────┬────────────────────────────────┘
     │
     │ Tenant object
     │
     ▼
┌─────────────────────────────────────┐
│ Step 5: TenantMembershipRepository  │
│   get_membership(user.id, tenant_id)│
│                                     │
│   IF membership exists:             │
│     → Return TenantMembership       │
│   ELSE:                              │
│     → HTTPException 403             │
└────┬────────────────────────────────┘
     │
     │ TenantMembership (with role)
     │
     ▼
┌─────────────────────────────────────┐
│ Step 6: Build TenantContext         │
│   TenantContext(                    │
│     user=user,                      │
│     tenant=tenant,                  │
│     role=membership.role            │
│   )                                 │
└────┬────────────────────────────────┘
     │
     │ TenantContext injected
     │
     ▼
┌─────────────────────────────────────┐
│ Route Handler Executes              │
│   list_accounts(context, db)        │
└────┬────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ AccountService                      │
│   get_tenant_accounts(context)      │
│   - No permission check (read op)   │
└────┬────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ AccountRepository                   │
│   get_by_tenant(context.tenant.id)  │
│   - Query: WHERE tenant_id = 1      │
└────┬────────────────────────────────┘
     │
     │ List[Account]
     │
     ▼
┌─────────────────────────────────────┐
│ Response: 200 OK                    │
│ {                                   │
│   "accounts": [...],                │
│   "total": 5                        │
│ }                                   │
└─────────────────────────────────────┘
```

### Error Flows

#### Invalid JWT Token (401)

```
Client → JWT Validation
         ├─ Invalid signature → 401 Unauthorized
         ├─ Expired token → 401 Unauthorized
         ├─ Missing 'sub' → 401 Unauthorized
         ├─ Missing 'exp' → 401 Unauthorized
         └─ Malformed JWT → 401 Unauthorized
```

#### Non-Existent Tenant (404)

```
Client → JWT Valid → Extract Claims → Get/Create User
         → Tenant Lookup → Tenant Not Found → 404 Not Found
```

#### No Tenant Membership (403)

```
Client → JWT Valid → Extract Claims → Get/Create User
         → Tenant Found → Membership Check → Not a Member
         → 403 Forbidden
```

#### Insufficient Permissions (403)

```
Client → JWT Valid → ... → TenantContext Created
         → Route Handler → Service Layer
         → Permission Check → VIEWER trying to write
         → 403 Forbidden
```

---

## Code Examples

### Example 1: Create Account (Write Operation)

**Request:**
```bash
curl -X POST "http://localhost:8000/api/accounts" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chase Checking",
    "account_type": "checking",
    "initial_balance": 1500.00
  }'
```

**Route:**
```python
@router.post("/", response_model=AccountResponse, status_code=201)
async def create_account(
    data: AccountCreate,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    service = AccountService(db)
    account = service.create_account(data, context)
    return account
```

**Service (with RBAC):**
```python
def create_account(self, data: AccountCreate, context: TenantContext) -> Account:
    # Permission check - MEMBER or higher required
    if not context.can_write():
        raise ForbiddenException("Insufficient permissions")

    account = Account(
        tenant_id=context.tenant.id,  # From authenticated context
        user_id=context.user.id,
        name=data.name,
        account_type=data.account_type,
        balance=data.initial_balance or 0.00
    )

    return self.repo.create(account)
```

**Repository (with tenant isolation):**
```python
def create(self, account: Account) -> Account:
    self.db.add(account)
    self.db.commit()
    self.db.refresh(account)
    return account
```

**SQL Generated:**
```sql
INSERT INTO accounts (tenant_id, user_id, name, account_type, balance, created_at, updated_at)
VALUES (1, 5, 'Chase Checking', 'checking', 1500.00, NOW(), NOW());
```

### Example 2: List Accounts (Read Operation)

**Request:**
```bash
curl -X GET "http://localhost:8000/api/accounts" \
  -H "Authorization: Bearer eyJhbGc..."
```

**Service:**
```python
def get_tenant_accounts(self, context: TenantContext) -> list[Account]:
    # No permission check - all roles can read
    return self.repo.get_by_tenant(context.tenant.id)
```

**Repository:**
```python
def get_by_tenant(self, tenant_id: int) -> list[Account]:
    return (
        self.db.query(Account)
        .filter(Account.tenant_id == tenant_id)  # Tenant isolation
        .order_by(Account.created_at.desc())
        .all()
    )
```

**SQL Generated:**
```sql
SELECT * FROM accounts
WHERE tenant_id = 1
ORDER BY created_at DESC;
```

### Example 3: Update Member Role (OWNER-only Operation)

**Request:**
```bash
curl -X PATCH "http://localhost:8000/api/tenants/me/members/5/role" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

**Service:**
```python
def update_member_role(
    self,
    user_id: int,
    role_update: TenantRoleUpdate,
    context: TenantContext
) -> TenantMembership:
    # Only OWNER can change roles
    if not context.is_owner():
        raise ForbiddenException("Only owner can change member roles")

    membership = self.membership_repo.get_membership(
        user_id,
        context.tenant.id
    )

    if not membership:
        raise NotFoundException("Member not found")

    # Additional business rules
    if membership.role == TenantRole.OWNER:
        raise ForbiddenException("Cannot change owner's role")

    if membership.user_id == context.user.id:
        raise ForbiddenException("Cannot change own role")

    membership.role = role_update.role
    return self.membership_repo.update(membership)
```

### Example 4: Batch Transaction Creation (Atomic)

**Service with Transaction:**
```python
def create_transaction_batch(
    self,
    batch_data: TransactionBatchCreate,
    context: TenantContext
):
    # Permission check
    if not context.can_write():
        raise ForbiddenException("Insufficient permissions")

    # Verify account ownership
    account = self.account_repo.get_by_id_and_tenant(
        batch_data.account_id,
        context.tenant.id
    )
    if not account:
        raise NotFoundException("Account not found")

    # Calculate total
    total_amount = sum(txn.amount for txn in batch_data.transactions)

    try:
        # Atomic operation - all or nothing
        transactions = self.transaction_repo.create_bulk(transaction_objects)

        account.balance = float(account.balance) + total_amount
        self.account_repo.update_no_commit(account)

        self.db.commit()  # Single commit point

        # Refresh all objects
        self.db.refresh(account)
        for txn in transactions:
            self.db.refresh(txn)

        return transactions, float(account.balance)

    except Exception as e:
        self.db.rollback()
        raise
```

---

## Error Handling

### Error Response Format

All authentication and authorization errors follow FastAPI's standard error format:

```json
{
  "detail": "Error message here"
}
```

### Error Types and Status Codes

| Error Type | Status Code | When It Occurs | Example Detail |
|------------|-------------|----------------|----------------|
| **Missing Token** | 401 | No Authorization header | "Not authenticated" |
| **Invalid Token** | 401 | JWT validation fails | "Invalid token: Signature verification failed" |
| **Expired Token** | 401 | Token past expiration | "Invalid token: Token is expired" |
| **Missing Claims** | 401 | Required claim absent | "Token missing user identifier" |
| **Tenant Not Found** | 404 | tenant_id doesn't exist | "Tenant 5 not found" |
| **Not a Member** | 403 | No TenantMembership | "User not member of tenant 1" |
| **Insufficient Permissions** | 403 | RBAC check fails | "Insufficient permissions to create accounts" |
| **Resource Not Found** | 404 | Account/Transaction missing | "Account not found" |

### Custom Exception Classes

**File:** `app/core/exceptions.py`

```python
class UnauthorizedException(Exception):
    """Raised when JWT validation fails"""
    pass

class NotFoundException(Exception):
    """Raised when resource not found"""
    pass

class ForbiddenException(Exception):
    """Raised when user lacks required permissions"""
    pass

class ValidationException(Exception):
    """Raised when business logic validation fails"""
    pass
```

### Error Handling in Dependencies

```python
async def get_tenant_context(...) -> TenantContext:
    try:
        # ... authentication logic ...
    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tenant_id: {str(e)}",
        )
```

### Security Note: Consistent Error Messages

**DO NOT** reveal whether a resource exists to unauthorized users:

```python
# ✅ GOOD - Same error for "doesn't exist" and "not authorized"
account = self.repo.get_by_id_and_tenant(account_id, tenant_id)
if not account:
    raise NotFoundException("Account not found")  # Could be either!

# ❌ BAD - Leaks information about what exists
account = self.repo.get_by_id(account_id)
if not account:
    raise NotFoundException("Account doesn't exist")
if account.tenant_id != tenant_id:
    raise ForbiddenException("Access denied")  # Now they know it exists!
```

---

## Testing Strategy

### Test Categories

#### 1. JWT Validation Tests

**File:** `tests/test_auth_middleware.py`

```python
def test_valid_token_accepted(client, auth_headers):
    """Valid JWT token should be accepted"""
    response = client.get("/api/accounts", headers=auth_headers)
    assert response.status_code == 200

def test_expired_token_rejected(client):
    """Expired tokens should return 401"""
    expired_token = create_test_token(expired=True)
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 401

def test_invalid_signature_rejected(client):
    """Tokens signed with wrong key should fail"""
    payload = {"sub": "test-user", "exp": datetime.now(UTC) + timedelta(minutes=15)}
    token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 401

def test_missing_sub_claim_rejected(client):
    """Token without 'sub' claim should be rejected"""
    payload = {"exp": datetime.now(UTC) + timedelta(minutes=15)}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 401
```

#### 2. Auto-User Creation Tests

```python
def test_user_auto_created_on_first_request(client, db_session):
    """User record should be auto-created on first API request"""
    from app.models.user import User

    # Verify no users exist
    assert db_session.query(User).count() == 0

    # Create tenant and membership manually for test
    tenant = Tenant(name="Test Tenant")
    db_session.add(tenant)
    db_session.commit()

    # Make first request
    token = create_test_token(user_id="new-user-123", tenant_id=tenant.id)
    headers = {"Authorization": f"Bearer {token}"}
    client.get("/api/accounts", headers=headers)  # Will fail on membership

    # Verify user was auto-created
    user = db_session.query(User).filter_by(auth_user_id="new-user-123").first()
    assert user is not None

def test_same_user_not_duplicated(client, db_session):
    """Multiple requests from same user should not create duplicates"""
    # ... setup tenant and membership ...

    # Make multiple requests
    client.get("/api/accounts", headers=headers)
    client.get("/api/accounts", headers=headers)
    client.get("/api/accounts", headers=headers)

    # Should only have one user
    users = db_session.query(User).all()
    assert len(users) == 1
```

#### 3. Tenant Membership Tests

```python
def test_user_cannot_access_different_tenant(client, db_session):
    """User should not access accounts from tenant they don't belong to"""
    # Create two tenants
    tenant1 = Tenant(name="Tenant 1")
    tenant2 = Tenant(name="Tenant 2")
    db_session.add_all([tenant1, tenant2])
    db_session.commit()

    # User has membership in tenant1 only
    user = User(auth_user_id="user-123")
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        tenant_id=tenant1.id,
        user_id=user.id,
        role=TenantRole.MEMBER
    )
    db_session.add(membership)
    db_session.commit()

    # Try to access tenant2 (should fail)
    token = create_test_token(user_id="user-123", tenant_id=tenant2.id)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 403
```

#### 4. RBAC Permission Tests

```python
def test_viewer_cannot_create_account(client, auth_headers_viewer):
    """VIEWER role should not be able to create accounts"""
    response = client.post(
        "/api/accounts",
        headers=auth_headers_viewer,
        json={"name": "Test", "account_type": "checking"}
    )
    assert response.status_code == 403

def test_member_can_create_account(client, auth_headers_member):
    """MEMBER role should be able to create accounts"""
    response = client.post(
        "/api/accounts",
        headers=auth_headers_member,
        json={"name": "Test", "account_type": "checking"}
    )
    assert response.status_code == 201

def test_non_owner_cannot_change_roles(client, auth_headers_admin):
    """Only OWNER can change member roles"""
    response = client.patch(
        "/api/tenants/me/members/5/role",
        headers=auth_headers_admin,
        json={"role": "admin"}
    )
    assert response.status_code == 403
```

#### 5. Tenant Isolation Tests

```python
def test_tenant_data_isolation(client, db_session):
    """Users from different tenants should not see each other's data"""
    # Create two tenants with accounts
    tenant1 = create_tenant_with_account(db_session, "Tenant 1")
    tenant2 = create_tenant_with_account(db_session, "Tenant 2")

    # User in tenant1 lists accounts
    token1 = create_test_token(user_id="user-1", tenant_id=tenant1.id)
    response1 = client.get("/api/accounts", headers={"Authorization": f"Bearer {token1}"})

    # User in tenant2 lists accounts
    token2 = create_test_token(user_id="user-2", tenant_id=tenant2.id)
    response2 = client.get("/api/accounts", headers={"Authorization": f"Bearer {token2}"})

    # Each should only see their own tenant's accounts
    assert len(response1.json()["accounts"]) == 1
    assert len(response2.json()["accounts"]) == 1
    assert response1.json()["accounts"][0]["id"] != response2.json()["accounts"][0]["id"]
```

### Test Fixtures

**File:** `tests/conftest.py`

```python
@pytest.fixture
def auth_headers(db_session):
    """Create auth headers with MEMBER role"""
    tenant = Tenant(name="Test Tenant")
    db_session.add(tenant)
    db_session.commit()

    user = User(auth_user_id="test-user")
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        role=TenantRole.MEMBER
    )
    db_session.add(membership)
    db_session.commit()

    token = create_test_token(user_id="test-user", tenant_id=tenant.id)
    return {"Authorization": f"Bearer {token}"}

def create_test_token(user_id="test-user", tenant_id=1, expired=False):
    """Create a test JWT token"""
    if expired:
        exp = datetime.now(UTC) - timedelta(minutes=15)
    else:
        exp = datetime.now(UTC) + timedelta(minutes=15)

    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "exp": exp,
        "iat": datetime.now(UTC)
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
```

---

## Security Considerations

### 1. Shared SECRET_KEY

**Critical:** The `SECRET_KEY` in Finance Planner's `.env` MUST exactly match MCP_Auth's SECRET_KEY.

```bash
# Finance Planner .env
SECRET_KEY=your-super-secret-key-here

# MCP_Auth .env (MUST BE IDENTICAL)
SECRET_KEY=your-super-secret-key-here
```

**Why:** JWT signatures are validated using HS256 algorithm with this shared secret. Mismatched keys result in all tokens being rejected.

**Verification Script:**
```bash
# Check both services have same SECRET_KEY
echo "Finance Planner:"
grep SECRET_KEY /path/to/finance_planner/.env

echo "MCP_Auth:"
grep SECRET_KEY /path/to/MCP_Auth/.env
```

### 2. Token Expiration

**Default:** JWTs typically expire after 15 minutes.

**Behavior:**
- Expired tokens → 401 Unauthorized
- Client must re-authenticate with MCP_Auth
- No token refresh mechanism (by design)

**Configuration:** Token TTL is set in MCP_Auth, not Finance Planner.

### 3. Multi-Tenant Isolation

**Defense in Depth:**

1. **JWT Level:** tenant_id in token payload
2. **Membership Level:** TenantMembership gate checks user belongs to tenant
3. **Repository Level:** All queries filter by tenant_id
4. **SQL Level:** Composite indexes on (tenant_id, ...) columns

**No single point of failure:** Multiple layers prevent data leakage.

### 4. RBAC Enforcement

**Hierarchy:**
```
OWNER (4)
  └─ Can do everything
     └─ ADMIN (3)
        └─ Can manage members + all data ops
           └─ MEMBER (2)
              └─ Can create/edit/delete data
                 └─ VIEWER (1)
                    └─ Read-only access
```

**Enforcement Points:**
- Service layer: Before business logic
- Explicit checks: `context.can_write()`, `context.is_owner()`
- Fail secure: Default deny, explicit allow

### 5. Information Disclosure Prevention

**DO NOT reveal resource existence to unauthorized users:**

```python
# ✅ GOOD
account = repo.get_by_id_and_tenant(id, tenant_id)
if not account:
    raise NotFoundException("Account not found")
# Returns 404 whether account doesn't exist OR unauthorized

# ❌ BAD
account = repo.get_by_id(id)
if not account:
    raise NotFoundException("Account not found")
if account.tenant_id != tenant_id:
    raise ForbiddenException("Access denied")
# Reveals account exists via different error codes!
```

### 6. SQL Injection Protection

**SQLAlchemy ORM handles parameterization automatically:**

```python
# Safe - SQLAlchemy parameterizes values
accounts = db.query(Account).filter(Account.tenant_id == tenant_id).all()

# Generated SQL (parameterized)
# SELECT * FROM accounts WHERE tenant_id = ?
# Parameters: [1]
```

**Never use raw SQL with string interpolation.**

### 7. CORS Configuration

**Production Setup:**

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),  # From .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

```bash
# .env
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

**Development:**
```bash
# .env
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

## Integration with MCP_Auth

### MCP_Auth Responsibilities

1. **User Authentication**: Username/password validation
2. **JWT Generation**: Creates tokens with required claims
3. **Token Signing**: Signs JWTs with HS256 + SECRET_KEY
4. **Tenant Context**: Includes tenant_id in token for Finance Planner

### Finance Planner Responsibilities

1. **JWT Validation**: Verifies signature and expiration
2. **User Auto-Creation**: Creates local User records
3. **Membership Verification**: Enforces tenant membership
4. **RBAC**: Manages and enforces role-based permissions
5. **Data Operations**: All CRUD operations on financial data

### Communication Flow

```
┌──────────────────────┐
│      MCP_Auth        │
│  (Port 8001)         │
│                      │
│  POST /auth/login    │
│  POST /auth/register │
│  POST /auth/refresh  │
└──────────┬───────────┘
           │
           │ Returns JWT:
           │ {
           │   "sub": "user-123",
           │   "tenant_id": 1,
           │   "exp": ...,
           │   "access_token": "eyJ..."
           │ }
           │
           ▼
    ┌─────────────┐
    │   Client    │
    └──────┬──────┘
           │
           │ Authorization: Bearer <jwt>
           │
           ▼
┌──────────────────────┐
│  Finance Planner     │
│  (Port 8000)         │
│                      │
│  All /api/* routes   │
└──────────────────────┘
```

### Required JWT Structure

MCP_Auth MUST include these claims in JWTs for Finance Planner:

```json
{
  "sub": "auth-user-id-from-mcp",
  "tenant_id": 1,
  "exp": 1737000000,
  "iat": 1736999400
}
```

**Optional Claims:**
- `email`: User email (informational)
- `name`: User display name (informational)
- Additional claims ignored by Finance Planner

### Tenant Selection Flow

**When user belongs to multiple tenants:**

1. User logs in to MCP_Auth
2. MCP_Auth shows tenant selection UI
3. User selects tenant (e.g., "Smith Family" vs "Personal")
4. MCP_Auth generates JWT with selected tenant_id
5. Client uses this JWT for all Finance Planner requests
6. To switch tenants, user re-authenticates with MCP_Auth and selects different tenant

### Service Discovery

**Both services must be running:**

```bash
# Terminal 1 - MCP_Auth
cd /path/to/MCP_Auth
source .venv/bin/activate
uvicorn main:app --reload --port 8001

# Terminal 2 - Finance Planner
cd /path/to/finance_planner
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Health Checks:**
```bash
# Verify MCP_Auth is running
curl http://localhost:8001/health

# Verify Finance Planner is running
curl http://localhost:8000/health
```

### End-to-End Integration Test

```bash
# 1. Register user with MCP_Auth
TOKEN=$(curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}' \
  | jq -r '.access_token')

# 2. Use token with Finance Planner
curl -X GET http://localhost:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with empty accounts list (or 403 if no tenant membership)
```

---

## Summary

### The "Front Door" Checklist

Every protected endpoint request goes through this gate:

- [ ] **Step 1:** Extract JWT from Authorization header
- [ ] **Step 2:** Validate JWT signature (HS256 + SECRET_KEY)
- [ ] **Step 3:** Check token expiration
- [ ] **Step 4:** Extract `sub` (user_id) claim
- [ ] **Step 5:** Extract `tenant_id` claim
- [ ] **Step 6:** Get or auto-create User record
- [ ] **Step 7:** Verify Tenant exists (404 if not)
- [ ] **Step 8:** Check TenantMembership (403 if not member)
- [ ] **Step 9:** Build TenantContext with user, tenant, role
- [ ] **Step 10:** Inject context into route handler
- [ ] **Step 11:** Service layer checks RBAC permissions
- [ ] **Step 12:** Repository layer filters by tenant_id

### Key Security Principles

1. **Stateless:** All auth state in JWT, no session storage
2. **Fail Secure:** Authorization failures return generic errors
3. **Defense in Depth:** Multiple layers prevent data leakage
4. **Principle of Least Privilege:** RBAC enforces minimum required permissions
5. **Complete Isolation:** Tenants are fully separated at all layers

### Quick Reference

**Dependencies:**
- `get_tenant_context` - Full authentication + authorization (most endpoints)
- `get_current_user` - Authentication only (special cases like tenant list)

**Permission Helpers:**
- `context.can_write()` - MEMBER or higher
- `context.is_admin_or_higher()` - ADMIN or OWNER
- `context.is_owner()` - OWNER only

**Exception Types:**
- `UnauthorizedException` → 401
- `NotFoundException` → 404
- `ForbiddenException` → 403

**Testing:**
- `create_test_token()` - Generate test JWTs
- `auth_headers` fixture - Pre-configured auth headers
- Test tenant isolation, RBAC, and auto-user creation

---

**Document Version:** 1.0
**Last Updated:** January 2026
**Maintained By:** Finance Planner Team