"""SQLAlchemy ORM models."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Source(Base):
    """Data source registry (FRED, BLS, Treasury, etc.)."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    rate_limit_per_min: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    series: Mapped[list["Series"]] = relationship(back_populates="source")
    fetch_jobs: Mapped[list["FetchJob"]] = relationship(back_populates="source")


class Series(Base):
    """Time series metadata."""

    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    frequency: Mapped[str | None] = mapped_column(String(20))
    units: Mapped[str | None] = mapped_column(String(100))
    seasonal_adjustment: Mapped[str | None] = mapped_column(String(20))
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    source: Mapped["Source"] = relationship(back_populates="series")
    observations: Mapped[list["Observation"]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_series_source_external", "source_id", "external_id", unique=True),)


class Observation(Base):
    """Time series data points."""

    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric)
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision_num: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    series: Mapped["Series"] = relationship(back_populates="observations")

    __table_args__ = (
        Index("idx_observations_series_date", "series_id", "date"),
        Index("idx_observations_release", "release_date"),
        Index(
            "idx_observations_unique",
            "series_id",
            "date",
            "revision_num",
            unique=True,
        ),
    )


class FetchJob(Base):
    """Scheduled data fetch jobs."""

    __tablename__ = "fetch_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    series_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    schedule: Mapped[str | None] = mapped_column(String(50))
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(20))
    next_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    source: Mapped["Source"] = relationship(back_populates="fetch_jobs")
    logs: Mapped[list["FetchLog"]] = relationship(back_populates="job")


class FetchLog(Base):
    """Audit log for fetch operations."""

    __tablename__ = "fetch_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("fetch_jobs.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str | None] = mapped_column(String(20))
    records_fetched: Mapped[int | None] = mapped_column(Integer)
    records_inserted: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Relationships
    job: Mapped["FetchJob"] = relationship(back_populates="logs")


class EconomicEvent(Base):
    """External economic events table (populated by extraction agent)."""

    __tablename__ = "economic_events"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # UUID as text
    run_id: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_agent_id: Mapped[str] = mapped_column(Text, nullable=False)
    calendar_date: Mapped[str | None] = mapped_column(Text)
    time_ny: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(Text, nullable=False)
    event_name: Mapped[str] = mapped_column(Text, nullable=False)
    period: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str | None] = mapped_column(Text)
    consensus: Mapped[str | None] = mapped_column(Text)
    last_value: Mapped[str | None] = mapped_column(Text)
    actual_result: Mapped[str | None] = mapped_column(Text)
    result_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_date: Mapped[date | None] = mapped_column(Date)
    importance_indicator: Mapped[str | None] = mapped_column(Text)
    day_date: Mapped[str | None] = mapped_column(Text)
