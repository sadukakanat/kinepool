from datetime import datetime, timezone

from sqlalchemy import (String, Integer, BigInteger, JSON, DateTime,
                        UniqueConstraint, ForeignKey)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def _now():
    return datetime.now(timezone.utc)


class DBNodeRegistry(Base):
    """Anchor nodes (e.g. THR / THRINC000)."""
    __tablename__ = "node_registry"
    callsign: Mapped[str] = mapped_column(String(10), primary_key=True)
    full_id: Mapped[str] = mapped_column(String(20), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    coordinates: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class DBTerminal(Base):
    """A registered user terminal. Only a SHA-256 of its bearer token is stored."""
    __tablename__ = "terminals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    grl_uid: Mapped[str] = mapped_column(String(32), unique=True)
    kuts_serial: Mapped[str] = mapped_column(String(64), unique=True)
    device_profile: Mapped[str] = mapped_column(String(100))
    anchor_callsign: Mapped[str] = mapped_column(ForeignKey("node_registry.callsign"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class DBSubTickAllocation(Base):
    """One row per (node, tick) holding the highest sub-tick (00-99) handed out."""
    __tablename__ = "sub_tick_allocations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(10))
    tick_integer: Mapped[int] = mapped_column(BigInteger)   # ~1.1e18 > 32-bit
    sub_counter: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("node_id", "tick_integer", name="_node_tick_uc"),)


class DBMeasurement(Base):
    __tablename__ = "measurements"
    measurement_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    terminal_id: Mapped[int] = mapped_column(ForeignKey("terminals.id"))
    node_id: Mapped[str] = mapped_column(String(10))
    category_code: Mapped[str] = mapped_column(String(2))
    resource_type: Mapped[str] = mapped_column(String(200))
    raw_metrics: Mapped[dict] = mapped_column(JSON)
    metering_source: Mapped[str] = mapped_column(String(50))
    rve_signature: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    source_reading_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("terminal_id", "idempotency_key", name="_terminal_idem_uc"),)


class DBSettlement(Base):
    """Append-only, hash-chained. Amounts are integers in e8 units (1 K = 1e8)."""
    __tablename__ = "settlements"
    composite_kuts_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    seq: Mapped[int] = mapped_column(BigInteger, unique=True)
    measurement_id: Mapped[str] = mapped_column(ForeignKey("measurements.measurement_id"), unique=True)
    rve_signature: Mapped[str] = mapped_column(String(64))
    raw_kines_e8: Mapped[int] = mapped_column(BigInteger)
    valuation_usd_e8: Mapped[int] = mapped_column(BigInteger)
    pfs_e8: Mapped[int] = mapped_column(BigInteger)
    rsp_e8: Mapped[int] = mapped_column(BigInteger)
    net_e8: Mapped[int] = mapped_column(BigInteger)
    audit_trail: Mapped[list] = mapped_column(JSON)
    prev_hash: Mapped[str] = mapped_column(String(64))
    entry_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)