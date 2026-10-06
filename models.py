from sqlalchemy import BigInteger, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class DBSubTickAllocation(Base):
    """Ensures unique sub-tick indexing (00-99) per node and integer tick."""

    __tablename__ = "sub_tick_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(10), index=True)
    tick_integer: Mapped[int] = mapped_column(BigInteger, index=True)
    sub_counter: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("node_id", "tick_integer", name="_node_tick_uc"),
    )


class DBMeasurement(Base):
    """Stores temporal measurement and sync telemetry data."""

    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(10), index=True)
    timestamp: Mapped[int] = mapped_column(BigInteger, index=True)
    metric_name: Mapped[str] = mapped_column(String(50))
    metric_value: Mapped[float] = mapped_column(Float)


class DBSettlement(Base):
    """Tracks protocol settlement records and token distributions."""

    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    settlement_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_node: Mapped[str] = mapped_column(String(10))
    target_node: Mapped[str] = mapped_column(String(10))
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[int] = mapped_column(BigInteger)
