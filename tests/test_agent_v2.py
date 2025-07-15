import pytest
from src.agent.agent import OrderConfirmationAgent
from src.agent.database.sqlite import SQLiteDatabase
from src.agent.models import Order, OrderItem, ConversationState
from datetime import datetime
import json
from tests.llm_responses import get_llm_response

@pytest.fixture
def db():
    db = SQLiteDatabase(db_url="sqlite:///:memory:")
    return db

@pytest.fixture
def agent(db):
    return OrderConfirmationAgent(db)

@pytest.fixture
def mock_llm(monkeypatch):
    def mock_call_llm(prompt, model=None, system_prompt=None, max_tokens=None):
        import inspect
        caller_frame = inspect.stack()[2]
        test_name = caller_frame.function
        if "test_confirm_order_with_yes_or_oui" in test_name:
            return get_llm_response("test_confirm_order_with_yes_or_oui")
        if "test_language_switch_mid_conversation" in test_name:
             return get_llm_response("test_language_switch_mid_conversation")
        return get_llm_response(test_name)

    monkeypatch.setattr("src.agent.agent.call_llm", mock_call_llm)

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
    db.create_order(order.model_dump())
    
    response = agent.start_conversation("test_order", language="en")
    
    assert "Hello John Doe" in response
    assert "confirming your order" in response
    assert "1x laptop" in response.lower()
    assert "1200.0" in response
    assert "is this correct?" in response.lower()

