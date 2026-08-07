"""Create secure conversation requests table.

Revision ID: 011
Revises: 010
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_requests",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("receiver_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sender_id", "receiver_id", name="uq_conversation_request_pair"),
    )
    op.create_index("ix_conversation_requests_sender_id", "conversation_requests", ["sender_id"])
    op.create_index("ix_conversation_requests_receiver_id", "conversation_requests", ["receiver_id"])
    op.create_index("ix_conversation_requests_status", "conversation_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_conversation_requests_status", table_name="conversation_requests")
    op.drop_index("ix_conversation_requests_receiver_id", table_name="conversation_requests")
    op.drop_index("ix_conversation_requests_sender_id", table_name="conversation_requests")
    op.drop_table("conversation_requests")
