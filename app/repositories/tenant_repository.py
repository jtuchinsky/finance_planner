"""Repository for Tenant model operations."""

from sqlalchemy.orm import Session
from app.models.tenant import Tenant


class TenantRepository:
    """Repository for Tenant model operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: int) -> Tenant | None:
        """
        Get tenant by ID.

        Args:
            tenant_id: Tenant ID

        Returns:
            Tenant object or None if not found
        """
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_all(self) -> list[Tenant]:
        """
        Get all tenants.

        Returns:
            List of all Tenant objects
        """
        return self.db.query(Tenant).all()

    def create(self, tenant: Tenant) -> Tenant:
        """
        Create a new tenant.

        Args:
            tenant: Tenant object to create

        Returns:
            Created Tenant object with ID populated
        """
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def update(self, tenant: Tenant) -> Tenant:
        """
        Update an existing tenant.

        Args:
            tenant: Tenant object with updated fields

        Returns:
            Updated Tenant object
        """
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def delete(self, tenant: Tenant) -> None:
        """
        Delete a tenant.

        WARNING: This will cascade delete all accounts, transactions,
        and memberships associated with this tenant.

        Args:
            tenant: Tenant object to delete
        """
        self.db.delete(tenant)
        self.db.commit()