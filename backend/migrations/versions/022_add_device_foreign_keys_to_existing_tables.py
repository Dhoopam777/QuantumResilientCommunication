"""Add device foreign keys to existing tables (session_keys, messages, attachments).

Revision ID: 022
Revises: 021
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("session_keys", sa.Column("initiator_device_id", sa.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True))
    op.add_column("session_keys", sa.Column("recipient_device_id", sa.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_session_keys_initiator_device_id", "session_keys", ["initiator_device_id"])
    op.create_index("ix_session_keys_recipient_device_id", "session_keys", ["recipient_device_id"])

    op.add_column("messages", sa.Column("sender_device_id", sa.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True))
    op.add_column("messages", sa.Column("sender_device_uuid", sa.String(36), nullable=True))
    op.add_column("messages", sa.Column("sender_device_signature_public_key_snapshot", sa.Text(), nullable=True))
    op.create_index("ix_messages_sender_device_id", "messages", ["sender_device_id"])

    op.add_column("attachments", sa.Column("sender_device_id", sa.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_attachments_sender_device_id", "attachments", ["sender_device_id"])


def downgrade() -> None:
    op.drop_index("ix_attachments_sender_device_id", table_name="attachments")
    op.drop_column("attachments", "sender_device_id")
    op.drop_index("ix_messages_sender_device_id", table_name="messages")
    op.drop_column("messages", "sender_device_signature_public_key_snapshot")
    op.drop_column("messages", "sender_device_uuid")
    op.drop_column("messages", "sender_device_id")
    op.drop_index("ix_session_keys_recipient_device_id", table_name="session_keys")
    op.drop_index("ix_session_keys_initiator_device_id", table_name="session_keys")
    op.drop_column("session_keys", "recipient_device_id")
    op.drop_column("session_keys", "initiator_device_id")
