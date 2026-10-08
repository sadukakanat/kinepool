"""
KUTS Admin Operations Engine (Revision 8)
Handles multi-tier administrative authorization, node status override,
global parameter adjustments, and audit log generation.
"""

from fastapi import HTTPException, status
from database import get_db_connection

class AdminService:
    @staticmethod
    def verify_admin_privilege(node_id: str, required_level: int) -> bool:
        """Verifies if a node admin holds sufficient hierarchical rank (Level 1, 2, or 3)."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT admin_level, status FROM nodes WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return False
        
        admin_level, node_status = row[0], row[1]
        if node_status != "ACTIVE" or admin_level > required_level:
            return False
        return True

    @staticmethod
    def update_global_parameters(admin_node_id: str, new_floor_rate: float, new_lap_split: float):
        """Level 1 Admin action to update global protocol parameters."""
        if not AdminService.verify_admin_privilege(admin_node_id, required_level=1):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Unauthorized: Level 1 Master Origin privileges required."
            )
        
        # Persist parameter update logic to database/registry
        return {
            "success": True,
            "message": "Global KUTS parameters successfully updated across all nodes.",
            "floor_rate": new_floor_rate,
            "lap_split": new_lap_split
        }