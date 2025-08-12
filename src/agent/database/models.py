# src/agent/database/models.py
from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime
import secrets
from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from passlib.context import CryptContext

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class BusinessUser(Base):
    __tablename__ = 'business_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    business_id = Column(String(100), unique=True, nullable=False)
    api_key = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def set_password(self, password):
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    @staticmethod
    def generate_api_key():
        return secrets.token_urlsafe(32)

class OrderModel(Base):
    __tablename__ = 'orders'
    
    id = Column(String(50), primary_key=True)
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    customer_email = Column(String(100), nullable=True)
    items = Column(JSON, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    delivery_address = Column(Text, nullable=True)
    
    # New columns for Business Admin Panel
    business_id = Column(String(100), nullable=True) # Changed to nullable=True
    site_url = Column(String(255), nullable=True)
    site_id = Column(String(100), nullable=True)

class ConversationModel(Base):
    __tablename__ = 'conversations'
    
    order_id = Column(String(50), primary_key=True)
    messages = Column(JSON, nullable=False)  # Stores chat history
    current_step = Column(String(50), default='greeting')
    confirmed_items = Column(JSON, default=[])
    issues_found = Column(JSON, default=[])
    notes = Column(Text, nullable=True)  # For storing extra JSON data like pending_address