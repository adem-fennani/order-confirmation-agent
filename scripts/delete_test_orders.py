# scripts/delete_test_orders.py
import os
import sys
import asyncio

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agent.database.sqlite import SQLiteDatabase
from src.agent.database.models import OrderModel
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

def delete_test_orders():
    engine = create_engine("sqlite:///orders.db")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Delete all orders that start with 'test_order_'
    session.query(OrderModel).filter(OrderModel.id.like("test_order_%")).delete(synchronize_session=False)
    session.commit()
    print("Deleted all test orders.")

if __name__ == "__main__":
    delete_test_orders()
