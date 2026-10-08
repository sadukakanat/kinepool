"""
KUTS Uniqueness Engine (Revision 8)
Enforces global constraint checks to guarantee uniqueness for node callsigns,
composite asset identifiers, and transaction hashes across the ledger.
"""

from database import get_db_connection

class UniquenessEngine:
    @staticmethod
    def is_callsign_unique(callsign: str) -> bool:
        """Verifies if a node callsign is already registered in the database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM nodes WHERE callsign = ?", (callsign.upper(),))
        row = cursor.fetchone()
        conn.close()
        return row is None

    @staticmethod
    def is_composite_id_unique(composite_id: str) -> bool:
        """Verifies if a minted asset composite ID is unique."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE composite_id = ?", (composite_id,))
        row = cursor.fetchone()
        conn.close()
        return row is None

    @staticmethod
    def is_tx_hash_unique(tx_hash: str) -> bool:
        """Verifies if a ledger transaction hash is unique."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM ledger_transactions WHERE tx_hash = ?", (tx_hash,))
        row = cursor.fetchone()
        conn.close()
        return row is None

if __name__ == "__main__":
    print("Testing Uniqueness Engine...")
    test_callsign = "KIN"
    unique_check = UniquenessEngine.is_callsign_unique(test_callsign)
    print(f"Callsign '{test_callsign}' Unique: {unique_check}")