from fastapi import APIRouter, HTTPException
from typing import List, Optional
from models.database import get_db
from models.schemas import BuildGuide
from utils.helpers import mongo_doc_to_dict
from bson import ObjectId

router = APIRouter(prefix="/api/guides", tags=["guides"])

@router.get("/", response_model=List[BuildGuide])
async def get_guides():
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = db.build_guides.find()
    docs = await cursor.to_list(length=100)
    return [BuildGuide(**mongo_doc_to_dict(doc)) for doc in docs]

@router.get("/{guide_id}", response_model=BuildGuide)
async def get_guide(guide_id: str):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        doc = await db.build_guides.find_one({"_id": ObjectId(guide_id)})
    except Exception:
        doc = None
        
    if not doc:
        raise HTTPException(status_code=404, detail="Build guide not found")
        
    return BuildGuide(**mongo_doc_to_dict(doc))

@router.post("/", response_model=BuildGuide, status_code=201)
async def create_guide(guide: BuildGuide):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    guide_data = guide.model_dump(exclude={"id"})
    result = await db.build_guides.insert_one(guide_data)
    
    doc = await db.build_guides.find_one({"_id": result.inserted_id})
    return BuildGuide(**mongo_doc_to_dict(doc))

@router.put("/{guide_id}", response_model=BuildGuide)
async def update_guide(guide_id: str, guide: BuildGuide):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        obj_id = ObjectId(guide_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid guide ID")
        
    guide_data = guide.model_dump(exclude={"id"})
    result = await db.build_guides.update_one(
        {"_id": obj_id},
        {"$set": guide_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Build guide not found")
        
    doc = await db.build_guides.find_one({"_id": obj_id})
    return BuildGuide(**mongo_doc_to_dict(doc))

@router.delete("/{guide_id}")
async def delete_guide(guide_id: str):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        obj_id = ObjectId(guide_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid guide ID")
        
    result = await db.build_guides.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Build guide not found")
        
    return {"message": "Build guide deleted successfully", "id": guide_id}
