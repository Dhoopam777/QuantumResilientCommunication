"""Store AES-GCM message envelope fields for client-side encryption.

Revision ID: 017
Revises: 016
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("encryption_version", sa.String(32), nullable=True))
    op.add_column("messages", sa.Column("nonce", sa.String(64), nullable=True))
    op.add_column("messages", sa.Column("authentication_tag", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "authentication_tag")
    op.drop_column("messages", "nonce")
    op.drop_column("messages", "encryption_version")
