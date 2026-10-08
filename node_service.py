"""
KUTS Node Service (Revision 8) - PostgreSQL edition
Handles database operations, registration logic, and validation for
Terminals, Anchor Nodes, and Entities within the Global Resource Registry.
"""

import psycopg

from database import get_db_connection


class NodeService:
    @staticmethod
    def register_node(node_id: str, callsign: str, entity_name: str, domain_category: str,
                      parent_anchor: str, rve_endpoint: str = None):
        """
        Registers a new node (Anchor Node, Terminal, or Entity) in the database.

        NOTE: nodes are currently marked 'VERIFIED' on registration without any
        compliance check (same behaviour as before). Change the status here to
        'PENDING' once a real verification step exists.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO nodes (node_id, callsign, entity_name, domain_category,
                                       parent_anchor, rve_endpoint, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'VERIFIED')
                    """,
                    (node_id, callsign.upper(), entity_name, domain_category,
                     parent_anchor, rve_endpoint),
                )
            conn.commit()
            success = True
            message = "Node successfully registered and verified on Master Origin network."
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            success = False
            message = f"Registration failed: Node ID '{node_id}' already exists in registry."
        finally:
            conn.close()

        return {
            "success": success,
            "message": message,
            "node_id": node_id,
            "callsign": callsign.upper(),
            "parent_anchor": parent_anchor,
        }

    @staticmethod
    def get_all_nodes():
        """Retrieves all registered nodes for exploration and audit."""
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT node_id, callsign, entity_name, domain_category, parent_anchor,
                       rve_endpoint, status, created_at
                FROM nodes
                ORDER BY id DESC
                """
            )
            return cur.fetchall()

    @staticmethod
    def get_node_by_id(node_id: str):
        """Retrieves a specific node by its Node ID or composite identifier."""
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM nodes WHERE node_id = %s", (node_id,))
            return cur.fetchone()


if __name__ == "__main__":
    print("Testing Node Service...")
    print(NodeService.register_node(
        node_id="02:00.01.13.51.71.67.97.76.61.67.66-THR.42",
        callsign="KIN",
        entity_name="Pinaleaf Advancements LLP",
        domain_category="02",
        parent_anchor="THRINC000",
        rve_endpoint="https://rve.kinepool.in/attest",
    ))
