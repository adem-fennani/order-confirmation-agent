from fastapi import APIRouter, HTTPException, Body, Depends
from typing import List, Optional
from src.agent.models import OrderItem, Order, ConversationState
from src.agent.database.models import OrderModel
from src.api.schemas import CreateOrder
from src.api.dependencies import get_db, get_agent
import uuid
from datetime import datetime
import json
from fastapi.encoders import jsonable_encoder

router = APIRouter()

@router.get("/orders")
async def get_orders(db=Depends(get_db)):
    orders = []
    with db.Session() as session:
        db_orders = session.query(OrderModel).all()
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
    with db.Session() as session:
        order = session.query(OrderModel).filter_by(id=order_id).first()
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
async def start_confirmation(order_id: str, db=Depends(get_db), agent=Depends(get_agent)):
    # No need to fetch order_data here, just pass language (default 'fr')
    initial_response = agent.start_conversation(order_id, language="fr")
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
    response = agent.process_message(order_id, user_input, language=language)
    return {
        "order_id": order_id,
        "user_message": user_input,
        "agent_response": response
    }

@router.get("/orders/{order_id}/conversation")
async def get_conversation(order_id: str, db=Depends(get_db)):
    conversation = db.get_conversation(order_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation": conversation}

@router.post("/orders")
async def create_order(order: CreateOrder, db=Depends(get_db)):
    order_id = f"order_{str(uuid.uuid4())[:8]}"
    now = datetime.utcnow()
    with db.Session() as session:
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
        session.commit()
    return {"id": order_id, "status": "created"}

@router.delete("/orders/{order_id}")
async def delete_order(order_id: str, db=Depends(get_db)):
    with db.Session() as session:
        order = session.query(OrderModel).filter_by(id=order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        session.delete(order)
        session.commit()
    db.delete_conversation(order_id) if hasattr(db, 'delete_conversation') else None
    return {"id": order_id, "status": "deleted"}

@router.put("/orders/{order_id}")
async def update_order(order_id: str, order: dict = Body(...), db=Depends(get_db)):
    with db.Session() as session:
        db_order = session.query(OrderModel).filter_by(id=order_id).first()
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        db_order.customer_name = order.get("customer_name", db_order.customer_name)
        db_order.customer_phone = order.get("customer_phone", db_order.customer_phone)
        db_order.items = order.get("items", db_order.items)
        db_order.total_amount = order.get("total_amount", db_order.total_amount)
        db_order.status = order.get("status", db_order.status)
        db_order.notes = order.get("notes", db_order.notes)
        session.commit()
    return {"id": order_id, "status": "updated"}

@router.post("/orders/{order_id}/reset")
async def reset_conversation(order_id: str, db=Depends(get_db), agent=Depends(get_agent)):
    try:
        result = agent.reset_conversation(order_id)
        return jsonable_encoder(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la réinitialisation: {str(e)}") 