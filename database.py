"""
KUTS Database Engine (Revision 8)
Manages SQLite database initialization, connection handling, and schema 
definitions for nodes, minted assets, transactions, and synchronization logs.
"""

import sqlite3
import os

DB_FILE = "kinepool.db"

def get_db_connection():
    """Creates and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
    return conn

def init_database():
    """Initializes the database schema if tables do not already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Nodes Table (Terminals & Anchor Nodes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT UNIQUE NOT NULL,
            callsign TEXT NOT NULL,
            entity_name TEXT NOT NULL,
            domain_category TEXT NOT NULL,
            parent_anchor TEXT NOT NULL,
            rve_endpoint TEXT,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Assets Table (Minted Kines & Resources)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            composite_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            functional_category TEXT NOT NULL,
            energy_kwh REAL DEFAULT 0.0,
            compute_tokens REAL DEFAULT 0.0,
            kines_minted REAL NOT NULL,
            floor_usd_value REAL NOT NULL,
            target_anchor TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Transactions / Ledger Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ledger_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_hash TEXT UNIQUE NOT NULL,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            amount_kines REAL NOT NULL,
            pfs_split REAL NOT NULL,
            rsp_split REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 4. Chronometric Sync Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            offset_ns REAL NOT NULL,
            uncertainty_ns REAL NOT NULL,
            status TEXT NOT NULL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("KUTS Database initialized successfully (kinepool.db).")

if __name__ == "__main__":
    init_database()