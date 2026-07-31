"""
Add user profile fields

Revision ID: 005
Revises: 004
Create Date: 2024-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add profile fields to the users table."""
    op.add_column("users", sa.Column("display_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("status_message", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("is_online", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    """Remove profile fields from the users table."""
    op.drop_column("users", "is_online")
    op.drop_column("users", "last_seen")
    op.drop_column("users", "status_message")
    op.drop_column("users", "bio")
    op.drop_column("users", "display_name")