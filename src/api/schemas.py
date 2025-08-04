# src/api/schemas.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class OrderItem(BaseModel):
    name: str
    price: float
    quantity: int

class CreateOrder(BaseModel):
    customer_name: str
    customer_phone: str
    items: List[OrderItem]
    total_amount: float
    notes: Optional[str] = None

class Order(BaseModel):
    id: str
    customer_name: str
    customer_phone: str
    items: List[OrderItem]
    total_amount: float
    status: str
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    notes: Optional[str] = None
    business_id: Optional[str] = None
    site_url: Optional[str] = None
    site_id: Optional[str] = None

    class Config:
        from_attributes = True

class BusinessUserSchema(BaseModel):
    id: int
    username: str
    business_id: str
    api_key: str
    created_at: datetime

    class Config:
        from_attributes = True

class CustomerInfo(BaseModel):
    customer_name: str
    customer_phone: str

class OrderData(BaseModel):
    items: List[OrderItem]
    total_amount: float
    notes: Optional[str] = None

class OrderSubmission(BaseModel):
    site_id: str
    site_url: str
    order_data: OrderData
    customer_info: CustomerInfo