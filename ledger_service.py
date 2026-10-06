"""
Mint pipeline: RVE attestation -> valuation -> unique ID -> hash-chained record.

The whole "read last entry -> append next entry -> commit" step runs under a
process-wide asyncio lock (and a PostgreSQL advisory lock for multi-process
safety) so the hash chain can never fork.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

import integrity
from chronometric_engine import ChronometricEngine
from models import DBMeasurement, DBSettlement, DBSubTickAllocation
from uniqueness_engine import SUB_TICK_MAX
from valuation_engine import ValuationEngine, fmt_e8

_chain_lock = asyncio.Lock()
_ADVISORY_KEY = 7_340_001

chrono = ChronometricEngine()
valuation = ValuationEngine()


class SubTickExhausted(Exception):
    """All 100 sub-ticks of this 334 ns tick are used; caller should retry."""


async def allocate_sub_tick(db, node_id: str, tick: int) -> int:
    """Atomically allocate sub-tick 00-99 for (node, tick). Persisted in the DB."""
    q = (select(DBSubTickAllocation)
         .where(DBSubTickAllocation.node_id == node_id,
                DBSubTickAllocation.tick_integer == tick)
         .with_for_update())
    row = (await db.execute(q)).scalar_one_or_none()
    if row is None:
        try:
            async with db.begin_nested():
                db.add(DBSubTickAllocation(node_id=node_id, tick_integer=tick, sub_counter=0))
                await db.flush()
            return 0
        except IntegrityError:           # another process inserted first
            row = (await db.execute(q)).scalar_one()
    if row.sub_counter >= SUB_TICK_MAX:
        raise SubTickExhausted()
    row.sub_counter += 1
    await db.flush()
    return row.sub_counter


def settlement_to_dict(s: DBSettlement) -> dict:
    return {
        "composite_kuts_id": s.composite_kuts_id,
        "seq": s.seq,
        "measurement_id": s.measurement_id,
        "raw_kines": fmt_e8(s.raw_kines_e8),
        "total_valuation_usd": fmt_e8(s.valuation_usd_e8),
        "pfs_allocation": fmt_e8(s.pfs_e8),
        "rsp_allocation": fmt_e8(s.rsp_e8),
        "net_recipient_credit": fmt_e8(s.net_e8),
        "audit_trail": s.audit_trail,
        "entry_hash": s.entry_hash,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


async def _existing_for_key(db, terminal_id: int, idem_key: str):
    q = (select(DBSettlement)
         .join(DBMeasurement, DBMeasurement.measurement_id == DBSettlement.measurement_id)
         .where(DBMeasurement.terminal_id == terminal_id,
                DBMeasurement.idempotency_key == idem_key))
    return (await db.execute(q)).scalar_one_or_none()


async def mint_settlement(db, terminal, req: dict, rve) -> dict:
    """
    req keys: title, category (1..16), energy_kwh (Decimal), compute_mtok (Decimal),
              idempotency_key, source_reading_id (optional)
    """
    energy: Decimal = req["energy_kwh"]
    compute: Decimal = req["compute_mtok"]
    category: int = req["category"]
    sv = valuation.settle(energy, compute)          # raises ValueError on zero Kines

    async with _chain_lock:
        # Idempotent replay: same terminal + same key returns the original record.
        prior = await _existing_for_key(db, terminal.id, req["idempotency_key"])
        if prior:
            return {**settlement_to_dict(prior), "replayed": True,
                    "terminal_serial": terminal.kuts_serial}

        if db.bind.dialect.name == "postgresql":
            await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _ADVISORY_KEY})

        node = terminal.anchor_callsign
        tick = chrono.compute_ticks(datetime.now(timezone.utc))
        sub_tick = await allocate_sub_tick(db, node, tick)
        composite_id = chrono.compose_identifier(category, tick, node, sub_tick)

        packet = rve.attest_telemetry(
            node_id=node,
            terminal_uid=terminal.grl_uid,
            category_code=category,
            resource_type=req["title"],
            raw_metrics={"energy_kwh": str(energy), "compute_mtok": str(compute)},
        )

        last = (await db.execute(
            select(DBSettlement).order_by(DBSettlement.seq.desc()).limit(1))).scalar_one_or_none()
        seq = (last.seq + 1) if last else 1
        prev_hash = last.entry_hash if last else integrity.GENESIS_HASH

        fields = {
            "seq": seq, "composite_kuts_id": composite_id,
            "measurement_id": packet["measurement_id"], "rve_signature": packet["rve_signature"],
            "raw_kines_e8": sv["raw_kines_e8"], "valuation_usd_e8": sv["valuation_usd_e8"],
            "pfs_e8": sv["pfs_e8"], "rsp_e8": sv["rsp_e8"], "net_e8": sv["net_e8"],
        }
        e_hash = integrity.entry_hash(prev_hash, fields)

        audit = [
            "RECEIVED",
            f"ATTESTED (RVE HMAC signature issued; source={packet['metering_source']}, "
            f"trust={packet['trust_level']})",
            "VALUED (floor rate applied)",
            "ALLOCATED (PFS + RSP computed)",
            f"RECORDED (ledger seq {seq}, hash-chained)",
        ]

        db.add(DBMeasurement(
            measurement_id=packet["measurement_id"], terminal_id=terminal.id, node_id=node,
            category_code=packet["category_code"], resource_type=req["title"],
            raw_metrics=packet["raw_metrics"], metering_source=packet["metering_source"],
            rve_signature=packet["rve_signature"], idempotency_key=req["idempotency_key"],
            source_reading_id=req.get("source_reading_id"),
        ))
        await db.flush()   # measurement row must exist before the settlement FK
        settlement = DBSettlement(
            audit_trail=audit,
            prev_hash=prev_hash,
            entry_hash=e_hash,
            **fields
        )
        db.add(settlement)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            prior = await _existing_for_key(db, terminal.id, req["idempotency_key"])
            if prior:     # lost a cross-process race on the same idempotency key
                return {**settlement_to_dict(prior), "replayed": True,
                        "terminal_serial": terminal.kuts_serial}
            raise ValueError("Duplicate source_reading_id: this reading was already recorded.")

        return {**settlement_to_dict(settlement), "replayed": False,
                "terminal_serial": terminal.kuts_serial,
                "metering_source": packet["metering_source"],
                "trust_level": packet["trust_level"],
                "flux_units": sv["flux_units"], "dyne_units": sv["dyne_units"]}


async def verify_ledger(db, limit: int = 100_000) -> dict:
    rows = (await db.execute(
        select(DBSettlement).order_by(DBSettlement.seq.asc()).limit(limit))).scalars().all()
    entries = [{
        "seq": r.seq, "composite_kuts_id": r.composite_kuts_id,
        "measurement_id": r.measurement_id, "rve_signature": r.rve_signature,
        "raw_kines_e8": r.raw_kines_e8, "valuation_usd_e8": r.valuation_usd_e8,
        "pfs_e8": r.pfs_e8, "rsp_e8": r.rsp_e8, "net_e8": r.net_e8,
        "prev_hash": r.prev_hash, "entry_hash": r.entry_hash,
    } for r in rows]
    return integrity.verify_chain(entries)
    
