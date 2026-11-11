"""add receipt page content hash

Revision ID: a3f1c9d27b54
Revises: 6bae1dbe7e7b
Create Date: 2026-11-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3f1c9d27b54"
down_revision: Union[str, None] = "6bae1dbe7e7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("receipt_pages", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_receipt_pages_content_hash", "receipt_pages", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_receipt_pages_content_hash", table_name="receipt_pages")
    op.drop_column("receipt_pages", "content_hash")
