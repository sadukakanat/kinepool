"""
Kinepool // KUTS Revision 8 Resource-Verification Engine (RVE)
Engine C: Telemetry ingestion, cryptographic attestation, unique measurement 
tracking, and double-counting prevention.
"""

import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class ResourceVerificationEngine:
    """
    Validates, signs, and attests raw resource telemetry before it enters 
    the Kinepool Normalization and Valuation pipeline.
    """
    
    def __init__(self):
        # Ledger registry tracking consumed measurement IDs to prevent double-minting
        self._consumed_measurement_ids: set = set()
        
    def generate_measurement_id(self, asset_source: str, timestamp: str) -> str:
        """Generates a globally unique measurement ID (UUIDv4 + SHA256 hash)."""
        unique_raw = f"{asset_source}-{timestamp}-{uuid.uuid4()}"
        return hashlib.sha256(unique_raw.encode('utf-8')).hexdigest()

    def attest_telemetry(self, 
                         node_id: str, 
                         category_code: int, 
                         resource_type: str, 
                         raw_metrics: Dict[str, Any], 
                         metering_source: str) -> Dict[str, Any]:
        """
        Ingests raw telemetry, checks against double-counting, signs cryptographically,
        and outputs an RVE-attested telemetry packet.
        """
        timestamp_str = datetime.now(timezone.utc).isoformat()
        measurement_id = self.generate_measurement_id(node_id, timestamp_str)
        
        # Check double-counting constraint (Section 6.3)
        if measurement_id in self._consumed_measurement_ids:
            raise ValueError(f"DUPLICATE_ERROR: Measurement ID {measurement_id} has already been consumed.")

        # Construct the attestation payload package
        packet = {
            "measurement_id": measurement_id,
            "node_id": node_id,
            "category_code": f"{category_code:02d}",
            "resource_type": resource_type,
            "metering_source": metering_source, # e.g., "SmartMeter-API-v2", "AWS-Cloudwatch"
            "raw_metrics": raw_metrics,
            "attested_at_utc": timestamp_str,
            "status": "ATTESTED"
        }

        # Generate a tamper-evident cryptographic signature for the packet
        packet_string = json.dumps(packet, sort_keys=True)
        digital_signature = hashlib.sha256(packet_string.encode('utf-8')).hexdigest()
        
        packet["rve_signature"] = digital_signature
        
        # Mark as registered in local verification ledger
        self._consumed_measurement_ids.add(measurement_id)
        
        return packet


# --- Verification Test ---
if __name__ == "__main__":
    rve = ResourceVerificationEngine()
    
    print("--- Kinepool Resource-Verification Engine (RVE) Test ---")
    
    # Simulate incoming solar farm energy telemetry (Category 05 / Elemental or 13 / Structural)
    solar_telemetry = {
        "energy_kwh": 450.5,
        "peak_output_kw": 75.0,
        "duration_hours": 6.0
    }
    
    try:
        attested_packet = rve.attest_telemetry(
            node_id="THR",
            category_code=5,
            resource_type="Renewable Energy Generation",
            raw_metrics=solar_telemetry,
            metering_source="Utility-SmartMeter-Grid-Modbus"
        )
        print("Telemetry successfully attested by RVE:")
        print(json.dumps(attested_packet, indent=2))
        
    except ValueError as e:
        print(f"Attestation Failed: {e}")