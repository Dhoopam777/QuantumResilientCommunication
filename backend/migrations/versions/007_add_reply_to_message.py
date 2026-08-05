"""
Add reply_to_message_id to messages table

Revision ID: 007
Revises: 006
Create Date: 2024-08-06

Adds a nullable FK column `reply_to_message_id` referencing messages.id
to support the message reply system. Preserves referential integrity and
allows soft-deleted parent messages to retain the reply relationship.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add reply_to_message_id FK column to messages."""
    op.add_column(
        "messages",
        sa.Column(
            "reply_to_message_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="RESTRICT"),
            nullable=True,
            comment="Parent message this message replies to (FK to messages.id)",
        ),
    )
    op.create_index(
        "ix_messages_reply_to_message_id",
        "messages",
        ["reply_to_message_id"],
    )


def downgrade() -> None:
    """Drop reply_to_message_id column from messages."""
    op.drop_index("ix_messages_reply_to_message_id", table_name="messages")
    op.drop_column("messages", "reply_to_message_id")