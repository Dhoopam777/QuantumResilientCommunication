"""Add encrypted post-quantum identity keys.

Revision ID: 014
Revises: 013
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pq_signature_public_key", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("pq_signature_private_key_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("pq_kem_public_key", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("pq_kem_private_key_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("pq_algorithm_version", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("pq_key_created_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "pq_key_created_at")
    op.drop_column("users", "pq_algorithm_version")
    op.drop_column("users", "pq_kem_private_key_encrypted")
    op.drop_column("users", "pq_kem_public_key")
    op.drop_column("users", "pq_signature_private_key_encrypted")
    op.drop_column("users", "pq_signature_public_key")
