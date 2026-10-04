# Kinepool (flat layout)

All files live in one folder - no `backend/` or `frontend/` directories.

| File | Role |
|---|---|
| `main.py` | FastAPI app, routes, auth, rate limits, serves the 4 HTML pages |
| `ledger_service.py` | Mint pipeline (RVE -> valuation -> ID -> hash-chained record) |
| `chronometric_engine.py` | Engine A - exact-integer tick math + base-100 IDs |
| `uniqueness_engine.py` | Engine B - NodeID grammar (sub-ticks are DB-backed in `ledger_service.py`) |
| `rve_engine.py` | Engine C - HMAC attestation (readings are UNVERIFIED self-reports) |
| `valuation_engine.py` | Engine D - Decimal Kine math, $2.00 floor, 1.5% PFS + 1.5% RSP |
| `integrity.py` | Hash chain + verification |
| `models.py`, `database.py` | SQLAlchemy models / async engine |
| `*.html` | Dashboard, terminal registration, minting, ledger explorer |
| `test_engines.py`, `test_api.py` | Tests |

## Environment variables (set on Render)
- `DATABASE_URL` - PostgreSQL URL (required; `postgres://` is converted automatically)
- `RVE_SIGNING_KEY` - long random secret (required in production; otherwise signatures break on restart)
- `ADMIN_API_KEY` - enables `POST /api/v8/nodes/register` (header `X-Admin-Key`); unset = disabled
- `ENABLE_DOCS=1` - optional, exposes `/docs`

## Local run
    pip install -r requirements-dev.txt
    KINEPOOL_DEV_SQLITE=1 RVE_SIGNING_KEY=dev-key-change-me-0123456789 uvicorn main:app --reload
    python test_engines.py && pytest test_api.py

## Deploy notes
- The Dockerfile is named `Dockerfile` (not `Dockerfile.txt`).
- Tables are created at startup. `create_all` does NOT alter existing tables: if an older
  schema already exists in your Render database, drop those tables once (prototype data only).
