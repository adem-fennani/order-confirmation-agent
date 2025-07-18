# src/agent/database/models.py
from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class OrderModel(Base):
    __tablename__ = 'orders'
    
    id = Column(String(50), primary_key=True)
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    items = Column(JSON, nullable=False)  # Stores list of items as JSON
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    delivery_address = Column(Text, nullable=True)  # Added for delivery address confirmation step

class ConversationModel(Base):
    __tablename__ = 'conversations'
    
    order_id = Column(String(50), primary_key=True)
    messages = Column(JSON, nullable=False)  # Stores chat history
    current_step = Column(String(50), default='greeting')
    confirmed_items = Column(JSON, default=[])
    issues_found = Column(JSON, default=[])
    notes = Column(Text, nullable=True)  # For storing extra JSON data like pending_address