import json
from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class AgentState(Enum):
    GREETING = "greeting"
    CONFIRMING_ITEMS = "confirming_items"
    CONFIRMING_ADDRESS = "confirming_address"
    CONFIRMING_DETAILS = "confirming_details"
    FINAL_CONFIRMATION = "final_confirmation"
    ORDER_CONFIRMED = "order_confirmed"
    COMPLETED = "completed"

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
    delivery_address: Optional[str] = None  # Added for delivery address confirmation step

    @validator('items', pre=True)
    def parse_items(cls, v):
        if isinstance(v, str):
            return [OrderItem(**item) for item in json.loads(v)]
        return v

class ConversationState(BaseModel):
    order_id: str
    messages: List[Dict[str, str]]
    current_step: str = "greeting"  # greeting, confirming_items, confirming_address, confirming_details, final_confirmation
    confirmed_items: List[Dict] = []
    issues_found: List[str] = []
    modification_request: Optional[Dict] = None
    last_modification: Optional[tuple] = None
    pending_address: Optional[str] = None  # Persist delivery address being confirmed
    last_active: datetime = Field(default_factory=datetime.utcnow)

class Message(BaseModel):
    role: str  # 'user' or 'agent'
    content: str