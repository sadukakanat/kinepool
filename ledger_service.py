"""
KUTS Ledger Service (Revision 8)
Manages ledger transactions, asset minting records, transfers, and 
automated Least Action Protocol splits (PFS/RSP) across registered nodes.
"""

import uuid
from database import get_db_connection
from valuation_engine import ValuationEngine

class LedgerService:
    @staticmethod
    def mint_asset(title: str, category: str, kwh: float, compute_tokens: float, target_anchor: str, owner_node: str):
        """
        Mints new Kines based on resource metrics, calculates economic valuation,
        applies LAP splits, and commits the asset and transaction to the ledger.
        """
        # Calculate valuation and splits
        valuation = ValuationEngine.calculate_kines(kwh, compute_tokens)
        total_kines = valuation["total_kines"]
        floor_usd = valuation["floor_usd_value"]
        pfs_split = valuation["pfs_split_kines"]
        rsp_split = valuation["rsp_split_kines"]

        # Generate composite identifiers and transaction hash
        composite_id = f"{category}:00.01.13.51.71.67.97.76.61.67.66-{target_anchor}.01"
        tx_hash = f"TX-REV8-{uuid.uuid4().hex[:12].upper()}"

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Insert minted asset
            cursor.execute("""
                INSERT INTO assets (composite_id, title, functional_category, energy_kwh, compute_tokens, kines_minted, floor_usd_value, target_anchor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (composite_id, title, category, kwh, compute_tokens, total_kines, floor_usd, target_anchor))

            # Insert ledger transaction record
            cursor.execute("""
                INSERT INTO ledger_transactions (tx_hash, sender, recipient, amount_kines, pfs_split, rsp_split)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tx_hash, "GENESIS_POOL", owner_node, total_kines, pfs_split, rsp_split))

            conn.commit()
            success = True
            message = "Asset successfully minted and committed to ledger."
        except Exception as e:
            conn.rollback()
            success = False
            message = f"Ledger commit failed: {str(e)}"
        finally:
            conn.close()

        return {
            "success": success,
            "message": message,
            "tx_hash": tx_hash,
            "composite_id": composite_id,
            "valuation": valuation
        }

    @staticmethod
    def get_all_transactions(limit=20):
        """Retrieves recent ledger transactions."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tx_hash, sender, recipient, amount_kines, pfs_split, rsp_split, timestamp 
            FROM ledger_transactions 
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_all_assets():
        """Retrieves all registered/minted assets from the ledger."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT composite_id, title, functional_category, energy_kwh, compute_tokens, kines_minted, floor_usd_value, target_anchor, created_at 
            FROM assets 
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

if __name__ == "__main__":
    print("Testing Ledger Service...")
    test_mint = LedgerService.mint_asset(
        title="Solar Telemetry Grid Unit 01",
        category="02",
        kwh=150.0,
        compute_tokens=2.5,
        target_anchor="THRINC000",
        owner_node="KIN-TERMINAL-01"
    )
    print("Test Mint Result:", test_mint)