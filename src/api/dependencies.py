from src.agent.database.sqlite import SQLiteDatabase
from src.agent.agent import OrderConfirmationAgent
from src.agent.database.models import Base

db = SQLiteDatabase()
agent = OrderConfirmationAgent(db)

async def create_db_tables():
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def get_db():
    return db

def get_agent():
    return agent 