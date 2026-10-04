from fastapi import FastAPI, HTTPException, APIRouter, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timezone
import os
import sys

# SQLAlchemy Imports
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from database import get_db
from models import DBNodeRegistry, DBSettlement

app = FastAPI(title="Kinepool MCC Master Ledger")
router = APIRouter()

# 1. Define missing Pydantic Request Model
class NodeCreateRequest(BaseModel):
    node_id: str
    full_id: str
    coordinates: str = None

@router.post("/api/v8/nodes/register")
async def register_node_db(req: NodeCreateRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(DBNodeRegistry).where(DBNodeRegistry.callsign == req.node_id)
    result = await db.execute(stmt)
    existing_node = result.scalars().first()
    
    if existing_node:
        raise HTTPException(
            status_code=400, 
            detail=f"Node callsign '{req.node_id}' is already registered in the database."
        )
    
    new_node = DBNodeRegistry(
        callsign=req.node_id,
        full_id=req.full_id,
        status="ACTIVE",
        coordinates=req.coordinates
    )
    
    db.add(new_node)
    await db.commit()  # Commit the transaction
    await db.refresh(new_node)
    
    return {
        "status": "NODE_COMMISSIONED_IN_DB",
        "node_id": req.node_id,
        "full_id": req.full_id,
        "message": "Hardware terminal successfully written to PostgreSQL ledger."
    }

@router.get("/api/v8/ledger/search")
async def search_ledger(query: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(DBSettlement)
    
    if query:
        stmt = stmt.where(
            or_(
                DBSettlement.composite_kuts_id.ilike(f"%{query}%"),
                DBSettlement.measurement_id.ilike(f"%{query}%")
            )
        ).limit(50)  # Safety limit for search results
    else:
        stmt = stmt.order_by(DBSettlement.created_at.desc()).limit(20)
        
    result = await db.execute(stmt)
    settlements = result.scalars().all()
    
    return [
        {
            "composite_kuts_id": s.composite_kuts_id,
            "measurement_id": s.measurement_id,
            "raw_kines": s.raw_kines,
            "total_valuation_usd": s.total_valuation_usd,
            "pfs_allocation": s.pfs_allocation,
            "rsp_allocation": s.rsp_allocation,
            "audit_trail": s.audit_trail,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in settlements
    ]

# Include the router
app.include_router(router)

# Mount current directory for static HTML/CSS serving
app.mount("/", StaticFiles(directory=".", html=True), name="static")