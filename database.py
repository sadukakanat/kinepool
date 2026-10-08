"""
KUTS Database Engine (Revision 8) - PostgreSQL edition
Manages PostgreSQL connection handling and schema definitions for nodes, minted
assets, ledger transactions, balances, and synchronization logs.

Connection string comes from the DATABASE_URL environment variable. On Render,
use the *Internal Database URL* of your Postgres instance (same region as the
web service); use the External URL only for connecting from your own machine.
"""

import os

import psycopg
from psycopg.rows import dict_row

# Pool accounts that receive the Least Action Protocol (LAP) splits.
PFS_POOL_ACCOUNT = "PFS_POOL"   # Protocol Fiscal Sweep (1.5%)
RSP_POOL_ACCOUNT = "RSP_POOL"   # Regenerative Stewardship Pool (1.5%)

# Arbitrary constant used to serialise schema creation across workers.
_SCHEMA_LOCK_ID = 80808008


def get_db_connection():
    """Opens a PostgreSQL connection whose rows behave like dictionaries."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it in the Render dashboard "
            "(Environment tab) using your Postgres instance's Internal Database URL."
        )
    return psycopg.connect(database_url, row_factory=dict_row)


_SCHEMA_STATEMENTS = [
    # 1. Nodes (Terminals & Anchor Nodes)
    """
    CREATE TABLE IF NOT EXISTS nodes (
        id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        node_id         TEXT UNIQUE NOT NULL,
        callsign        TEXT NOT NULL,
        entity_name     TEXT NOT NULL,
        domain_category TEXT NOT NULL,
        parent_anchor   TEXT NOT NULL,
        rve_endpoint    TEXT,
        status          TEXT NOT NULL DEFAULT 'PENDING',
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # 2. Assets (Minted Kines & Resources)
    """
    CREATE TABLE IF NOT EXISTS assets (
        id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        composite_id        TEXT UNIQUE NOT NULL,
        title               TEXT NOT NULL,
        functional_category TEXT NOT NULL,
        energy_kwh          NUMERIC(20,8) NOT NULL DEFAULT 0 CHECK (energy_kwh >= 0),
        compute_tokens      NUMERIC(20,8) NOT NULL DEFAULT 0 CHECK (compute_tokens >= 0),
        kines_minted        NUMERIC(20,8) NOT NULL CHECK (kines_minted >= 0),
        floor_usd_value     NUMERIC(20,2) NOT NULL,
        target_anchor       TEXT NOT NULL,
        owner_node          TEXT NOT NULL,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # 3. Ledger transactions (amount_kines is the gross mint; net_kines is what
    #    the recipient receives after the PFS and RSP splits).
    """
    CREATE TABLE IF NOT EXISTS ledger_transactions (
        id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        tx_hash            TEXT UNIQUE NOT NULL,
        sender             TEXT NOT NULL,
        recipient          TEXT NOT NULL,
        amount_kines       NUMERIC(20,8) NOT NULL,
        pfs_split          NUMERIC(20,8) NOT NULL,
        rsp_split          NUMERIC(20,8) NOT NULL,
        net_kines          NUMERIC(20,8) NOT NULL,
        asset_composite_id TEXT REFERENCES assets(composite_id),
        timestamp          TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # 4. Chronometric sync logs
    """
    CREATE TABLE IF NOT EXISTS sync_logs (
        id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        node_id        TEXT NOT NULL,
        offset_ns      DOUBLE PRECISION NOT NULL,
        uncertainty_ns DOUBLE PRECISION NOT NULL,
        status         TEXT NOT NULL,
        recorded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_sync_logs_node ON sync_logs (node_id, id DESC)",
    # 5. Balances: one row per account (a node ID or a pool account).
    """
    CREATE TABLE IF NOT EXISTS balances (
        account_id     TEXT PRIMARY KEY,
        balance_kines  NUMERIC(20,8) NOT NULL DEFAULT 0 CHECK (balance_kines >= 0),
        updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
]


def init_database():
    """Creates the schema if it does not exist and seeds the LAP pool accounts."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Several workers may start at once; make schema creation one-at-a-time.
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (_SCHEMA_LOCK_ID,))
            for statement in _SCHEMA_STATEMENTS:
                cur.execute(statement)
            for account in (PFS_POOL_ACCOUNT, RSP_POOL_ACCOUNT):
                cur.execute(
                    "INSERT INTO balances (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (account,),
                )
    print("KUTS Database initialized successfully (PostgreSQL).")


if __name__ == "__main__":
    init_database()
