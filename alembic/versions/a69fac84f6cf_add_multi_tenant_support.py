"""add_multi_tenant_support

Revision ID: a69fac84f6cf
Revises: c61541b90ee5
Create Date: 2026-01-04 16:14:06.327965

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a69fac84f6cf'
down_revision: Union[str, Sequence[str], None] = 'c61541b90ee5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema to multi-tenant architecture.

    Creates:
    - tenants table
    - tenant_memberships table
    - tenant_id column in accounts table

    Data Migration:
    - Creates single "Shared Tenant" with tenant_id=1
    - Adds all existing users as members (first user becomes OWNER)
    - Assigns all accounts to the shared tenant
    """
    # 1. Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Create tenant_memberships table
    op.create_table(
        'tenant_memberships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_user')
    )

    # 3. Add tenant_id to accounts (nullable initially for data migration)
    op.add_column('accounts', sa.Column('tenant_id', sa.Integer(), nullable=True))

    # 4. DATA MIGRATION - Create single shared tenant
    connection = op.get_bind()

    # Create "Shared Tenant" for all users
    result = connection.execute(
        sa.text("""
            INSERT INTO tenants (name, created_at, updated_at)
            VALUES ('Shared Tenant', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        """)
    )
    shared_tenant_id = result.fetchone()[0]

    # Get all existing users (ordered by ID to make first user the OWNER)
    users = connection.execute(sa.text("SELECT id FROM users ORDER BY id")).fetchall()

    # Add all users as members of shared tenant
    # First user becomes OWNER, rest become MEMBER
    for idx, (user_id,) in enumerate(users):
        role = 'owner' if idx == 0 else 'member'
        connection.execute(
            sa.text("""
                INSERT INTO tenant_memberships
                (tenant_id, user_id, role, created_at, updated_at)
                VALUES (:tenant_id, :user_id, :role, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {"tenant_id": shared_tenant_id, "user_id": user_id, "role": role}
        )

    # Update all accounts to belong to shared tenant
    connection.execute(
        sa.text("""
            UPDATE accounts SET tenant_id = :tenant_id
        """),
        {"tenant_id": shared_tenant_id}
    )

    # 5. Make tenant_id NOT NULL now that data is migrated
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', nullable=False)
        batch_op.create_foreign_key('fk_accounts_tenant_id', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    # 6. Add indexes for performance
    op.create_index('ix_accounts_tenant_id', 'accounts', ['tenant_id'])
    op.create_index('ix_tenant_memberships_tenant_id', 'tenant_memberships', ['tenant_id'])
    op.create_index('ix_tenant_memberships_user_id', 'tenant_memberships', ['user_id'])


def downgrade() -> None:
    """
    Rollback multi-tenant architecture changes.

    WARNING: This will delete all tenant and membership data.
    Accounts will revert to being owned by individual users.
    """
    # 1. Drop indexes
    op.drop_index('ix_tenant_memberships_user_id', table_name='tenant_memberships')
    op.drop_index('ix_tenant_memberships_tenant_id', table_name='tenant_memberships')
    op.drop_index('ix_accounts_tenant_id', table_name='accounts')

    # 2. Drop foreign key and tenant_id column from accounts
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_accounts_tenant_id', type_='foreignkey')
        batch_op.drop_column('tenant_id')

    # 3. Drop tenant_memberships table
    op.drop_table('tenant_memberships')

    # 4. Drop tenants table
    op.drop_table('tenants')
