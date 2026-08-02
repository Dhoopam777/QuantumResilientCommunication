"""
Create attachments table

Revision ID: 006
Revises: 005
Create Date: 2024-08-02

Security-hardened attachment storage:
- Files stored with UUIDv4 filenames, not client-supplied names
- SHA-256 checksum computed server-side
- EXIF stripped and images re-encoded
- Server-side MIME detection
- Thumbnail generation
- Soft delete flag
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create attachments table."""
    op.create_table(
        "attachments",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("message_id", sa.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("conversation_id", sa.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploader_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False, comment="UUIDv4-based filename on disk (never exposed to clients)"),
        sa.Column("original_filename", sa.String(255), nullable=False, comment="Sanitized original filename (metadata only)"),
        sa.Column("mime_type", sa.String(100), nullable=False, comment="Server-detected MIME type"),
        sa.Column("file_extension", sa.String(10), nullable=False, comment="Lowercase extension including dot"),
        sa.Column("file_size", sa.Integer(), nullable=False, comment="File size in bytes"),
        sa.Column("checksum_sha256", sa.String(64), nullable=False, comment="Server-computed SHA-256 hex digest"),
        sa.Column("width", sa.Integer(), nullable=True, comment="Image width in pixels"),
        sa.Column("height", sa.Integer(), nullable=True, comment="Image height in pixels"),
        sa.Column("thumbnail_filename", sa.String(255), nullable=True, comment="UUIDv4-based thumbnail filename"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false", comment="Soft delete flag"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for performance and security lookups
    op.create_index("ix_attachments_id", "attachments", ["id"])
    op.create_index("ix_attachments_message_id", "attachments", ["message_id"])
    op.create_index("ix_attachments_conversation_id", "attachments", ["conversation_id"])
    op.create_index("ix_attachments_uploader_id", "attachments", ["uploader_id"])
    op.create_index("ix_attachments_checksum", "attachments", ["checksum_sha256"])


def downgrade() -> None:
    """Drop attachments table."""
    op.drop_index("ix_attachments_checksum", table_name="attachments")
    op.drop_index("ix_attachments_uploader_id", table_name="attachments")
    op.drop_index("ix_attachments_conversation_id", table_name="attachments")
    op.drop_index("ix_attachments_message_id", table_name="attachments")
    op.drop_index("ix_attachments_id", table_name="attachments")
    op.drop_table("attachments")
