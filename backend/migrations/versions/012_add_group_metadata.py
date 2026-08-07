"""Add secure group metadata to conversations.

Revision ID: 012
Revises: 011
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("group_description", sa.String(1000), nullable=True))
    op.add_column("conversations", sa.Column("group_avatar_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "group_avatar_url")
    op.drop_column("conversations", "group_description")
