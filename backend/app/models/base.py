"""Base model with common fields and functionality"""
import uuid
from datetime import UTC, datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def generate_uuid() -> str:
    """Generate UUID string for primary key"""
    return str(uuid.uuid4())


class BaseModel(Base):
    """Abstract base model with common timestamp fields"""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        primary_key=True,
        default=generate_uuid,
        doc="UUID primary key"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
        doc="Creation timestamp in UTC"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        doc="Last update timestamp in UTC"
    )

    def __repr__(self) -> str:
        """String representation"""
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
