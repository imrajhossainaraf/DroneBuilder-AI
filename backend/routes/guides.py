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
