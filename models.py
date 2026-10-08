"""
KUTS API Data Models (Revision 8)
Defines Pydantic models for request bodies, validation schemas, and response 
structures for nodes, asset minting, ledger transactions, and telemetry sync.
"""

from pydantic import BaseModel, Field
from typing import Optional

class NodeRegistrationRequest(BaseModel):
    node_id: str = Field(..., description="Unique composite node ID or identifier")
    callsign: str = Field(..., min_length=3, max_length=3, description="3-letter node callsign")
    entity_name: str = Field(..., description="Operator or entity name")
    domain_category: str = Field(..., description="Primary domain category code (e.g., '02', '13', '14')")
    parent_anchor: str = Field(..., description="Parent Global Anchor Node ID (e.g., 'THRINC000')")
    rve_endpoint: Optional[str] = Field(None, description="Resource-Verification Engine endpoint URL")

class AssetMintRequest(BaseModel):
    title: str = Field(..., description="Title or description of the telemetry/resource unit")
    functional_category: str = Field(..., description="Functional domain category")
    energy_kwh: float = Field(..., ge=0.0, description="Energy metric in kWh")
    compute_tokens: float = Field(..., ge=0.0, description="Compute metric in units")
    target_anchor: str = Field(..., description="Target parent anchor node callsign or ID")
    owner_node: str = Field(..., description="Owner node identifier receiving the minted Kines")

class ChronometricSyncRequest(BaseModel):
    node_id: str = Field(..., description="Reporting node ID")
    target_lat: float = Field(..., ge=-90.0, le=90.0, description="Node latitude")
    target_lon: float = Field(..., ge=-180.0, le=180.0, description="Node longitude")
    local_clock_offset_ns: float = Field(..., description="Measured clock offset in nanoseconds")

if __name__ == "__main__":
    print("Testing Pydantic Models...")
    sample_data = {
        "node_id": "02:00.01.13.51.71.67.97.76.61.67.66-THR.42",
        "callsign": "KIN",
        "entity_name": "Pinaleaf Advancements LLP",
        "domain_category": "02",
        "parent_anchor": "THRINC000",
        "rve_endpoint": "https://rve.kinepool.in/attest"
    }
    req = NodeRegistrationRequest(**sample_data)
    print("Validation Successful for Node Model:", req.dict())