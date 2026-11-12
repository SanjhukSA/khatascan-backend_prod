"""add uploads (pending images owned by a user)

Revision ID: c9e4f1a2d630
Revises: b7d2e5a9c418
Create Date: 2026-11-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e4f1a2d630"
down_revision: Union[str, None] = "b7d2e5a9c418"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Uploads that were pending before this migration have no row here: their owners
    # will get "not found, please re-upload" once, and the cleanup job deletes the files.
    op.create_table(
        "uploads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_uploads_user_id_users", ondelete="CASCADE"),
    )
    op.create_index("ix_uploads_user_id", "uploads", ["user_id"])
    op.create_index("ix_uploads_created_at", "uploads", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_uploads_created_at", table_name="uploads")
    op.drop_index("ix_uploads_user_id", table_name="uploads")
    op.drop_table("uploads")
