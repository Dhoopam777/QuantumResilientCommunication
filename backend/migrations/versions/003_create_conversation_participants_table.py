"""
Create conversation_participants table

Revision ID: 003
Revises: 002
Create Date: 2024-07-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create conversation_participants table."""
    op.create_table(
        "conversation_participants",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("conversation_id", sa.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_read_message_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_muted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index("ix_conversation_participants_id", "conversation_participants", ["id"])
    op.create_index("ix_participants_conversation", "conversation_participants", ["conversation_id"])
    op.create_index("ix_participants_user", "conversation_participants", ["user_id"])
    op.create_index(
        "ix_participants_active",
        "conversation_participants",
        ["user_id", "left_at"],
        postgresql_where=sa.text("left_at IS NULL"),
    )
    op.create_index(
        "uq_participants_active_membership",
        "conversation_participants",
        ["conversation_id", "user_id", "left_at"],
        unique=True,
        postgresql_where=sa.text("left_at IS NULL"),
    )


def downgrade() -> None:
    """Drop conversation_participants table."""
    op.drop_index("uq_participants_active_membership", table_name="conversation_participants")
    op.drop_index("ix_participants_active", table_name="conversation_participants")
    op.drop_index("ix_participants_user", table_name="conversation_participants")
    op.drop_index("ix_participants_conversation", table_name="conversation_participants")
    op.drop_index("ix_conversation_participants_id", table_name="conversation_participants")
    op.drop_table("conversation_participants")