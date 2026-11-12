"""add users and receipt owner

Revision ID: b7d2e5a9c418
Revises: a3f1c9d27b54
Create Date: 2026-11-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7d2e5a9c418"
down_revision: Union[str, None] = "a3f1c9d27b54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # Existing receipts keep user_id NULL: nobody can see them until you assign an owner.
    op.add_column("receipts", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_receipts_user_id_users", "receipts", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_receipts_user_id", "receipts", ["user_id"])

    # "Same invoice" is now per user (two accounts may each keep the same bill).
    op.drop_constraint("uq_receipt_vendor_invoice", "receipts", type_="unique")
    op.create_unique_constraint(
        "uq_receipt_vendor_invoice", "receipts", ["user_id", "vendor_gstin", "invoice_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_receipt_vendor_invoice", "receipts", type_="unique")
    op.create_unique_constraint(
        "uq_receipt_vendor_invoice", "receipts", ["vendor_gstin", "invoice_number"]
    )
    op.drop_index("ix_receipts_user_id", table_name="receipts")
    op.drop_constraint("fk_receipts_user_id_users", "receipts", type_="foreignkey")
    op.drop_column("receipts", "user_id")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
