"""
KUTS Uniqueness Engine (Revision 8) - PostgreSQL edition
Enforces global constraint checks to guarantee uniqueness for node callsigns,
composite asset identifiers, and transaction hashes across the ledger.
"""

from database import get_db_connection


def _exists(query: str, value: str) -> bool:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(query, (value,))
        return cur.fetchone() is not None


class UniquenessEngine:
    @staticmethod
    def is_callsign_unique(callsign: str) -> bool:
        """True if no registered node already uses this callsign."""
        return not _exists("SELECT 1 FROM nodes WHERE callsign = %s LIMIT 1", callsign.upper())

    @staticmethod
    def is_composite_id_unique(composite_id: str) -> bool:
        """True if no minted asset already uses this composite ID."""
        return not _exists("SELECT 1 FROM assets WHERE composite_id = %s LIMIT 1", composite_id)

    @staticmethod
    def is_tx_hash_unique(tx_hash: str) -> bool:
        """True if no ledger transaction already uses this hash."""
        return not _exists("SELECT 1 FROM ledger_transactions WHERE tx_hash = %s LIMIT 1", tx_hash)


if __name__ == "__main__":
    print("Testing Uniqueness Engine...")
    print("Callsign 'KIN' unique:", UniquenessEngine.is_callsign_unique("KIN"))
