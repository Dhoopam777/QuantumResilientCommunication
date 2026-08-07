"""Add ML-KEM secure session metadata.

Revision ID: 015
Revises: 014
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_keys",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "conversation_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "initiator_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "recipient_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kem_ciphertext", sa.Text(), nullable=False),
        sa.Column("session_key_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("algorithm", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("session_key_id", name="uq_session_keys_session_key_id"),
    )
    op.create_index("ix_session_keys_conversation_id", "session_keys", ["conversation_id"])
    op.create_index("ix_session_keys_initiator_id", "session_keys", ["initiator_id"])
    op.create_index("ix_session_keys_recipient_id", "session_keys", ["recipient_id"])
    op.create_index("ix_session_keys_expires_at", "session_keys", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_session_keys_expires_at", table_name="session_keys")
    op.drop_index("ix_session_keys_recipient_id", table_name="session_keys")
    op.drop_index("ix_session_keys_initiator_id", table_name="session_keys")
    op.drop_index("ix_session_keys_conversation_id", table_name="session_keys")
    op.drop_table("session_keys")
