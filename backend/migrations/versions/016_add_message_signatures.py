"""Add ML-DSA message authentication fields.

Revision ID: 016
Revises: 015
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("signature", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("signature_algorithm", sa.String(64), nullable=True))
    op.add_column("messages", sa.Column("signature_created_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "signature_created_at")
    op.drop_column("messages", "signature_algorithm")
    op.drop_column("messages", "signature")
