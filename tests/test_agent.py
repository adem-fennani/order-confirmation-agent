
import pytest
from src.agent.agent import OrderConfirmationAgent
from src.agent.database.sqlite import SQLiteDatabase
from src.agent.models import Order, OrderItem, ConversationState
from datetime import datetime
import json

@pytest.fixture
def db():
    db = SQLiteDatabase(db_url="sqlite:///:memory:")
    return db

@pytest.fixture
def agent(db):
    return OrderConfirmationAgent(db)

def test_start_conversation_english(agent, db):
    order = Order(
        id="test_order",
        customer_name="John Doe",
        customer_phone="1234567890",
        items=[OrderItem(name="Laptop", quantity=1, price=1200)],
        status="pending",
        total_amount=1200,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.dict())
    
    response = agent.start_conversation("test_order", language="en")
    
    assert "Hello John Doe" in response
    assert "confirm your order" in response
    assert "Laptop x1" in response
    assert "1200€" in response
    assert "Is this correct?" in response

def test_cancel_order(agent, db):
    order = Order(
        id="test_order",
        customer_name="John Doe",
        customer_phone="1234567890",
        items=[OrderItem(name="Laptop", quantity=1, price=1200)],
        status="pending",
        total_amount=1200,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.dict())
    
    agent.llm_process_message("test_order", "I want to cancel my order", language="en")
    
    updated_order = db.get_order("test_order")
    assert updated_order["status"] == "cancelled"

