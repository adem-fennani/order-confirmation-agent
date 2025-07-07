from src.agent.database.sqlite import SQLiteDatabase
from src.agent.agent import OrderConfirmationAgent

db = SQLiteDatabase()
agent = OrderConfirmationAgent(db)

def get_db():
    return db

def get_agent():
    return agent 