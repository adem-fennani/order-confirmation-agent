# src/agent/database/sqlite.py
from typing import Dict, Optional, Any
from datetime import datetime
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, OrderModel, ConversationModel
from .base import DatabaseInterface

class SQLiteDatabase(DatabaseInterface):
    def __init__(self, db_url="sqlite:///orders.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def create_order(self, order_data: Dict) -> None:
        with self.Session() as session:
            order_data['created_at'] = datetime.fromisoformat(order_data['created_at'])
            order = OrderModel(**order_data)
            session.add(order)
            session.commit()
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        with self.Session() as session:
            order = session.query(OrderModel).filter_by(id=order_id).first()
            if order:
                items = order.items
                if isinstance(items, str):
                    try:
                        items = json.loads(items)
                    except Exception:
                        items = []
                return {
                    "id": order.id,
                    "customer_name": order.customer_name,
                    "customer_phone": order.customer_phone,
                    "items": items,
                    "total_amount": order.total_amount,
                    "status": order.status,
                    "created_at": order.created_at.isoformat(),
                    "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
                    "notes": order.notes
                }
        return None
    
    def update_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        with self.Session() as session:
            order = session.query(OrderModel).filter_by(id=order_id).first()
            if order:
                for key, value in updates.items():
                    if key == "confirmed_at" and isinstance(value, str):
                        setattr(order, key, datetime.fromisoformat(value))
                    else:
                        setattr(order, key, value)
                session.commit()
                return True
        return False
    
    def get_conversation(self, order_id: str) -> Optional[Dict]:
        with self.Session() as session:
            conv = session.query(ConversationModel).filter_by(order_id=order_id).first()
            if conv:
                return {
                    "order_id": conv.order_id,
                    "messages": json.loads(conv.messages),
                    "current_step": conv.current_step,
                    "confirmed_items": json.loads(conv.confirmed_items),
                    "issues_found": json.loads(conv.issues_found)
                }
        return None
    
    def update_conversation(self, order_id: str, conversation: Dict) -> bool:
        with self.Session() as session:
            conv = session.query(ConversationModel).filter_by(order_id=order_id).first()
            if conv:
                # Update existing
                conv.messages = json.dumps(conversation["messages"])
                conv.current_step = conversation["current_step"]
                conv.confirmed_items = json.dumps(conversation.get("confirmed_items", []))
                conv.issues_found = json.dumps(conversation.get("issues_found", []))
            else:
                # Create new
                new_conv = ConversationModel(
                    order_id=order_id,
                    messages=json.dumps(conversation["messages"]),
                    current_step=conversation["current_step"],
                    confirmed_items=json.dumps(conversation.get("confirmed_items", [])),
                    issues_found=json.dumps(conversation.get("issues_found", []))
                )
                session.add(new_conv)
            session.commit()
            return True

    def delete_conversation(self, order_id: str) -> bool:
        """Delete conversation for an order"""
        with self.Session() as session:
            conv = session.query(ConversationModel).filter_by(order_id=order_id).first()
            if conv:
                session.delete(conv)
                session.commit()
                return True
        return False