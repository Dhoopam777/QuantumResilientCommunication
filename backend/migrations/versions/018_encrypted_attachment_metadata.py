"""Add client-encrypted attachment metadata.

Revision ID: 018
Revises: 017
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("attachments", sa.Column("encryption_algorithm", sa.String(32), nullable=True))
    op.add_column("attachments", sa.Column("nonce", sa.String(64), nullable=True))
    op.add_column("attachments", sa.Column("authentication_tag", sa.String(64), nullable=True))
    op.add_column("attachments", sa.Column("encrypted_size", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("attachments", "encrypted_size")
    op.drop_column("attachments", "authentication_tag")
    op.drop_column("attachments", "nonce")
    op.drop_column("attachments", "encryption_algorithm")
