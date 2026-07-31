"""
Create messages table

Revision ID: 004
Revises: 003
Create Date: 2024-07-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create messages table."""
    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("conversation_id", sa.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sender_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("content_encrypted", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(255), nullable=False),
        sa.Column("message_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("reply_to", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("is_edited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index("ix_messages_id", "messages", ["id"])
    op.create_index("ix_messages_conversation", "messages", ["conversation_id", "created_at"])
    op.create_index("ix_messages_sender", "messages", ["sender_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])


def downgrade() -> None:
    """Drop messages table."""
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_sender", table_name="messages")
    op.drop_index("ix_messages_conversation", table_name="messages")
    op.drop_index("ix_messages_id", table_name="messages")
    op.drop_table("messages")