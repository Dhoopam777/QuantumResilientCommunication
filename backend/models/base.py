"""
Base Models and Mixins for Quantum-Resilient Communication System

This module provides reusable base classes for SQLAlchemy models.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """
    Mixin for models that require timestamp tracking.
    
    Provides:
    - created_at: Timestamp when record was created
    - updated_at: Timestamp when record was last updated
    - deleted_at: Timestamp when record was soft-deleted (NULL if not deleted)
    """
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )