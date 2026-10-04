"""
Kinepool // Global Resource Ledger - KUTS Rev 8 prototype backend (flat layout).

Run locally (dev, SQLite):  KINEPOOL_DEV_SQLITE=1 uvicorn main:app --reload
Production (Render):        set DATABASE_URL, RVE_SIGNING_KEY, ADMIN_API_KEY
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, or_, text

import ledger_service
from database import Base, engine, get_db, IS_SQLITE, SessionLocal
from models import DBNodeRegistry, DBSettlement, DBTerminal
from rve_engine import ResourceVerificationEngine, load_signing_key
from uniqueness_engine import NodeIDRegistry
from valuation_engine import ValuationEngine

logger = logging.getLogger("kinepool")
BASE_DIR = Path(__file__).resolve().parent
PAGES = {"index.html", "register.html", "asset-register.html", "explorer.html"}

MASTER_CALLSIGN, MASTER_FULL_ID = "THR", "THRINC000"
MASTER_COORDS = "10.493210Â° N, 76.213464Â° E"

APPEND_ONLY_DDL = [
    """CREATE OR REPLACE FUNCTION kinepool_reject_mutation() RETURNS trigger AS $$
       BEGIN RAISE EXCEPTION 'Kinepool ledger tables are append-only'; END;
       $$ LANGUAGE plpgsql""",
    "DROP TRIGGER IF EXISTS settlements_append_only ON settlements",
    """CREATE TRIGGER settlements_append_only BEFORE UPDATE OR DELETE ON settlements
       FOR EACH ROW EXECUTE FUNCTION kinepool_reject_mutation()""",
    "DROP TRIGGER IF EXISTS measurements_append_only ON measurements",
    """CREATE TRIGGER measurements_append_only BEFORE UPDATE OR DELETE ON measurements
       FOR EACH ROW EXECUTE FUNCTION kinepool_reject_mutation()""",
]


# --------------------------------------------------------------------------- lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "postgresql":
            for stmt in APPEND_ONLY_DDL:
                await conn.execute(text(stmt))
    async with SessionLocal() as db:       # seed the master origin node
        exists = (await db.execute(
            select(DBNodeRegistry).where(DBNodeRegistry.callsign == MASTER_CALLSIGN))).scalar_one_or_none()
        if not exists:
            db.add(DBNodeRegistry(callsign=MASTER_CALLSIGN, full_id=MASTER_FULL_ID,
                                  status="ACTIVE", coordinates=MASTER_COORDS))
            await db.commit()
    app.state.rve = ResourceVerificationEngine(load_signing_key())
    yield
    await engine.dispose()


app = FastAPI(
    title="Kinepool", lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENABLE_DOCS") == "1" else None,
    redoc_url=None, openapi_url="/openapi.json" if os.getenv("ENABLE_DOCS") == "1" else None,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


# --------------------------------------------------------------------------- helpers
class RateLimiter:
    """Simple per-IP sliding window (per process). Use Redis if you scale out."""
    def __init__(self, limit: int, window_s: int):
        self.limit, self.window = limit, window_s
        self.hits: dict = defaultdict(deque)

    async def __call__(self, request: Request):
        ip = request.client.host if request.client else "unknown"
        key, now = f"{ip}:{request.url.path}", time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            raise HTTPException(429, "Too many requests. Slow down.",
                                headers={"Retry-After": str(self.window)})
        q.append(now)
        if len(self.hits) > 20_000:                       # crude memory bound
            for k in [k for k, v in self.hits.items() if not v or now - v[-1] > self.window]:
                self.hits.pop(k, None)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def current_terminal(authorization: Optional[str] = Header(default=None),
                           db=Depends(get_db)) -> DBTerminal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Register a terminal first (missing bearer token).")
    token_hash = _hash_token(authorization[7:].strip())
    terminal = (await db.execute(
        select(DBTerminal).where(DBTerminal.token_hash == token_hash,
                                 DBTerminal.status == "ACTIVE"))).scalar_one_or_none()
    if not terminal:
        raise HTTPException(401, "Unknown or inactive terminal token.")
    return terminal


# --------------------------------------------------------------------------- schemas
class TerminalRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_profile: str = Field(default="Unknown", max_length=100)


class MintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    category: int = Field(ge=1, le=16)
    energy_kwh: Decimal = Field(ge=0, le=Decimal("1000000000"), decimal_places=6)
    compute_mtok: Decimal = Field(ge=0, le=Decimal("1000000000"), decimal_places=6)
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    source_reading_id: Optional[str] = Field(default=None, max_length=128)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be blank")
        return v


class NodeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str          # callsign, e.g. "THR"
    full_id: str          # e.g. "THRINC000"
    coordinates: Optional[str] = Field(default=None, max_length=50)


# --------------------------------------------------------------------------- API
router = APIRouter()


@router.get("/api/health")
async def health(request: Request, db=Depends(get_db)):
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("health: database check failed")
        db_ok = False
    engines = {
        "chronometric": True,
        "uniqueness": db_ok,
        "rve": getattr(request.app.state, "rve", None) is not None,
        "valuation": True,
    }
    return {
        "status": "operational" if (db_ok and all(engines.values())) else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "kine_floor_rate_usd": float(ValuationEngine.KINE_FLOOR_RATE_USD),
        "engines": engines,
        "dev_sqlite": IS_SQLITE,
    }


@router.post("/api/v8/register", dependencies=[Depends(RateLimiter(20, 3600))])
async def register_terminal(req: TerminalRegisterRequest, db=Depends(get_db)):
    """Anonymous terminal registration. IDs and token are generated SERVER-side."""
    token = secrets.token_urlsafe(32)
    terminal = DBTerminal(
        grl_uid="GRL-UID-" + secrets.token_hex(4).upper(),
        kuts_serial=f"KUTS-SEC-{secrets.token_hex(6).upper()}-{MASTER_FULL_ID}",
        device_profile=req.device_profile.strip() or "Unknown",
        anchor_callsign=MASTER_CALLSIGN,
        token_hash=_hash_token(token),
        status="ACTIVE",
    )
    db.add(terminal)
    await db.commit()
    return {
        "status": "TERMINAL_REGISTERED",
        "grl_uid": terminal.grl_uid,
        "kuts_serial": terminal.kuts_serial,
        "anchor": MASTER_FULL_ID,
        "token": token,       # shown ONCE; only its hash is stored
    }


@router.post("/api/v8/mint", dependencies=[Depends(RateLimiter(30, 60))])
async def mint(req: MintRequest, request: Request,
               terminal: DBTerminal = Depends(current_terminal), db=Depends(get_db)):
    try:
        return await ledger_service.mint_settlement(db, terminal, req.model_dump(), request.app.state.rve)
    except ledger_service.SubTickExhausted:
        raise HTTPException(503, "Sub-tick slots exhausted for this tick; retry.", headers={"Retry-After": "1"})
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.get("/api/v8/ledger/search", dependencies=[Depends(RateLimiter(60, 60))])
async def search_ledger(query: Optional[str] = None, db=Depends(get_db)):
    stmt = select(DBSettlement)
    if query:
        query = query.strip()[:100]
        esc = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(or_(
            DBSettlement.composite_kuts_id.ilike(f"%{esc}%", escape="\\"),
            DBSettlement.measurement_id.ilike(f"%{esc}%", escape="\\")))
        stmt = stmt.order_by(DBSettlement.seq.desc()).limit(50)
    else:
        stmt = stmt.order_by(DBSettlement.seq.desc()).limit(20)
    rows = (await db.execute(stmt)).scalars().all()
    return [ledger_service.settlement_to_dict(s) for s in rows]


@router.get("/api/v8/ledger/verify", dependencies=[Depends(RateLimiter(6, 60))])
async def verify_ledger(db=Depends(get_db)):
    """Recompute the whole hash chain; reports the first altered/missing entry."""
    return await ledger_service.verify_ledger(db)


@router.post("/api/v8/nodes/register", dependencies=[Depends(RateLimiter(10, 60))])
async def register_node(req: NodeCreateRequest, x_admin_key: Optional[str] = Header(default=None),
                        db=Depends(get_db)):
    """Anchor-node registration. Admin only (X-Admin-Key == ADMIN_API_KEY)."""
    admin_key = os.getenv("ADMIN_API_KEY")
    if not admin_key:
        raise HTTPException(503, "Node registration is disabled (ADMIN_API_KEY not set).")
    if not x_admin_key or not hmac.compare_digest(x_admin_key, admin_key):
        raise HTTPException(403, "Forbidden.")
    if not NodeIDRegistry.consistent(req.node_id, req.full_id):
        raise HTTPException(422, "Invalid callsign/full_id format.")
    exists = (await db.execute(select(DBNodeRegistry).where(
        or_(DBNodeRegistry.callsign == req.node_id, DBNodeRegistry.full_id == req.full_id)))).scalar_one_or_none()
    if exists:
        raise HTTPException(409, f"Node '{req.node_id}' / '{req.full_id}' is already registered.")
    db.add(DBNodeRegistry(callsign=req.node_id, full_id=req.full_id, status="ACTIVE",
                          coordinates=req.coordinates))
    await db.commit()
    return {"status": "NODE_COMMISSIONED", "node_id": req.node_id, "full_id": req.full_id}


app.include_router(router)


# --------------------------------------------------------------------------- static pages (flat layout)
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(BASE_DIR / "index.html", media_type="text/html")


@app.get("/{page}", include_in_schema=False)
async def page(page: str):
    if page not in PAGES:          # whitelist: never expose .py files, Dockerfile, etc.
        raise HTTPException(404, "Not found")
    return FileResponse(BASE_DIR / page, media_type="text/html")
import os
import uvicorn

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 10000))
  uvicorn.run("main:app", host="0.0.0.0", port=port)
    
