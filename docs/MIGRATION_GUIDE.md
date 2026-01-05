# Multi-Tenant Migration Guide

This guide explains the migration from single-user isolation to multi-tenant architecture and what it means for existing users.

## Overview

Finance Planner has been upgraded from a single-user system to a multi-tenant architecture that enables families and households to collaborate on shared financial accounts while maintaining complete data isolation between different tenant groups.

## What Changed

### Before (Single-User Isolation)
- Each user had completely isolated accounts and transactions
- No way to share financial data with family members
- Users could only see their own data

### After (Multi-Tenant with Shared Access)
- Users belong to tenants (families/households)
- All members of a tenant share the same accounts and transactions
- Role-based permissions control what each member can do
- Complete isolation between different tenant groups

## Migration Details

### Date: January 4, 2026

All existing users were migrated to a single "Shared Tenant" with the following structure:

- **1 Tenant Created**: "Shared Tenant"
- **49 Users Migrated**: All existing users
- **79 Accounts Migrated**: All linked to the shared tenant
- **8 Transactions Preserved**: All data intact

### User Assignments

- **First User (ID 1)**: Assigned as **OWNER**
  - Full control over the tenant
  - Can invite/remove members
  - Can change member roles
  - Can update tenant settings

- **Remaining 48 Users**: Assigned as **MEMBER**
  - Can create, edit, and delete accounts and transactions
  - Can view all tenant data
  - Cannot manage other users

## Role Hierarchy

### OWNER
**Permissions:**
- All ADMIN permissions
- Change member roles
- Update tenant name
- Cannot be removed from tenant

**Use Case:** Household head, primary account manager

### ADMIN
**Permissions:**
- All MEMBER permissions
- Invite new members
- Remove members (except OWNER)

**Use Case:** Co-manager, spouse with administrative access

### MEMBER
**Permissions:**
- View all tenant accounts and transactions
- Create new accounts
- Create, edit, and delete transactions
- Cannot manage users

**Use Case:** Family member with full financial access

### VIEWER
**Permissions:**
- View all tenant accounts and transactions (read-only)
- Cannot create, edit, or delete anything
- Cannot manage users

**Use Case:** Accountant, financial advisor, read-only family member

## New Features Available

### 1. View Current Tenant
```http
GET /api/tenants/me
Authorization: Bearer <token>
```

### 2. List All Members
```http
GET /api/tenants/me/members
Authorization: Bearer <token>
```

### 3. Invite New Member (ADMIN/OWNER only)
```http
POST /api/tenants/me/members
Authorization: Bearer <token>
Content-Type: application/json

{
  "auth_user_id": "user-123",
  "role": "member"
}
```

### 4. Change Member Role (OWNER only)
```http
PATCH /api/tenants/me/members/{user_id}/role
Authorization: Bearer <token>
Content-Type: application/json

{
  "role": "admin"
}
```

### 5. Remove Member (ADMIN/OWNER only)
```http
DELETE /api/tenants/me/members/{user_id}
Authorization: Bearer <token>
```

## JWT Token Changes

### Before
```json
{
  "sub": "user-123",
  "exp": 1767622597
}
```

### After
```json
{
  "sub": "user-123",
  "tenant_id": "1",
  "exp": 1767622597
}
```

**Important:** All JWT tokens issued by MCP_Auth now include a `tenant_id` claim. This is required for Finance Planner to work correctly.

## Data Sharing Behavior

### Before Migration
- User A creates account "Savings" → Only User A can see it
- User B creates account "Checking" → Only User B can see it

### After Migration
- User A creates account "Savings" → **All members** of shared tenant can see it
- User B creates account "Checking" → **All members** of shared tenant can see it
- Both users can create transactions in each other's accounts

**This is intentional!** The new system is designed for families/households to collaborate on shared finances.

## Frequently Asked Questions

### Q: Can I still have private accounts?
**A:** Not within the same tenant. All accounts are shared with all members of your tenant. If you need private accounts, you would need to be in a separate tenant.

### Q: Can I be part of multiple tenants?
**A:** The architecture supports this, but the current implementation focuses on single-tenant usage. Multi-tenant switching is planned for a future release.

### Q: What happens if I'm removed from a tenant?
**A:** You lose access to all accounts and transactions associated with that tenant. You would need to be re-invited to regain access.

### Q: Can the OWNER be changed?
**A:** No, the OWNER role is fixed and cannot be changed or transferred. The OWNER also cannot be removed from the tenant.

### Q: How do I create a new tenant?
**A:** Currently, tenants are created during the MCP_Auth registration process. Contact your system administrator to set up additional tenants.

### Q: Are my old transactions safe?
**A:** Yes! All 8 existing transactions were preserved during the migration. No data was lost.

## Permission Matrix

| Action | OWNER | ADMIN | MEMBER | VIEWER |
|--------|-------|-------|--------|--------|
| View accounts & transactions | ✅ | ✅ | ✅ | ✅ |
| Create accounts | ✅ | ✅ | ✅ | ❌ |
| Edit accounts | ✅ | ✅ | ✅ | ❌ |
| Delete accounts | ✅ | ✅ | ✅ | ❌ |
| Create transactions | ✅ | ✅ | ✅ | ❌ |
| Edit transactions | ✅ | ✅ | ✅ | ❌ |
| Delete transactions | ✅ | ✅ | ✅ | ❌ |
| Invite members | ✅ | ✅ | ❌ | ❌ |
| Remove members | ✅ | ✅ | ❌ | ❌ |
| Change member roles | ✅ | ❌ | ❌ | ❌ |
| Update tenant name | ✅ | ❌ | ❌ | ❌ |

## Rollback Information

A database backup was created before migration:
- Backup file: `finance_planner.db.backup_20260105_091200`
- Migration version: `a69fac84f6cf`

To rollback (if necessary):
```bash
# Restore from backup
cp finance_planner.db.backup_20260105_091200 finance.db

# Or downgrade migration
alembic downgrade c61541b90ee5
```

**Note:** Rolling back will remove all multi-tenant features and return to single-user isolation.

## Support

If you experience issues with the migration or have questions:

1. Check the [main README](../README.md) for configuration details
2. Review the [API documentation](http://localhost:8000/docs) (when server is running)
3. Open an issue on GitHub

## Technical Details

For developers interested in the technical implementation:

- Migration file: `alembic/versions/a69fac84f6cf_add_multi_tenant_support.py`
- Test coverage: 106 tests (24 new tenant management tests)
- Models: `Tenant`, `TenantMembership`, `TenantRole`, `TenantContext`
- New routes: `/api/tenants/*` endpoints
- Updated routes: All account/transaction endpoints now tenant-scoped

## Summary

The multi-tenant migration successfully:
- ✅ Preserved all existing data (49 users, 79 accounts, 8 transactions)
- ✅ Created hierarchical role system (OWNER > ADMIN > MEMBER > VIEWER)
- ✅ Enabled family/household collaboration
- ✅ Maintained complete isolation between tenant groups
- ✅ Maintained backward compatibility for existing API endpoints
- ✅ Added comprehensive tenant management features

Your data is safe, and you now have powerful new collaboration features!
