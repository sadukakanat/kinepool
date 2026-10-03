from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, UniqueConstraint
from database import Base
from datetime import datetime, timezone

class DBNodeRegistry(Base):
    __tablename__ = "node_registry"
    callsign = Column(String(10), primary_key=True)
    full_id = Column(String(20), unique=True, nullable=False)
    status = Column(String(20), default="ACTIVE")
    coordinates = Column(String(50))

class DBSubTickAllocation(Base):
    __tablename__ = "sub_tick_allocations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(String(10), nullable=False)
    tick_integer = Column(Integer, nullable=False)
    sub_counter = Column(Integer, nullable=False)
    
    __table_args__ = (UniqueConstraint('node_id', 'tick_integer', name='_node_tick_uc'),)

class DBMeasurement(Base):
    __tablename__ = "measurements"
    measurement_id = Column(String(64), primary_key=True)
    node_id = Column(String(10), nullable=False)
    category_code = Column(String(255), nullable=False)
    resource_type = Column(String(100))
    raw_metrics = Column(JSON)
    rve_signature = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DBSettlement(Base):
    __tablename__ = "settlements"
    composite_kuts_id = Column(String(100), primary_key=True)
    measurement_id = Column(String(64), nullable=False)
    raw_kines = Column(Float, nullable=False)
    total_valuation_usd = Column(Float, nullable=False)
    pfs_allocation = Column(Float, nullable=False)
    rsp_allocation = Column(Float, nullable=False)
    audit_trail = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))