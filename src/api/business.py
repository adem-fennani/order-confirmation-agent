# src/api/business.py
from fastapi import APIRouter, Depends
from src.api.dependencies import verify_api_key
from src.agent.database.models import BusinessUser

router = APIRouter()

@router.get("/api/business/test")
async def test_api_key(user: BusinessUser = Depends(verify_api_key)):
    return {"message": f"API Key is valid for business: {user.business_id}"}
