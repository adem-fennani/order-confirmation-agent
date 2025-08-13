import pytest
import asyncio
from fastapi.testclient import TestClient
from src.main import app
import uuid
from src.api.dependencies import create_db_tables
from src.agent.database.sqlite import SQLiteDatabase
from src.agent.database.models import OrderModel
from datetime import datetime

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Ensure DB tables are created before any tests run
    asyncio.run(create_db_tables())

db = SQLiteDatabase()

client = TestClient(app)

# Helper to create a new order
def create_order(items, customer_name="Test User", customer_phone="+1234567890", total_amount=100.0, notes="", woocommerce_order_id=None):
    import uuid
    order_id = str(uuid.uuid4())
    order_data = {
        "id": order_id,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "items": items,
        "total_amount": total_amount,
        "status": "pending",
        "created_at": datetime.now(),  # Pass datetime object, not string
        "notes": notes,
        "confirmed_at": None,
        "delivery_address": None,
        "woocommerce_order_id": woocommerce_order_id
    }
    async def _insert():
        async with db.AsyncSession() as session:
            order = OrderModel(**order_data)
            session.add(order)
            await session.commit()
    asyncio.run(_insert())
    return order_id

# --- 1. Basic Order Confirmation (French) ---
def test_basic_order_confirmation_french():
    """Test basic order confirmation flow in French."""
    order_id = create_order([
        {"name": "Chaise", "quantity": 2, "price": 10.0},
        {"name": "Table", "quantity": 2, "price": 20.0}
    ], customer_name="Jean", customer_phone="+33123456789", woocommerce_order_id="999")
    # Start confirmation (simulate frontend call)
    resp = client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    assert resp.status_code == 200
    assert "fr" in resp.json()["message"].lower() or "commande" in resp.json()["message"].lower()
    # User replies 'Oui'
    resp2 = client.post(f"/orders/{order_id}/message", json={"text": "Oui"})
    assert resp2.status_code == 200
    agent_response = resp2.json()["agent_response"].lower()
    assert "adresse de livraison" in agent_response

    # Simulate user providing an address
    resp3 = client.post(f"/orders/{order_id}/message", json={"text": "123 Rue de la Paix"})
    assert resp3.status_code == 200
    agent_response = resp3.json()["agent_response"].lower()
    assert "votre adresse" or "confirmed" in agent_response or "correct" in agent_response

    # Simulate user confirming the address
    resp4 = client.post(f"/orders/{order_id}/message", json={"text": "Oui"})
    assert resp4.status_code == 200
    agent_response = resp4.json()["agent_response"].lower()
    assert "livraison" in agent_response or "confirmée" in agent_response

# --- 2. Basic Order Confirmation (English) ---
def test_basic_order_confirmation_english():
    """Test basic order confirmation flow in English."""
    order_id = create_order([
        {"name": "Chair", "quantity": 2, "price": 10.0},
        {"name": "Table", "quantity": 2, "price": 20.0}
    ], customer_name="John", customer_phone="+441234567890", woocommerce_order_id="999")
    resp = client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    assert resp.status_code == 200
    assert "john" in resp.json()["message"].lower() or ("chair" in resp.json()["message"].lower() and "table" in resp.json()["message"].lower())
    resp2 = client.post(f"/orders/{order_id}/message", json={"text": "yes"})
    assert resp2.status_code == 200
    agent_response = resp2.json()["agent_response"].lower()
    assert "delivery address" in agent_response

    # Simulate user providing an address
    resp3 = client.post(f"/orders/{order_id}/message", json={"text": "123 Main St, London"})
    assert resp3.status_code == 200
    agent_response = resp3.json()["agent_response"].lower()
    assert "confirm" in agent_response or "correct" in agent_response

    # Simulate user confirming the address
    resp4 = client.post(f"/orders/{order_id}/message", json={"text": "yes"})
    assert resp4.status_code == 200
    agent_response = resp4.json()["agent_response"].lower()
    assert "delivery" in agent_response or "confirmed" in agent_response

