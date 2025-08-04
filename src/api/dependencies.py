# src/api/dependencies.py
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from src.agent.database.sqlite import SQLiteDatabase
from src.agent.database.models import BusinessUser, Base
from src.agent.database.base import DatabaseInterface
from src.agent.agent import OrderConfirmationAgent

async def create_db_tables():
    from src.agent.database.sqlite import SQLiteDatabase
    db = SQLiteDatabase()
    async with db.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return True


def get_db_interface():
    return SQLiteDatabase()

async def get_agent(db: DatabaseInterface = Depends(get_db_interface)) -> OrderConfirmationAgent:
    return OrderConfirmationAgent(db)

async def verify_api_key(x_api_key: str = Header(...), db: SQLiteDatabase = Depends(get_db_interface)):
    if not x_api_key:
        raise HTTPException(status_code=400, detail="X-API-Key header missing")
    
    user = await db.get_business_user_by_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    return user