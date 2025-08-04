# scripts/create_test_orders.py
import os
import sys
import asyncio

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agent.database.sqlite import SQLiteDatabase
from src.agent.database.models import OrderModel
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import uuid
from datetime import datetime

def create_test_orders():
    # Use a synchronous engine for this script
    engine = create_engine("sqlite:///orders.db")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create 3 test orders for test_business
    for i in range(3):
        order_id = f"test_order_{uuid.uuid4()}"
        new_order = OrderModel(
            id=order_id,
            customer_name=f"Test Customer {i}",
            customer_phone="1234567890",
            items=[{"name": f"Test Item {i}", "price": 10.0, "quantity": 1}],
            total_amount=10.0,
            status="pending",
            created_at=datetime.utcnow(),
            business_id="test_business",
            site_url="https://example.com",
            site_id="test_site"
        )
        session.add(new_order)
    
    session.commit()
    print("Created 3 test orders for test_business")

if __name__ == "__main__":
    create_test_orders()
