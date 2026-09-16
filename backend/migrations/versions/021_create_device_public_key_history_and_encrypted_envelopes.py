"""Create device_public_key_history and encrypted_envelopes tables.

Revision ID: 021
Revises: 020
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_public_key_history",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("device_id", sa.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kem_public_key", sa.Text(), nullable=False),
        sa.Column("signature_public_key", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.String(64), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_device_public_key_history_device_id", "device_public_key_history", ["device_id"])
    op.create_index("ix_dpk_history_device_valid_from", "device_public_key_history", ["device_id", "valid_from"])

    op.create_table(
        "encrypted_envelopes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("message_id", sa.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_device_id", sa.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("nonce", sa.String(64), nullable=False),
        sa.Column("authentication_tag", sa.String(64), nullable=False),
        sa.Column("encryption_version", sa.String(32), nullable=True),
        sa.Column("ciphertext_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("message_id", "recipient_device_id", name="uq_envelopes_message_recipient_device"),
    )
    op.create_index("ix_envelopes_recipient_device_id", "encrypted_envelopes", ["recipient_device_id"])
    op.create_index("ix_envelopes_message_id", "encrypted_envelopes", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_envelopes_message_id", table_name="encrypted_envelopes")
    op.drop_index("ix_envelopes_recipient_device_id", table_name="encrypted_envelopes")
    op.drop_table("encrypted_envelopes")
    op.drop_index("ix_dpk_history_device_valid_from", table_name="device_public_key_history")
    op.drop_index("ix_device_public_key_history_device_id", table_name="device_public_key_history")
    op.drop_table("device_public_key_history")