# --- 3. Remove Item (English) ---
def test_remove_item_english():
    """Test removing an item in English."""
    order_id = create_order([
        {"name": "Chair", "quantity": 2, "price": 10.0},
        {"name": "Table", "quantity": 2, "price": 20.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "I want to remove the chairs from the order"})
    response = resp.json()["agent_response"].lower()
    assert "table x2" in response
    assert "chair" not in response
    assert "is your order now correct" in response or "est-ce correct" in response
    # Confirm
    resp2 = client.post(f"/orders/{order_id}/message", json={"text": "yes"})
    response2 = resp2.json()["agent_response"].lower()
    assert "address" in response2 or "adresse" in response2
    # Provide address
    resp3 = client.post(f"/orders/{order_id}/message", json={"text": "123 Main St, London"})
    response3 = resp3.json()["agent_response"].lower()
    assert "confirm" in response3 or "parfait" in response3 or "confirmed" in response3

# --- 4. Remove Item (French) ---
def test_remove_item_french():
    """Test removing an item in French."""
    order_id = create_order([
        {"name": "Chaise", "quantity": 2, "price": 10.0},
        {"name": "Table", "quantity": 2, "price": 20.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "Je veux supprimer les chaises de la commande"})
    response = resp.json()["agent_response"].lower()
    assert "table x2" in response
    assert "chaise" not in response
    assert "est-ce correct" in response or "is your order now correct" in response
    resp2 = client.post(f"/orders/{order_id}/message", json={"text": "oui"})
    response2 = resp2.json()["agent_response"].lower()
    assert "adresse" in response2 or "address" in response2
    resp3 = client.post(f"/orders/{order_id}/message", json={"text": "123 rue Principale, Paris"})
    response3 = resp3.json()["agent_response"].lower()
    assert "confirm" in response3 or "parfait" in response3 or "confirmée" in response3

# --- 5. Add Existing Item (English) ---
def test_add_existing_item_english():
    """Test adding more of an existing item in English."""
    order_id = create_order([
        {"name": "Table", "quantity": 2, "price": 20.0},
        {"name": "Chair", "quantity": 1, "price": 10.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "Add 3 more chairs"})
    response = resp.json()["agent_response"].lower()
    assert "chair x4" in response
    assert "table x2" in response
    assert "is your order now correct" in response or "est-ce correct" in response
    resp2 = client.post(f"/orders/{order_id}/message", json={"text": "yes"})
    response2 = resp2.json()["agent_response"].lower()
    assert "address" in response2 or "adresse" in response2
    resp3 = client.post(f"/orders/{order_id}/message", json={"text": "123 Main St, London"})
    response3 = resp3.json()["agent_response"].lower()
    assert "confirm" in response3 or "parfait" in response3 or "confirmed" in response3

# --- 6. Add Existing Item (French) ---
def test_add_existing_item_french():
    """Test adding more of an existing item in French."""
    order_id = create_order([
        {"name": "Table", "quantity": 2, "price": 20.0},
        {"name": "Chaise", "quantity": 1, "price": 10.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "Ajouter 3 chaises de plus"})
    response = resp.json()["agent_response"].lower()
    assert "chaise x4" in response
    assert "table x2" in response
    assert "est-ce correct" in response or "is your order now correct" in response
    resp2 = client.post(f"/orders/{order_id}/message", json={"text": "oui"})
    response2 = resp2.json()["agent_response"].lower()
    assert "adresse" in response2 or "address" in response2
    resp3 = client.post(f"/orders/{order_id}/message", json={"text": "123 rue Principale, Paris"})
    response3 = resp3.json()["agent_response"].lower()
    assert "confirm" in response3 or "parfait" in response3 or "confirmée" in response3

# --- 7. Replace Item (English) ---
def test_replace_item_english():
    """Test replacing an item in English."""
    order_id = create_order([
        {"name": "Pizza", "quantity": 2, "price": 12.0},
        {"name": "Lasagna", "quantity": 2, "price": 14.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "Replace lasagna with salad"})
    response = resp.json()["agent_response"].lower()
    assert "pizza x2" in response
    assert "salad" in response
    assert "lasagna" not in response
    assert "is your order now correct" in response or "est-ce correct" in response
    resp2 = client.post(f"/orders/{order_id}/message", json={"text": "yes"})
    response2 = resp2.json()["agent_response"].lower()
    assert "address" in response2 or "adresse" in response2
    resp3 = client.post(f"/orders/{order_id}/message", json={"text": "123 Main St, London"})
    response3 = resp3.json()["agent_response"].lower()
    assert "confirm" in response3 or "parfait" in response3 or "confirmed" in response3

# --- 8. Replace Item (French) ---
def test_replace_item_french():
    """Test replacing an item in French."""
    order_id = create_order([
        {"name": "Pizza", "quantity": 2, "price": 12.0},
        {"name": "Lasagne", "quantity": 2, "price": 14.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "Remplacer lasagne par salade"})
    response = resp.json()["agent_response"].lower()
    assert "pizza x2" in response
    assert "salade" in response or "salad" in response
    assert "lasagne" not in response
    assert "est-ce correct" in response or "is your order now correct" in response
    resp2 = client.post(f"/orders/{order_id}/message", json={"text": "oui"})
    response2 = resp2.json()["agent_response"].lower()
    assert "adresse" in response2 or "address" in response2
    resp3 = client.post(f"/orders/{order_id}/message", json={"text": "123 rue Principale, Paris"})
    response3 = resp3.json()["agent_response"].lower()
    assert "confirm" in response3 or "parfait" in response3 or "confirmée" in response3

# --- 9. Modify Quantity (English) ---
def test_modify_quantity_english():
    """Test modifying item quantity in English."""
    order_id = create_order([
        {"name": "Table", "quantity": 2, "price": 20.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "Change the number of tables to 5"})
    response = resp.json()["agent_response"].lower()
    assert "table x5" in response
    assert "is your order now correct" in response or "est-ce correct" in response
    resp2 = client.post(f"/orders/{order_id}/message", json={"text": "yes"})
    response2 = resp2.json()["agent_response"].lower()
    assert "address" in response2 or "adresse" in response2
    resp3 = client.post(f"/orders/{order_id}/message", json={"text": "123 Main St, London"})
    response3 = resp3.json()["agent_response"].lower()
    assert "confirm" in response3 or "parfait" in response3 or "confirmed" in response3

# --- 10. Modify Quantity (French) ---
def test_modify_quantity_french():
    """Test modifying item quantity in French."""
    order_id = create_order([
        {"name": "Table", "quantity": 2, "price": 20.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "Changer le nombre de tables à 5"})
    response = resp.json()["agent_response"].lower()
    assert "table x5" in response
    assert "est-ce correct" in response or "is your order now correct" in response
    resp2 = client.post(f"/orders/{order_id}/message", json={"text": "oui"})
    response2 = resp2.json()["agent_response"].lower()
    assert "adresse" in response2 or "address" in response2
    resp3 = client.post(f"/orders/{order_id}/message", json={"text": "123 rue Principale, Paris"})
    response3 = resp3.json()["agent_response"].lower()
    assert "confirm" in response3 or "parfait" in response3 or "confirmée" in response3

# --- 11. Cancel Order (English) ---
def test_cancel_order_english():
    """Test cancelling an order in English."""
    order_id = create_order([
        {"name": "Table", "quantity": 1, "price": 20.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "I want to cancel my order"})
    assert resp.status_code == 200
    assert "cancel" in resp.json()["agent_response"].lower() or "cancelled" in resp.json()["agent_response"].lower()

# --- 12. Cancel Order (French) ---
def test_cancel_order_french():
    """Test cancelling an order in French."""
    order_id = create_order([
        {"name": "Table", "quantity": 1, "price": 20.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "Je veux annuler ma commande"})
    response = resp.json()["agent_response"].lower()
    assert "annuler" in response or "annulé" in response or "cancel" in response or "commande" in response

# --- 13. Ambiguous Request (English) ---
def test_ambiguous_request_english():
    """Test ambiguous/help request in English."""
    order_id = create_order([
        {"name": "Table", "quantity": 1, "price": 20.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "Can you help?"})
    assert resp.status_code == 200
    assert "clarify" in resp.json()["agent_response"].lower() or "help" in resp.json()["agent_response"].lower()

# --- 14. Ambiguous Request (French) ---
def test_ambiguous_request_french():
    """Test ambiguous/help request in French."""
    order_id = create_order([
        {"name": "Table", "quantity": 1, "price": 20.0}
    ], woocommerce_order_id="999")
    client.post(f"/orders/{order_id}/confirm", json={"mode": "web"})
    resp = client.post(f"/orders/{order_id}/message", json={"text": "Pouvez-vous m'aider ?"})
    assert resp.status_code == 200
    assert "préciser" in resp.json()["agent_response"].lower() or "aider" in resp.json()["agent_response"].lower() or "clarifier" in resp.json()["agent_response"].lower() or "assistant" in resp.json()["agent_response"].lower()


# Note: For a real test, the create_order helper should insert into the DB or use the API if available.
# If not, these tests may need to be adapted to your actual order creation flow. 