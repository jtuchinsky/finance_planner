"""Tenant role enum for role-based access control."""

from enum import Enum as PyEnum


class TenantRole(str, PyEnum):
    """
    Tenant membership roles with hierarchical permissions.

    Role Hierarchy (highest to lowest):
    1. OWNER - Full control, can delete tenant, manage all users
    2. ADMIN - Manage data, invite/remove users (except owner)
    3. MEMBER - Read/write data, cannot manage users
    4. VIEWER - Read-only access to all data

    Permissions:
    - OWNER: Everything (delete tenant, transfer ownership, manage all users/data)
    - ADMIN: Manage accounts/transactions/budgets, invite/remove members
    - MEMBER: Create/edit/delete accounts and transactions
    - VIEWER: Read-only access (useful for accountants, advisors)
    """

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"