- Single worker only (rate limiter and chain lock are per-process).
```[cite: 1]

---

### 2. `test_engines.py`
Runs pure-logic unit tests for engines A through D, integrity hashing, and node ID grammars without needing a database or web framework[cite: 1].

```python
"""Pure-logic tests (no web framework or database needed).
Run:  python test_engines.py     (or: pytest test_engines.py)
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fractions import Fraction

import integrity
from chronometric_engine import ChronometricEngine
from rve_engine import ResourceVerificationEngine
from uniqueness_engine import NodeIDRegistry
from valuation_engine import ValuationEngine, fmt_e8

GW = datetime(2015, 9, 14, 9, 50, 45, 390000, tzinfo=timezone.utc)
chrono = ChronometricEngine()


def test_gw150914_identifier_matches_spec():
    assert chrono.compute_ticks(GW) == 1135171679776616766
    assert chrono.generate_identifier(3, GW, "THR", 1) == "03:00.01.13.51.71.67.97.76.61.67.66-THR.01"


def test_t0_jdn_and_timezone_handling():
    assert chrono.get_t0_jdn() == Fraction(-3861999, 2)          # -1930999.5
    ist = GW.astimezone(timezone(timedelta(hours=5, minutes=30)))
    assert chrono.compute_ticks(ist) == chrono.compute_ticks(GW)  # same instant
    try:
        chrono.compute_ticks(datetime(2015, 9, 14))                # naive
        assert False, "naive datetime must be rejected"
    except ValueError:
        pass


def test_ticks_are_monotonic_and_334ns_apart():
    a = chrono.compute_ticks(GW)
    b = chrono.compute_ticks(GW + timedelta(microseconds=1))
    assert 2 <= b - a <= 4          # 1 us = ~2.99 ticks of 334 ns


def test_base100_roundtrip_and_bounds():
    n = chrono.compute_ticks(GW)
    payload = chrono.encode_base100_payload(n)
    assert int("".join(payload.split(".")), 10) == n
    assert len(payload.split(".")) == 11
    for bad in (-1, 100 ** 11):
        try:
            chrono.encode_base100_payload(bad)
            assert False
        except (ValueError, OverflowError):
            pass


def test_valuation_invariants():
    v = ValuationEngine()
    s = v.settle(Decimal("50"), Decimal("5"))
    assert fmt_e8(s["raw_kines_e8"]) == "27.50000000"
    assert fmt_e8(s["valuation_usd_e8"]) == "55.00000000"       # $2.00 floor
    assert s["pfs_e8"] + s["rsp_e8"] + s["net_e8"] == s["raw_kines_e8"]
    assert s["pfs_e8"] == s["rsp_e8"]
    tiny = v.settle(Decimal("0.000001"), Decimal("0"))           # rounding never leaks value
    assert tiny["pfs_e8"] + tiny["rsp_e8"] + tiny["net_e8"] == tiny["raw_kines_e8"]
    try:
        v.settle(Decimal("0"), Decimal("0"))
        assert False
    except ValueError:
        pass


def test_integrity_chain_detects_tampering():
    entries, prev = [], integrity.GENESIS_HASH
    for i in range(1, 4):
        e = {"seq": i, "composite_kuts_id": f"05:x-THR.0{i}", "measurement_id": f"m{i}",
             "rve_signature": f"s{i}", "raw_kines_e8": i * 10**8, "valuation_usd_e8": i * 2 * 10**8,
             "pfs_e8": 1, "rsp_e8": 1, "net_e8": i * 10**8 - 2, "prev_hash": prev}
        e["entry_hash"] = integrity.entry_hash(prev, e)
        prev = e["entry_hash"]
        entries.append(e)
    assert integrity.verify_chain(entries)["ok"]
    entries[1]["valuation_usd_e8"] += 1                          # alter a past record
    r = integrity.verify_chain(entries)
    assert not r["ok"] and r["first_bad_seq"] == 2
    del entries[1]                                               # delete a record
    assert not integrity.verify_chain(entries)["ok"]


def test_rve_signature_is_keyed_and_tamper_evident():
    rve = ResourceVerificationEngine(b"k" * 32)
    p = rve.attest_telemetry("THR", "GRL-UID-TEST", 5, "Solar", {"energy_kwh": "10"})
    assert p["trust_level"] == "UNVERIFIED" and rve.verify_packet(p)
    forged = dict(p, raw_metrics={"energy_kwh": "9999"})
    assert not rve.verify_packet(forged)
    other = ResourceVerificationEngine(b"z" * 32)                # different key cannot verify
    assert not other.verify_packet(p)
    assert p["measurement_id"] != rve.attest_telemetry("THR", "x", 5, "Solar", {})["measurement_id"]


def test_node_id_grammar():
    assert NodeIDRegistry.valid_callsign("THR") and NodeIDRegistry.valid_callsign("THR123456")
    assert not NodeIDRegistry.valid_callsign("thr") and not NodeIDRegistry.valid_callsign("TH")
    assert NodeIDRegistry.consistent("THR", "THRINC000")         # old regex rejected this
    assert not NodeIDRegistry.consistent("THR", "ABCINC000")


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print("PASS", name)
    print(f"{len(tests)} tests passed")
```[cite: 1]

---

### 3. `test_api.py`
End-to-end API integration tests verifying registration, authentication, minting rules, search, and chain verification using `pytest`[cite: 1].

```python
"""End-to-end API tests. NOT run by the author (the build sandbox had no network to install
FastAPI) - run them yourself:   pip install -r requirements-dev.txt && pytest test_api.py
"""
import os
import uuid

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("aiosqlite")

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_kinepool.db"
os.environ["RVE_SIGNING_KEY"] = "test-signing-key-0123456789abcdef"
os.environ["ADMIN_API_KEY"] = "test-admin"

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402


@pytest.fixture(scope="module")
def client():
    if os.path.exists("test_kinepool.db"):
        os.remove("test_kinepool.db")
    with TestClient(main.app) as c:
        yield c
    if os.path.exists("test_kinepool.db"):
        os.remove("test_kinepool.db")


@pytest.fixture(scope="module")
def auth(client):
    r = client.post("/api/v8/register", json={"device_profile": "pytest"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def body(**kw):
    d = dict(title="Solar test", category=5, energy_kwh=50, compute_mtok=5,
             idempotency_key=uuid.uuid4().hex)
    d.update(kw)
    return d


def test_health_and_pages(client):
    h = client.get("/api/health").json()
    assert h["status"] == "operational" and h["kine_floor_rate_usd"] == 2.0
    assert client.get("/").status_code == 200
    assert client.get("/explorer.html").status_code == 200
    assert client.get("/main.py").status_code == 404          # source never served
    assert client.get("/Dockerfile").status_code == 404


def test_mint_requires_token(client):
    assert client.post("/api/v8/mint", json=body()).status_code == 401
    assert client.post("/api/v8/mint", json=body(), headers={"Authorization": "Bearer nope"}).status_code == 401


def test_mint_values_and_idempotency(client, auth):
    b = body()
    r = client.post("/api/v8/mint", json=b, headers=auth)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["raw_kines"] == "27.50000000" and j["total_valuation_usd"] == "55.00000000"
    assert j["pfs_allocation"] == j["rsp_allocation"] == "0.41250000"
    assert j["composite_kuts_id"].startswith("05:") and j["composite_kuts_id"].endswith(tuple(f"-THR.{i:02d}" for i in range(100)))
    assert j["trust_level"] == "UNVERIFIED" and j["replayed"] is False
    again = client.post("/api/v8/mint", json=b, headers=auth).json()   # same key -> same record
    assert again["replayed"] is True and again["composite_kuts_id"] == j["composite_kuts_id"]


def test_validation(client, auth):
    for bad in (body(category=17), body(energy_kwh=-1), body(energy_kwh=0, compute_mtok=0),
                body(title="   "), body(idempotency_key="short"), {**body(), "extra": 1}):
        assert client.post("/api/v8/mint", json=bad, headers=auth).status_code == 422


def test_search_and_chain_verify(client, auth):
    for _ in range(3):
        assert client.post("/api/v8/mint", json=body(), headers=auth).status_code == 200
    rows = client.get("/api/v8/ledger/search").json()
    assert len(rows) >= 3 and rows[0]["seq"] > rows[1]["seq"]
    assert client.get("/api/v8/ledger/search", params={"query": "%"}).json() == []   # wildcard escaped
    v = client.get("/api/v8/ledger/verify").json()
    assert v["ok"] is True and v["checked"] >= 4


def test_node_registration_is_admin_only(client):
    payload = {"node_id": "ABC", "full_id": "ABCINC001"}
    assert client.post("/api/v8/nodes/register", json=payload).status_code == 403
    ok = client.post("/api/v8/nodes/register", json=payload, headers={"X-Admin-Key": "test-admin"})
    assert ok.status_code == 200
    dup = client.post("/api/v8/nodes/register", json=payload, headers={"X-Admin-Key": "test-admin"})
    assert dup.status_code == 409
```[cite: 1]