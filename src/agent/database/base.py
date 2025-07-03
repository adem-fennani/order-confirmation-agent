# src/agent/database/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any  # Added Any import
from pydantic import BaseModel

class DatabaseInterface(ABC):
    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:  # Fixed type annotation
        pass
    
    @abstractmethod
    def update_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def get_conversation(self, order_id: str) -> Optional[Dict[str, Any]]:  # Fixed
        pass
    
    @abstractmethod
    def update_conversation(self, order_id: str, conversation: Dict[str, Any]) -> bool:  # Fixed
        pass