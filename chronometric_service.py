"""
KUTS Chronometric Service (Revision 8) - PostgreSQL edition
Backend service wrapper bridging the database, chronometric engine,
and API routes for temporal synchronization, node offset logging, and drift analysis.
"""

from database import get_db_connection
from chronometric_engine import ChronometricEngine, SESSION_EPOCH_NS, MASTER_ORIGIN_CALLSIGN


class ChronometricService:
    def __init__(self):
        self.engine = ChronometricEngine()

    def record_node_sync(self, node_id: str, target_lat: float, target_lon: float,
                         local_clock_offset_ns: float):
        """
        Records a node synchronization ping, calculates light propagation delay,
        evaluates clock drift against Revision 8 uncertainty limits, and saves to the database.
        """
        # Calculate theoretical propagation delay
        prop_delay_ns = self.engine.calculate_light_delay(target_lat, target_lon)

        # Total offset incorporating propagation delay
        net_offset_ns = abs(local_clock_offset_ns - prop_delay_ns)

        # Evaluate compliance against the 334.00 ns threshold
        status = "SYNCHRONIZED" if net_offset_ns <= SESSION_EPOCH_NS else "DRIFT_WARNING"

        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sync_logs (node_id, offset_ns, uncertainty_ns, status)
                VALUES (%s, %s, %s, %s)
                """,
                (node_id, net_offset_ns, SESSION_EPOCH_NS, status),
            )

        return {
            "node_id": node_id,
            "origin_parent": MASTER_ORIGIN_CALLSIGN,
            "calculated_propagation_delay_ns": prop_delay_ns,
            "net_offset_ns": net_offset_ns,
            "uncertainty_threshold_ns": SESSION_EPOCH_NS,
            "status": status,
        }

    def get_recent_sync_logs(self, limit=10):
        """Retrieves recent chronometric synchronization logs from the database."""
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT node_id, offset_ns, uncertainty_ns, status, recorded_at
                FROM sync_logs
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


if __name__ == "__main__":
    service = ChronometricService()
    print("Testing Chronometric Service synchronization calculation...")
    # London node (approx 51.5074 N, 0.1278 W)
    print("Sync Result:", service.record_node_sync("LONINC002", 51.5074, -0.1278, 1250.0))
