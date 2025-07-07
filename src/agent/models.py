import json
from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict
from datetime import datetime

class OrderItem(BaseModel):
    name: str
    quantity: int
    price: float
    notes: Optional[str] = None

class Order(BaseModel):
    id: str
    customer_name: str
    customer_phone: str
    items: List[OrderItem]
    total_amount: float
    status: str = "pending"  # pending, confirmed, cancelled
    created_at: str
    confirmed_at: Optional[str] = None
    notes: Optional[str] = None

    @validator('items', pre=True)
    def parse_items(cls, v):
        if isinstance(v, str):
            return [OrderItem(**item) for item in json.loads(v)]
        return v

class ConversationState(BaseModel):
    order_id: str
    messages: List[Dict[str, str]]
    current_step: str = "greeting"  # greeting, confirming_items, confirming_details, final_confirmation
    confirmed_items: List[Dict] = []
    issues_found: List[str] = []
    modification_request: Optional[Dict] = None
    last_active: datetime = Field(default_factory=datetime.utcnow) 