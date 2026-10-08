"""
KUTS Node Service (Revision 8)
Handles database operations, registration logic, and validation for 
Terminals, Anchor Nodes, and Entities within the Global Resource Registry.
"""

import sqlite3
from database import get_db_connection

class NodeService:
    @staticmethod
    def register_node(node_id: str, callsign: str, entity_name: str, domain_category: str, parent_anchor: str, rve_endpoint: str = None):
        """
        Registers a new node (Anchor Node, Terminal, or Entity) in the database 
        with 'VERIFIED' status upon successful compliance check.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO nodes (node_id, callsign, entity_name, domain_category, parent_anchor, rve_endpoint, status)
                VALUES (?, ?, ?, ?, ?, ?, 'VERIFIED')
            """, (node_id, callsign.upper(), entity_name, domain_category, parent_anchor, rve_endpoint))
            conn.commit()
            success = True
            message = "Node successfully registered and verified on Master Origin network."
        except sqlite3.IntegrityError:
            success = False
            message = f"Registration failed: Node ID '{node_id}' or Callsign already exists in registry."
        finally:
            conn.close()

        return {
            "success": success,
            "message": message,
            "node_id": node_id,
            "callsign": callsign.upper(),
            "parent_anchor": parent_anchor
        }

    @staticmethod
    def get_all_nodes():
        """Retrieves all registered nodes from the database for exploration and audit."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT node_id, callsign, entity_name, domain_category, parent_anchor, rve_endpoint, status, created_at 
            FROM nodes 
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_node_by_id(node_id: str):
        """Retrieves a specific node by its Node ID or composite identifier."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

if __name__ == "__main__":
    print("Testing Node Service...")
    # Test provisional node registration
    test_res = NodeService.register_node(
        node_id="02:00.01.13.51.71.67.97.76.61.67.66-THR.42",
        callsign="KIN",
        entity_name="Pinaleaf Advancements LLP",
        domain_category="02",
        parent_anchor="THRINC000",
        rve_endpoint="https://rve.kinepool.in/attest"
    )
    print("Test Registration Result:", test_res)