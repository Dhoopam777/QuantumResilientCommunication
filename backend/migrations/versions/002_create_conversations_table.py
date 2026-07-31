"""
Create conversations table

Revision ID: 002
Revises: 001
Create Date: 2024-07-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create conversations table."""
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("is_group", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("group_name", sa.String(255), nullable=True),
        sa.Column("created_by", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index("ix_conversations_id", "conversations", ["id"])
    op.create_index("ix_conversations_created_by", "conversations", ["created_by"])
    op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])


def downgrade() -> None:
    """Drop conversations table."""
    op.drop_index("ix_conversations_updated_at", table_name="conversations")
    op.drop_index("ix_conversations_created_by", table_name="conversations")
    op.drop_index("ix_conversations_id", table_name="conversations")
    op.drop_table("conversations")