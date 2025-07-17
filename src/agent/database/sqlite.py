# src/agent/database/sqlite.py
from typing import Dict, Optional, Any
from datetime import datetime
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .models import Base, OrderModel, ConversationModel
from .base import DatabaseInterface
from sqlalchemy import select, delete

class SQLiteDatabase(DatabaseInterface):
    def __init__(self, db_url="sqlite+aiosqlite:///orders.db"):
        self.engine = create_async_engine(db_url)
        self.Session = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def create_order(self, order_data: Dict) -> None:
        async with self.Session() as session:
            order_data['created_at'] = datetime.fromisoformat(order_data['created_at'])
            order = OrderModel(**order_data)
            session.add(order)
            await session.commit()

    async def get_order(self, order_id: str) -> Optional[Dict]:
        async with self.Session() as session:
            result = await session.execute(select(OrderModel).filter_by(id=order_id))
            order = result.scalars().first()
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

    async def update_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        async with self.Session() as session:
            result = await session.execute(select(OrderModel).filter_by(id=order_id))
            order = result.scalars().first()
            if order:
                for key, value in updates.items():
                    if key == "confirmed_at" and isinstance(value, str):
                        setattr(order, key, datetime.fromisoformat(value))
                    else:
                        setattr(order, key, value)
                await session.commit()
                return True
        return False

    async def get_conversation(self, order_id: str) -> Optional[Dict]:
        async with self.Session() as session:
            result = await session.execute(select(ConversationModel).filter_by(order_id=order_id))
            conv = result.scalars().first()
            if conv:
                return {
                    "order_id": conv.order_id,
                    "messages": json.loads(conv.messages),
                    "current_step": conv.current_step,
                    "confirmed_items": json.loads(conv.confirmed_items),
                    "issues_found": json.loads(conv.issues_found)
                }
        return None

    async def update_conversation(self, order_id: str, conversation: Dict) -> bool:
        async with self.Session() as session:
            result = await session.execute(select(ConversationModel).filter_by(order_id=order_id))
            conv = result.scalars().first()
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
            await session.commit()
            return True

    async def delete_conversation(self, order_id: str) -> bool:
        """Delete conversation for an order"""
        async with self.Session() as session:
            await session.execute(delete(ConversationModel).filter_by(order_id=order_id))
            await session.commit()
            return True