def test_cancel_order(agent, db, mock_llm):
    order = Order(
        id="test_order",
        customer_name="John Doe",
        customer_phone="1234567890",
        items=[OrderItem(name="Laptop", quantity=1, price=1200)],
        status="pending",
        total_amount=1200,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    
    agent.llm_process_message("test_order", "I want to cancel my order", language="en")
    
    updated_order = db.get_order("test_order")
    assert updated_order["status"] == "cancelled"

def test_confirm_order_with_yes_or_oui(agent, db, mock_llm):
    order = Order(
        id="test_order_confirm",
        customer_name="Jane Doe",
        customer_phone="0987654321",
        items=[OrderItem(name="Keyboard", quantity=2, price=150)],
        status="pending",
        total_amount=300,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())

    # Agent initiates conversation
    agent.start_conversation("test_order_confirm", language="en")

    # Customer confirms with "yes"
    agent.llm_process_message("test_order_confirm", "yes", language="en")
    updated_order = db.get_order("test_order_confirm")
    assert updated_order["status"] == "confirmed"

    # Reset order status for "oui" test
    db.update_order(order.id, {"status": "pending"})

    # Agent initiates conversation again
    agent.start_conversation("test_order_confirm", language="fr")

    # Customer confirms with "oui"
    agent.llm_process_message("test_order_confirm", "oui", language="fr")
    updated_order = db.get_order("test_order_confirm")
    assert updated_order["status"] == "confirmed"

def test_remove_item_english(agent, db, mock_llm):
    order = Order(
        id="test_remove_en",
        customer_name="Alice",
        customer_phone="1111111111",
        items=[OrderItem(name="Chair", quantity=2, price=10), OrderItem(name="Table", quantity=2, price=20)],
        status="pending",
        total_amount=60,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_remove_en", language="en")
    response = agent.llm_process_message("test_remove_en", "I want to remove the chairs from the order", language="en")
    assert "Table x2" in response
    assert "Chair" not in response
    agent.llm_process_message("test_remove_en", "yes", language="en")
    updated_order = db.get_order("test_remove_en")
    assert updated_order["status"] == "confirmed"

def test_remove_item_french(agent, db, mock_llm):
    order = Order(
        id="test_remove_fr",
        customer_name="Alice",
        customer_phone="1111111111",
        items=[OrderItem(name="Chaise", quantity=2, price=10), OrderItem(name="Table", quantity=2, price=20)],
        status="pending",
        total_amount=60,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_remove_fr", language="fr")
    response = agent.llm_process_message("test_remove_fr", "Je veux supprimer les chaises de la commande", language="fr")
    assert "Table x2" in response
    assert "Chaise" not in response
    agent.llm_process_message("test_remove_fr", "oui", language="fr")
    updated_order = db.get_order("test_remove_fr")
    assert updated_order["status"] == "confirmed"

def test_add_item_english(agent, db, mock_llm):
    order = Order(
        id="test_add_en",
        customer_name="Bob",
        customer_phone="2222222222",
        items=[OrderItem(name="Table", quantity=2, price=20)],
        status="pending",
        total_amount=40,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_add_en", language="en")
    response = agent.llm_process_message("test_add_en", "Add 3 chairs", language="en")
    assert "Chair x3" in response
    agent.llm_process_message("test_add_en", "yes", language="en")
    updated_order = db.get_order("test_add_en")
    assert updated_order["status"] == "confirmed"

def test_add_item_french(agent, db, mock_llm):
    order = Order(
        id="test_add_fr",
        customer_name="Bob",
        customer_phone="2222222222",
        items=[OrderItem(name="Table", quantity=2, price=20)],
        status="pending",
        total_amount=40,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_add_fr", language="fr")
    response = agent.llm_process_message("test_add_fr", "Ajouter 3 chaises", language="fr")
    assert "Chaise x3" in response or "Chaises x3" in response
    agent.llm_process_message("test_add_fr", "oui", language="fr")
    updated_order = db.get_order("test_add_fr")
    assert updated_order["status"] == "confirmed"

def test_replace_item_english(agent, db, mock_llm):
    order = Order(
        id="test_replace_en",
        customer_name="Carol",
        customer_phone="3333333333",
        items=[OrderItem(name="Pizza", quantity=2, price=12), OrderItem(name="Lasagna", quantity=2, price=14)],
        status="pending",
        total_amount=52,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_replace_en", language="en")
    response = agent.llm_process_message("test_replace_en", "Replace lasagna with salad", language="en")
    assert "Salad" in response
    assert "Lasagna" not in response
    agent.llm_process_message("test_replace_en", "yes", language="en")
    updated_order = db.get_order("test_replace_en")
    assert updated_order["status"] == "confirmed"

def test_replace_item_french(agent, db, mock_llm):
    order = Order(
        id="test_replace_fr",
        customer_name="Carol",
        customer_phone="3333333333",
        items=[OrderItem(name="Pizza", quantity=2, price=12), OrderItem(name="Lasagne", quantity=2, price=14)],
        status="pending",
        total_amount=52,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_replace_fr", language="fr")
    response = agent.llm_process_message("test_replace_fr", "Remplacer lasagne par salade", language="fr")
    assert "Salade" in response
    assert "Lasagne" not in response
    agent.llm_process_message("test_replace_fr", "oui", language="fr")
    updated_order = db.get_order("test_replace_fr")
    assert updated_order["status"] == "confirmed"

def test_modify_quantity_english(agent, db, mock_llm):
    order = Order(
        id="test_modifyqty_en",
        customer_name="Dan",
        customer_phone="4444444444",
        items=[OrderItem(name="Table", quantity=2, price=20)],
        status="pending",
        total_amount=40,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_modifyqty_en", language="en")
    response = agent.llm_process_message("test_modifyqty_en", "Change the number of tables to 5", language="en")
    assert "Table x5" in response
    agent.llm_process_message("test_modifyqty_en", "yes", language="en")
    updated_order = db.get_order("test_modifyqty_en")
    assert updated_order["status"] == "confirmed"

def test_modify_quantity_french(agent, db, mock_llm):
    order = Order(
        id="test_modifyqty_fr",
        customer_name="Dan",
        customer_phone="4444444444",
        items=[OrderItem(name="Table", quantity=2, price=20)],
        status="pending",
        total_amount=40,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_modifyqty_fr", language="fr")
    response = agent.llm_process_message("test_modifyqty_fr", "Changer le nombre de tables à 5", language="fr")
    assert "Table x5" in response
    agent.llm_process_message("test_modifyqty_fr", "oui", language="fr")
    updated_order = db.get_order("test_modifyqty_fr")
    assert updated_order["status"] == "confirmed"

def test_cancel_order_english(agent, db, mock_llm):
    order = Order(
        id="test_cancel_en",
        customer_name="Eve",
        customer_phone="5555555555",
        items=[OrderItem(name="Table", quantity=2, price=20)],
        status="pending",
        total_amount=40,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_cancel_en", language="en")
    agent.llm_process_message("test_cancel_en", "I want to cancel my order", language="en")
    updated_order = db.get_order("test_cancel_en")
    assert updated_order["status"] == "cancelled"

def test_cancel_order_french(agent, db, mock_llm):
    order = Order(
        id="test_cancel_fr",
        customer_name="Eve",
        customer_phone="5555555555",
        items=[OrderItem(name="Table", quantity=2, price=20)],
        status="pending",
        total_amount=40,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_cancel_fr", language="fr")
    agent.llm_process_message("test_cancel_fr", "Je veux annuler ma commande", language="fr")
    updated_order = db.get_order("test_cancel_fr")
    assert updated_order["status"] == "cancelled"

def test_ambiguous_request_english(agent, db, mock_llm):
    order = Order(
        id="test_ambig_en",
        customer_name="Frank",
        customer_phone="6666666666",
        items=[OrderItem(name="Table", quantity=2, price=20)],
        status="pending",
        total_amount=40,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_ambig_en", language="en")
    response = agent.llm_process_message("test_ambig_en", "Can you help?", language="en")
    assert "clarify" in response.lower() or "not sure" in response.lower()

def test_ambiguous_request_french(agent, db, mock_llm):
    order = Order(
        id="test_ambig_fr",
        customer_name="Frank",
        customer_phone="6666666666",
        items=[OrderItem(name="Table", quantity=2, price=20)],
        status="pending",
        total_amount=40,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_ambig_fr", language="fr")
    response = agent.llm_process_message("test_ambig_fr", "Pouvez-vous m'aider ?", language="fr")
    assert "préciser" in response.lower() or "pas sûr" in response.lower()

def test_language_switch_mid_conversation(agent, db, mock_llm):
    order = Order(
        id="test_langswitch",
        customer_name="Grace",
        customer_phone="7777777777",
        items=[OrderItem(name="Pizza", quantity=1, price=12)],
        status="pending",
        total_amount=12,
        created_at=datetime.utcnow().isoformat()
    )
    db.create_order(order.model_dump())
    agent.start_conversation("test_langswitch", language="fr")
    response1 = agent.llm_process_message("test_langswitch", "Je veux ajouter une pizza", language="fr")
    assert "pizza" in response1.lower()
    assert "ajoutée" in response1.lower() or "ajouté" in response1.lower()
    response2 = agent.llm_process_message("test_langswitch", "Remove the pizza", language="en")
    assert "pizza" in response2.lower()
    assert "removed" in response2.lower() or "delete" in response2.lower()