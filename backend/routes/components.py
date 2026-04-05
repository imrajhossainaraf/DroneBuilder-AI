from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from models.database import get_db
from models.schemas import Component
from utils.helpers import mongo_doc_to_dict
from bson import ObjectId

router = APIRouter(prefix="/api/components", tags=["components"])

@router.get("/", response_model=List[Component])
async def get_components(
    component_type: Optional[str] = Query(None, description="Filter by component type"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    search: Optional[str] = Query(None, description="Search by name")
):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    query = {}
    if component_type:
        query["component_type"] = component_type
    if brand:
        query["brand"] = brand
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    cursor = db.drone_components.find(query)
    docs = await cursor.to_list(length=100)
    return [Component(**mongo_doc_to_dict(doc)) for doc in docs]

@router.get("/{component_id}", response_model=Component)
async def get_component(component_id: str):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        doc = await db.drone_components.find_one({"_id": ObjectId(component_id)})
    except Exception:
        doc = None
        
    if not doc:
        raise HTTPException(status_code=404, detail="Component not found")
        
    return Component(**mongo_doc_to_dict(doc))

@router.get("/types/list", response_model=List[str])
async def get_component_types():
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    types = await db.drone_components.distinct("component_type")
    return types
