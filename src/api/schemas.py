from pydantic import BaseModel
from typing import List, Optional
from src.agent.models import OrderItem

class CreateOrder(BaseModel):
    customer_name: str
    customer_phone: str
    items: List[OrderItem]
    total_amount: float
    notes: Optional[str] = None 