from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """SQLite/SQLAlchemy's DateTime column drops tzinfo on read (values are
    always written as UTC by _utcnow(), but come back naive) — attach it
    back so datetime arithmetic against datetime.now(timezone.utc) doesn't
    raise TypeError. SQL-side comparisons (WHERE created_at >= ...) aren't
    affected: the bind-parameter conversion is consistent whichever side
    of a query the datetime is on.
    """
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="citizen")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ai_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="reported", index=True)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    report_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_duplicate_of: Mapped[int | None] = mapped_column(
        ForeignKey("reports.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow, nullable=False)

    embedding: Mapped["ReportEmbedding"] = relationship(
        back_populates="report", uselist=False, cascade="all, delete-orphan"
    )
    status_history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="StatusHistory.created_at"
    )


class ReportEmbedding(Base):
    __tablename__ = "report_embeddings"

    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), primary_key=True)
    vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)

    report: Mapped["Report"] = relationship(back_populates="embedding")


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)

    report: Mapped["Report"] = relationship(back_populates="status_history")
