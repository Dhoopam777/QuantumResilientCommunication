"""
Add edited_at to messages table

Revision ID: 008
Revises: 007
Create Date: 2024-08-07

Adds a nullable `edited_at` timestamp column to the messages table to
support the secure message editing system. The `is_edited` boolean already
exists; `edited_at` records when the message was last edited.

Future-ready: edit history / message versions can reference `edited_at`
without requiring a schema redesign.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add edited_at timestamp column to messages."""
    op.add_column(
        "messages",
        sa.Column(
            "edited_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when the message was last edited (NULL if never edited)",
        ),
    )


def downgrade() -> None:
    """Drop edited_at column from messages."""
    op.drop_column("messages", "edited_at")