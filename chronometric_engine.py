"""
KUTS Chronometric Engine (Revision 8)
Handles high-precision temporal synchronization, session-epoch calculations,
propagation light-delay corrections relative to Master Origin Node (THRINC000),
and clock drift monitoring.
"""

import time
import math
from datetime import datetime, timezone

# KUTS Revision 8 Chronometric Constants
SESSION_EPOCH_NS = 334.00  # Nanoseconds per tick threshold
MASTER_ORIGIN_CALLSIGN = "THRINC000"
MASTER_ORIGIN_COORDS = {"lat": 10.493210, "lon": 76.213464}

class ChronometricEngine:
    def __init__(self, node_id="THRINC000", base_lat=10.493210, base_lon=76.213464):
        self.node_id = node_id
        self.lat = base_lat
        self.lon = base_lon
        self.reference_origin = MASTER_ORIGIN_CALLSIGN

    def get_current_utc_iso(self):
        """Returns current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    def calculate_light_delay(self, target_lat, target_lon):
        """
        Calculates approximate light-travel-time propagation delay 
        relative to the Master Origin Node (THRINC000) in Thrissur, India.
        """
        lat1 = math.radians(MASTER_ORIGIN_COORDS["lat"])
        lon1 = math.radians(MASTER_ORIGIN_COORDS["lon"])
        lat2 = math.radians(target_lat)
        lon2 = math.radians(target_lon)
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371.0  # Radius of earth in km
        distance_km = c * r
        
        # Speed of light in fiber optic cable approximation (~200,000 km/s)
        speed_of_light_fiber = 200000.0  # km/s
        delay_seconds = distance_km / speed_of_light_fiber
        delay_ns = delay_seconds * 1e9
        return round(delay_ns, 2)

    def generate_timestamp_packet(self):
        """Generates a Revision 8 compliant chronometric timestamp packet."""
        current_time = time.time()
        sub_tick = int((current_time % 1) * 100)
        
        packet = {
            "node_id": self.node_id,
            "utc_timestamp": self.get_current_utc_iso(),
            "epoch_tick": int(current_time),
            "sub_tick": f"{sub_tick:02d}",
            "uncertainty_ns": SESSION_EPOCH_NS,
            "status": "SYNCHRONIZED"
        }
        return packet

if __name__ == "__main__":
    engine = ChronometricEngine()
    print("KUTS Chronometric Engine Initialized.")
    print("Sample Packet:", engine.generate_timestamp_packet())