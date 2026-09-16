"""Create devices table for multi-device support.

Revision ID: 019
Revises: 018
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_uuid", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("device_type", sa.String(20), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("kem_public_key", sa.Text(), nullable=True),
        sa.Column("signature_public_key", sa.Text(), nullable=True),
        sa.Column("algorithm_version", sa.String(64), nullable=True),
        sa.Column("key_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorized_by_device_id", sa.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("security_code_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'active', 'revoked', 'lost')", name="ck_devices_status"),
        sa.UniqueConstraint("device_uuid", name="uq_devices_device_uuid"),
    )
    op.create_index("ix_devices_user_id", "devices", ["user_id"])
    op.create_index("ix_devices_status", "devices", ["status"])
    op.create_index("ix_devices_last_seen_at", "devices", ["last_seen_at"])
    op.create_index("uq_devices_one_primary_per_user", "devices", ["user_id"], unique=True, postgresql_where=sa.text("is_primary = true"))


def downgrade() -> None:
    op.drop_index("uq_devices_one_primary_per_user", table_name="devices")
    op.drop_index("ix_devices_last_seen_at", table_name="devices")
    op.drop_index("ix_devices_status", table_name="devices")
    op.drop_index("ix_devices_user_id", table_name="devices")
    op.drop_table("devices")
