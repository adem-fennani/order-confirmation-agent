from fastapi import APIRouter, HTTPException, Body, Depends, Form, Response
from typing import List, Optional, Dict
from src.agent.models import OrderItem, Order, ConversationState, Message
from src.agent.database.models import OrderModel
from src.api.schemas import CreateOrder
from src.api.dependencies import get_db, get_agent
from src.agent.database.base import DatabaseInterface
from src.agent.agent import OrderConfirmationAgent as Agent
import uuid
from datetime import datetime
import json
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from src.services.twilio_service import send_sms
import os

router = APIRouter()

@router.get("/orders")
async def get_orders(db=Depends(get_db)):
    orders = []
    async with db.Session() as session:
        result = await session.execute(select(OrderModel))
        db_orders = result.scalars().all()
        for order in db_orders:
            items = order.items
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except Exception:
                    items = []
            orders.append({
                "id": order.id,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "items": items,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at,
                "confirmed_at": order.confirmed_at,
                "notes": order.notes
            })
    return {"orders": orders}

@router.get("/orders/{order_id}")
async def get_order(order_id: str, db=Depends(get_db)):
    async with db.Session() as session:
        result = await session.execute(select(OrderModel).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        items = order.items
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except Exception:
                items = []
        return {
            "order": {
                "id": order.id,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "items": items,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at,
                "confirmed_at": order.confirmed_at,
                "notes": order.notes
            }
        }

@router.post("/orders/{order_id}/confirm")
async def start_confirmation(order_id: str, db: DatabaseInterface = Depends(get_db), agent: Agent = Depends(get_agent)):
    # Get the customer's phone number from the order
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    customer_phone = order.get("customer_phone")

    # Start the conversation with the agent to get the initial message
    initial_response = await agent.start_conversation(order_id, language="fr")

    # Send the initial message via SMS
    try:
        send_sms(to_number=customer_phone, message=initial_response)
    except Exception as e:
        # If SMS fails, we should still proceed to show the conversation in the UI,
        # but log the error.
        print(f"ERROR: Failed to send initial confirmation SMS to {customer_phone}: {e}")

    # Return the response to the frontend
    return {
        "order_id": order_id,
        "message": initial_response,
        "status": "confirmation_started"
    }

@router.post("/orders/{order_id}/message")
async def send_message(order_id: str, message: dict, agent=Depends(get_agent)):
    from langdetect import detect
    user_input = message.get("text", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="Message text is required")
    try:
        language = detect(user_input)
    except Exception:
        language = "fr"  # Default to French if detection fails
    response = await agent.process_message(order_id, user_input, language=language)
    return {
        "order_id": order_id,
        "user_message": user_input,
        "agent_response": response
    }

@router.get("/orders/{order_id}/conversation")
async def get_conversation(order_id: str, db=Depends(get_db)):
    conversation = await db.get_conversation(order_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation": conversation}

@router.post("/orders")
async def create_order(order: CreateOrder, db=Depends(get_db)):
    order_id = f"order_{str(uuid.uuid4())[:8]}"
    now = datetime.utcnow()
    async with db.Session() as session:
        new_order = OrderModel(
            id=order_id,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            items=[item.dict() for item in order.items],
            total_amount=order.total_amount,
            status="pending",
            created_at=now,
            confirmed_at=None,
            notes=order.notes
        )
        session.add(new_order)
        await session.commit()
    return {"id": order_id, "status": "created"}

@router.delete("/orders/{order_id}")
async def delete_order(order_id: str, db=Depends(get_db)):
    async with db.Session() as session:
        result = await session.execute(select(OrderModel).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        await session.delete(order)
        await session.commit()
    await db.delete_conversation(order_id)
    return {"id": order_id, "status": "deleted"}

@router.put("/orders/{order_id}")
async def update_order(order_id: str, order: dict = Body(...), db=Depends(get_db)):
    async with db.Session() as session:
        result = await session.execute(select(OrderModel).filter_by(id=order_id))
        db_order = result.scalars().first()
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        db_order.customer_name = order.get("customer_name", db_order.customer_name)
        db_order.customer_phone = order.get("customer_phone", db_order.customer_phone)
        db_order.items = order.get("items", db_order.items)
        db_order.total_amount = order.get("total_amount", db_order.total_amount)
        db_order.status = order.get("status", db_order.status)
        db_order.notes = order.get("notes", db_order.notes)
        await session.commit()
    return {"id": order_id, "status": "updated"}

@router.post("/orders/{order_id}/reset")
async def reset_conversation(order_id: str, db=Depends(get_db), agent=Depends(get_agent)):
    try:
        result = await agent.reset_conversation(order_id)
        return jsonable_encoder(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la réinitialisation: {str(e)}") 

# --- Test SMS endpoint ---
@router.post("/test-sms", include_in_schema=False)
async def send_test_sms():
    """Send a test SMS to the number specified in VERIFIED_TEST_NUMBER env var."""
    to_number = os.getenv("VERIFIED_TEST_NUMBER")
    if not to_number:
        raise HTTPException(status_code=400, detail="VERIFIED_TEST_NUMBER env var not set")
    try:
        send_sms(to_number=to_number, message="Test")
        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sms-webhook")
async def sms_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: DatabaseInterface = Depends(get_db),
    agent: Agent = Depends(get_agent)
):
    """Handle incoming SMS messages from Twilio."""
    customer_phone = From
    incoming_msg_text = Body

    # 1. Find the order associated with the phone number
    order = await db.get_order_by_phone(customer_phone)

    if not order:
        # If no pending order, we can't do anything.
        # In a real app, you might send a generic "Sorry, I can't find your order" message.
        print(f"No pending order found for phone number: {customer_phone}")
        # Twilio requires a response, even if empty. A 204 No Content is appropriate.
        return Response(status_code=204)

    # 2. Pass the message to the agent and get a response
    order_id = order['id']
    agent_response = await agent.get_response(order_id, incoming_msg_text)

    # 3. Send the agent's response back to the customer
    try:
        send_sms(to_number=customer_phone, message=agent_response)
    except Exception as e:
        print(f"Failed to send reply SMS to {customer_phone}: {e}")
        # Even if sending fails, we can't raise an HTTP exception here
        # because Twilio will see it as a webhook failure.

    # 4. Return a success response to Twilio
    return Response(status_code=204)