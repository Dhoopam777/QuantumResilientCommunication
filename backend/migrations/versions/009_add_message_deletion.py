"""
Add message deletion fields to messages table

Revision ID: 009
Revises: 008
Create Date: 2024-08-08

Adds `deleted_at`, `deleted_by`, and `delete_type` columns to the messages
table to support the secure message deletion system (Delete for Me /
Delete for Everyone).

Design:
- Soft delete only — database rows are NEVER removed.
- `deleted_at`: Timestamp when the message was deleted (NULL if not deleted).
- `deleted_by`: UUID of the user who initiated the deletion (NULL if not deleted).
- `delete_type`: 'me' (hidden only for requesting user) or 'everyone' (hidden for all).

Future-ready: message history, audit logs, PQC signatures, and multi-device
sync can reference these fields without requiring a schema redesign.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add message deletion fields to messages table.

    Note: ``deleted_at`` is intentionally NOT added here because migration
    004 already creates it on the ``messages`` table. Adding it again would
    fail with a DuplicateColumn error on a clean database.
    """
    op.add_column(
        "messages",
        sa.Column(
            "deleted_by",
            sa.UUID(as_uuid=True),
            nullable=True,
            comment="User who initiated the deletion (NULL if not deleted)",
        ),
    )
    op.add_column(
        "messages",
        sa.Column(
            "delete_type",
            sa.String(20),
            nullable=True,
            comment="Deletion mode: 'me' (hidden for requesting user) or 'everyone' (hidden for all)",
        ),
    )


def downgrade() -> None:
    """Drop message deletion fields from messages table.

    ``deleted_at`` is not dropped here because it was created by migration 004
    (which drops the entire messages table in its own downgrade).
    """
    op.drop_column("messages", "delete_type")
    op.drop_column("messages", "deleted_by")
