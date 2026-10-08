"""
KUTS Master Consensus Coordinator (MCC) Main Application (Revision 8)
FastAPI entrypoint integrating database initialization, node registration,
chronometric synchronization, asset minting, ledger transactions, and RVE verification.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import modular backend components
from database import init_database
from models import NodeRegistrationRequest, AssetMintRequest, ChronometricSyncRequest
from node_service import NodeService
from ledger_service import LedgerService
from chronometric_service import ChronometricService
from rve_engine import ResourceVerificationEngine
from integrity import IntegrityEngine

app = FastAPI(
    title="Kinepool Master Consensus Coordinator (MCC)",
    description="KUTS Revision 8 Decentralized Resource Ledger & Chronometric API",
    version="8.0.0"
)

# Configure CORS for Render production and local development testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from https://kinepool.onrender.com and local frontends
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory (if you have CSS/JS assets in a "static" folder)
# Remove or adjust this line if your assets are structured differently.
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass

@app.on_event("startup")
def startup_event():
    """Initializes the SQLite database schema upon application startup."""
    init_database()
    print("KUTS MCC FastAPI Backend initialized successfully for https://kinepool.onrender.com")

@app.get("/")
def serve_index():
    """Serves the frontend index.html file at the root URL."""
    return FileResponse("index.html")

@app.get("/api/status")
def system_status():
    """System status and Master Origin verification endpoint."""
    return {
        "system": "Kinepool Master Consensus Coordinator (MCC)",
        "master_origin": "THRINC000",
        "location": "Thrissur, Kerala, India",
        "specification": "KUTS Revision 8",
        "status": "ONLINE"
    }

@app.post("/api/v8/register", status_code=status.HTTP_201_CREATED)
def register_node(payload: NodeRegistrationRequest):
    """Registers a terminal or anchor node in the global registry."""
    result = NodeService.register_node(
        node_id=payload.node_id,
        callsign=payload.callsign,
        entity_name=payload.entity_name,
        domain_category=payload.domain_category,
        parent_anchor=payload.parent_anchor,
        rve_endpoint=payload.rve_endpoint
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.get("/api/v8/nodes")
def get_nodes():
    """Retrieves all registered nodes from the database."""
    return {"nodes": NodeService.get_all_nodes()}

@app.post("/api/v8/mint", status_code=status.HTTP_201_CREATED)
def mint_asset(payload: AssetMintRequest):
    """Mints tokenized Kines and commits transaction to the ledger."""
    result = LedgerService.mint_asset(
        title=payload.title,
        category=payload.functional_category,
        kwh=payload.energy_kwh,
        compute_tokens=payload.compute_tokens,
        target_anchor=payload.target_anchor,
        owner_node=payload.owner_node
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.get("/api/v8/assets")
def get_assets():
    """Retrieves all minted assets from the ledger."""
    return {"assets": LedgerService.get_all_assets()}

@app.get("/api/v8/transactions")
def get_transactions():
    """Retrieves recent ledger transactions and LAP splits."""
    return {"transactions": LedgerService.get_all_transactions()}

@app.post("/api/v8/sync")
def record_synchronization(payload: ChronometricSyncRequest):
    """Records node chronometric synchronization and light propagation offset."""
    sync_res = ChronometricService().record_node_sync(
        node_id=payload.node_id,
        target_lat=payload.target_lat,
        target_lon=payload.target_lon,
        local_clock_offset_ns=payload.local_clock_offset_ns
    )
    return sync_res

@app.post("/api/v8/attest")
def verify_attestation(node_id: str, kwh: float, compute: float, signature: str):
    """Verifies node resource telemetry attestation against RVE standards."""
    is_valid = ResourceVerificationEngine.verify_node_attestation(node_id, kwh, compute, signature)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Resource attestation validation failed.")
    return {"node_id": node_id, "attestation": "SUCCESS", "status": "VERIFIED"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
