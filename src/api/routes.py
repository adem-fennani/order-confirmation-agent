from fastapi import APIRouter, HTTPException, Body, Depends
from typing import List, Optional
from src.agent.models import OrderItem, Order, ConversationState
from src.agent.database.models import OrderModel
from src.api.schemas import CreateOrder
from src.api.dependencies import get_db, get_agent
import uuid
from datetime import datetime
import json

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
        order_data = {
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
    initial_response = agent.process_message(order_id, "Bonjour")
    return {
        "order_id": order_id,
        "message": initial_response,
        "status": "confirmation_started"
    }

@router.post("/orders/{order_id}/message")
async def send_message(order_id: str, message: dict, agent=Depends(get_agent)):
    user_input = message.get("text", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="Message text is required")
    response = agent.process_message(order_id, user_input)
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
        with db.Session() as session:
            order = session.query(OrderModel).filter_by(id=order_id).first()
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            order.status = "pending"  # type: ignore
            order.confirmed_at = None  # type: ignore
            if hasattr(db, 'delete_conversation'):
                db.delete_conversation(order_id)
            conversation = ConversationState(
                order_id=order_id,
                messages=[],
                current_step="greeting",
                last_active=datetime.utcnow()
            )
            db.update_conversation(order_id, conversation.dict())
            user_message = {"role": "user", "content": "Bonjour"}
            conversation.messages.append(user_message)
            order_data = db.get_order(order_id)
            if not order_data:
                raise HTTPException(status_code=404, detail="Order not found")
            if not isinstance(order_data, dict):
                order_data = {
                    "id": order_data.id,
                    "customer_name": order_data.customer_name,
                    "customer_phone": order_data.customer_phone,
                    "items": order_data.items,
                    "total_amount": order_data.total_amount,
                    "status": order_data.status,
                    "created_at": order_data.created_at,
                    "confirmed_at": order_data.confirmed_at,
                    "notes": order_data.notes
                }
            order_obj = Order(**order_data)
            order_context = agent._format_order_context(order_obj)
            agent_response = agent._generate_response(
                order_context,
                "greeting",
                "Pas d'historique",
                "Bonjour"
            )
            conversation.messages.append({"role": "assistant", "content": agent_response})
            conversation.current_step = "confirming_items"
            db.update_conversation(order_id, conversation.dict())
            session.commit()
            return {
                "order_id": order_id,
                "user_message": "Bonjour",
                "agent_response": agent_response,
                "status": "conversation_reset"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la réinitialisation: {str(e)}") 