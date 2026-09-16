"""
SecurityCode model for account-level identity verification.

One row per user. Stores a hash of the account-level security code (not the
code itself). The code is verified by any device on the account; each device
tracks its own last-verified timestamp on the Device record.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class SecurityCode(Base):
    __tablename__ = "security_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        comment="Unique identifier for this security code record",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False,
        comment="Owning user account (one security code per user)",
    )
    code_hash: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Hash of the account-level security code (never raw code)",
    )
    kdf_params: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="KDF parameters used to hash the code (e.g. algorithm, rounds, salt)",
    )
    code_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When the security code was last changed",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()",
        comment="When this security code record was created",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="security_code")

    def __repr__(self) -> str:
        return (
            f"<SecurityCode(id={self.id}, user_id={self.user_id}, "
            f"code_changed_at={self.code_changed_at})>"
        )