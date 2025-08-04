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


def get_db():
    db = SQLiteDatabase()
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()

def get_db_interface():
    return SQLiteDatabase()

async def get_agent(db: DatabaseInterface = Depends(get_db_interface)) -> OrderConfirmationAgent:
    return OrderConfirmationAgent(db)

async def verify_api_key(x_api_key: str = Header(...), session: Session = Depends(get_db)):
    if not x_api_key:
        raise HTTPException(status_code=400, detail="X-API-Key header missing")
    
    user = session.query(BusinessUser).filter_by(api_key=x_api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    return user
