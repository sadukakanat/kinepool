"""
Kinepool // KUTS Revision 8 Uniqueness & NodeID Engine
Engine B: NodeID validation, atomic sub-tick sequence allocation, 
and counter-exhaustion safety handling.
"""

import re
from typing import Dict, Tuple, Optional
from datetime import datetime

class NodeIDRegistry:
    """Manages global NodeID formats, registry resolutions (e.g., THR vs THRINC000), and lifecycles."""
    
    # Regex pattern: 3 uppercase letters followed by optional 0 to 6 numeric digits
    NODE_ID_PATTERN = re.compile(r"^[A-Z]{3}[0-9]{0,6}$")
    
    def __init__(self):
        # Simulated Global Resource Registry (GRR) mapping table
        self.registry: Dict[str, Dict[str, str]] = {
            "THR": {
                "full_id": "THRINC000",
                "status": "ACTIVE",
                "coordinates": "10.493210° N, 76.213464° E",
                "description": "Master Origin Node (Thrissur, India)"
            }
        }

    def validate_node_id(self, node_id: str) -> bool:
        """Validates that a NodeID strictly conforms to Section 4.2 grammar rules."""
        if not self.NODE_ID_PATTERN.match(node_id):
            return False
        return node_id in self.registry or node_id == "THRINC000"

    def resolve_callsign(self, short_or_full_id: str) -> Optional[str]:
        """Resolves between short callsign (e.g., 'THR') and full registry ID ('THRINC000')."""
        if short_or_full_id in self.registry:
            return self.registry[short_or_full_id]["full_id"]
        for callsign, data in self.registry.items():
            if data["full_id"] == short_or_full_id:
                return callsign
        return None


class SubTickAllocator:
    """
    Enforces atomic sub-tick sequence allocation (00-99) within a single 
    Session-Epoch tick (334.00 ns) per NodeID, preventing event collisions.
    """
    def __init__(self):
        # Tracks current state: { node_id: { tick_integer: current_sub_tick_counter } }
        self._active_tick_states: Dict[str, Tuple[int, int]] = {}

    def allocate_sub_tick(self, node_id: str, current_tick: int) -> Tuple[int, str]:
        """
        Allocates an atomic sub-tick counter (00-99) for a given node and Session-Epoch tick.
        Returns: (sub_tick_value, status_message)
        """
        if node_id not in self._active_tick_states:
            # Initialize tracking for this node
            self._active_tick_states[node_id] = (current_tick, 0)
        
        last_tick, sub_counter = self._active_tick_states[node_id]
        
        if current_tick > last_tick:
            # Rollover to a new tick: reset sub-tick counter to 00
            sub_counter = 0
            self._active_tick_states[node_id] = (current_tick, sub_counter)
        elif current_tick == last_tick:
            # Same tick collision avoidance
            sub_counter += 1
            if sub_counter > 99:
                # Counter exhaustion protocol (Section 4.3): 
                # Escalate to Order-32 or queue/backpressure. Here we trigger backpressure/escalation flag.
                return 99, "EXHAUSTION_WARNING: Sub-tick slots (00-99) exceeded. Escalating to Order-32 Register-Epoch."
            self._active_tick_states[node_id] = (current_tick, sub_counter)
        else:
            # Out-of-order clock drift detection
            return 0, "ERROR: Out-of-order timestamp received relative to node ledger history."
            
        return sub_counter, "SUCCESS"


# --- Verification Test ---
if __name__ == "__main__":
    registry = NodeIDRegistry()
    allocator = SubTickAllocator()
    
    test_node = "THR"
    mock_tick = 1135171679776616766
    
    print("--- Kinepool Uniqueness & NodeID Engine Test ---")
    print(f"NodeID '{test_node}' Valid: {registry.validate_node_id(test_node)}")
    
    # Simulate rapid consecutive events within the exact same Session-Epoch tick
    for i in range(3):
        sub_tick, status = allocator.allocate_sub_tick(test_node, mock_tick)
        print(f"Event {i+1} -> Sub-Tick: {sub_tick:02d} | Status: {status}")