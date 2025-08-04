# src/agent/database/sqlite.py
from typing import Dict, Optional, Any, List
from datetime import datetime
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .models import Base, OrderModel, ConversationModel, BusinessUser
from src.api.schemas import OrderItem
from .base import DatabaseInterface
from sqlalchemy import select, delete

from sqlalchemy import create_engine

class SQLiteDatabase(DatabaseInterface):
    def __init__(self, db_url="sqlite+aiosqlite:///orders.db?check_same_thread=False", sync_db_url="sqlite:///orders.db"):
        self.async_engine = create_async_engine(db_url)
        self.sync_engine = create_engine(sync_db_url)
        self.AsyncSession = sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.SyncSession = sessionmaker(bind=self.sync_engine)

    def get_session(self):
        return self.SyncSession()

    async def create_order(self, order_data: Dict) -> None:
        async with self.AsyncSession() as session:
            order_data['created_at'] = datetime.fromisoformat(order_data['created_at'])
            order = OrderModel(**order_data)
            session.add(order)
            await session.commit()

    async def get_order(self, order_id: str) -> Optional[Dict]:
        async with self.AsyncSession() as session:
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
                    "notes": order.notes,
                    "business_id": order.business_id,
                    "site_url": order.site_url,
                    "site_id": order.site_id
                }
        return None

    async def update_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        async with self.AsyncSession() as session:
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

    async def get_order_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get the most recent active order for a given phone number."""
        async with self.AsyncSession() as session:
            result = await session.execute(select(OrderModel).filter(
                OrderModel.customer_phone == phone_number,
                OrderModel.status == 'pending'
            ).order_by(OrderModel.id.desc()))
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
                    "notes": order.notes,
                    "business_id": order.business_id,
                    "site_url": order.site_url,
                    "site_id": order.site_id
                }
        return None

    async def get_conversation(self, order_id: str) -> Optional[Dict]:
        async with self.AsyncSession() as session:
            result = await session.execute(select(ConversationModel).filter_by(order_id=order_id))
            conv = result.scalars().first()
            if conv:
                # Try to load pending_address if present (backward compatible)
                pending_address = getattr(conv, 'pending_address', None)
                try:
                    # If stored as a JSON in notes or elsewhere
                    if hasattr(conv, 'notes') and conv.notes:
                        notes_data = json.loads(conv.notes)
                        pending_address = notes_data.get('pending_address', pending_address)
                except Exception:
                    pass
                return {
                    "order_id": conv.order_id,
                    "messages": json.loads(conv.messages),
                    "current_step": conv.current_step,
                    "confirmed_items": json.loads(conv.confirmed_items),
                    "issues_found": json.loads(conv.issues_found),
                    "pending_address": pending_address
                }
        return None

    async def update_conversation(self, order_id: str, conversation: Dict) -> bool:
        async with self.AsyncSession() as session:
            result = await session.execute(select(ConversationModel).filter_by(order_id=order_id))
            conv = result.scalars().first()
            if conv:
                # Update existing
                conv.messages = json.dumps(conversation["messages"])
                conv.current_step = conversation["current_step"]
                conv.confirmed_items = json.dumps(conversation.get("confirmed_items", []))
                conv.issues_found = json.dumps(conversation.get("issues_found", []))
                # Persist pending_address in notes as JSON
                notes_data = {}
                try:
                    if conv.notes:
                        notes_data = json.loads(conv.notes)
                except Exception:
                    notes_data = {}
                notes_data["pending_address"] = conversation.get("pending_address")
                conv.notes = json.dumps(notes_data)
            else:
                # Create new
                notes_data = {"pending_address": conversation.get("pending_address")}
                new_conv = ConversationModel(
                    order_id=order_id,
                    messages=json.dumps(conversation["messages"]),
                    current_step=conversation["current_step"],
                    confirmed_items=json.dumps(conversation.get("confirmed_items", [])),
                    issues_found=json.dumps(conversation.get("issues_found", [])),
                    notes=json.dumps(notes_data)
                )
                session.add(new_conv)
            await session.commit()
            return True

    async def delete_conversation(self, order_id: str) -> bool:
        """Delete conversation for an order"""
        async with self.AsyncSession() as session:
            await session.execute(delete(ConversationModel).filter_by(order_id=order_id))
            await session.commit()
            return True

    async def get_all_orders(self) -> list[Dict]:
        """Get all orders from the database."""
        async with self.AsyncSession() as session:
            result = await session.execute(select(OrderModel))
            db_orders = result.scalars().all()
            orders = []
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
                    "items": [OrderItem(**item) for item in items],
                    "total_amount": order.total_amount,
                    "status": order.status,
                    "created_at": order.created_at.isoformat(),
                    "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
                    "notes": order.notes,
                    "business_id": order.business_id,
                    "site_url": order.site_url,
                    "site_id": order.site_id
                })
            return orders

    async def get_business_user_by_username(self, username: str) -> Optional[BusinessUser]:
        async with self.AsyncSession() as session:
            result = await session.execute(select(BusinessUser).filter_by(username=username))
            return result.scalars().first()

    async def get_business_user_by_api_key(self, api_key: str) -> Optional[BusinessUser]:
        async with self.AsyncSession() as session:
            result = await session.execute(select(BusinessUser).filter_by(api_key=api_key))
            return result.scalars().first()

    async def get_orders_by_business_id(self, business_id: str, skip: int = 0, limit: int = 10) -> List[Dict]:
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(OrderModel)
                .filter_by(business_id=business_id)
                .offset(skip)
                .limit(limit)
            )
            db_orders = result.scalars().all()
            orders = []
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
                    "items": [OrderItem(**item) for item in items],
                    "total_amount": order.total_amount,
                    "status": order.status,
                    "created_at": order.created_at.isoformat(),
                    "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
                    "notes": order.notes,
                    "business_id": order.business_id,
                    "site_url": order.site_url,
                    "site_id": order.site_id
                })
            return orders

    async def get_order_by_business_id(self, order_id: str, business_id: str) -> Optional[Dict]:
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(OrderModel)
                .filter_by(id=order_id, business_id=business_id)
            )
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
                    "items": [OrderItem(**item) for item in items],
                    "total_amount": order.total_amount,
                    "status": order.status,
                    "created_at": order.created_at.isoformat(),
                    "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
                    "notes": order.notes,
                    "business_id": order.business_id,
                    "site_url": order.site_url,
                    "site_id": order.site_id
                }
        return None