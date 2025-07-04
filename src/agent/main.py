# main.py - Order Confirmation Agent Core
import json
from src.agent.database.sqlite import SQLiteDatabase
from src.agent.database.models import OrderModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import re

# Data Models
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

# Order Confirmation Agent
class OrderConfirmationAgent:
    def __init__(self, db: SQLiteDatabase): 
        self.db = db
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Tu es un agent de confirmation de commande professionnel et sympathique. 
            Ton rôle est de confirmer les détails d'une commande avec le client.
            
            Règles importantes:
            - Sois poli et professionnel
            - Reformule clairement les détails de la commande
            - Pose des questions de clarification si nécessaire
            - Confirme chaque élément un par un si la commande est complexe
            - Demande confirmation finale avant de valider
            - Si le client veut modifier quelque chose, note-le clairement
            
            Contexte de la commande:
            {order_context}
            
            Étape actuelle: {current_step}
            Historique de conversation: {conversation_history}
            """),
            ("human", "{user_input}")
        ])
    
    def process_message(self, order_id: str, user_input: str) -> str:
        """Process a message from the user and return agent response"""
        # Get order details from SQLite
        order_data = self.db.get_order(order_id)
        if not order_data:
            return "Désolé, je ne trouve pas cette commande. Pouvez-vous vérifier le numéro de commande?"
        
        # Convert to Pydantic model
        order = Order(**order_data)
        
        # Get or create conversation state
        conversation_data = self.db.get_conversation(order_id)
        if not conversation_data:
            conversation = ConversationState(
                order_id=order_id,
                messages=[],
                current_step="greeting"
            )
        else:
            conversation = ConversationState(**conversation_data)
        
        # Add user message to conversation
        conversation.messages.append({"role": "user", "content": user_input})
        
        # Prepare context
        order_context = self._format_order_context(order)
        conversation_history = self._format_conversation_history(conversation.messages)
        
        # Determine next step and generate response
        response = self._generate_response(
            order_context, 
            conversation.current_step, 
            conversation_history, 
            user_input
        )
        
        # Update conversation state
        conversation.messages.append({"role": "assistant", "content": response})
        conversation.current_step = self._determine_next_step(conversation.current_step, user_input, response)
        
        # Save conversation back to SQLite
        self.db.update_conversation(order_id, conversation.dict())
        
        return response
    
    def _format_order_context(self, order: Order) -> str:
        items_str = "\n".join([
            f"- {item.name} x{item.quantity} ({item.price}€ chacun)" 
            for item in order.items
        ])
        
        return f"""
        Commande ID: {order.id}
        Client: {order.customer_name}
        Téléphone: {order.customer_phone}
        Articles:
        {items_str}
        Total: {order.total_amount}€
        Statut: {order.status}
        """
    
    def _format_conversation_history(self, messages: List[Dict[str, str]]) -> str:
        if not messages:
            return "Pas d'historique"
        
        history = []
        for msg in messages[-4:]:  # Keep last 4 messages for context
            role = "Client" if msg["role"] == "user" else "Agent"
            history.append(f"{role}: {msg['content']}")
        
        return "\n".join(history)
    
    def _generate_response(self, order_context: str, current_step: str, 
                          conversation_history: str, user_input: str) -> str:
        """Generate response based on current context"""
        
        if current_step == "greeting":
            return f"Bonjour ! Je vous appelle pour confirmer votre commande. {order_context.split('Articles:')[1].split('Total:')[0]} pour un total de {order_context.split('Total: ')[1].split('€')[0]}€. Est-ce que ces informations sont correctes ?"
        
        elif current_step == "confirming_items":
            if any(word in user_input.lower() for word in ["oui", "correct", "ok", "d'accord"]):
                return "Parfait ! Pouvez-vous me confirmer votre nom et votre adresse de livraison ?"
            elif any(word in user_input.lower() for word in ["non", "incorrect", "erreur", "changer"]):
                return "Pas de problème ! Pouvez-vous me dire ce qui doit être modifié dans votre commande ?"
            else:
                return "Je ne suis pas sûr de comprendre. Pouvez-vous me dire si les articles de votre commande sont corrects ?"
        
        elif current_step == "confirming_details":
            return "Merci pour ces informations. Je récapitule : votre commande sera livrée sous 30 minutes. Confirmez-vous cette commande ?"
        
        elif current_step == "final_confirmation":
            if any(word in user_input.lower() for word in ["oui", "confirme", "ok", "d'accord"]):
                return "Parfait ! Votre commande est confirmée. Vous recevrez un SMS de confirmation. Merci et à bientôt !"
            else:
                return "Très bien, votre commande est annulée. N'hésitez pas à nous recontacter. Bonne journée !"
        
        return "Je ne suis pas sûr de comprendre. Pouvez-vous répéter ?"
    
    def _determine_next_step(self, current_step: str, user_input: str, response: str) -> str:
        step_transitions = {
            "greeting": "confirming_items",
            "confirming_items": "confirming_details",
            "confirming_details": "final_confirmation",
            "final_confirmation": "completed"
        }
        return step_transitions.get(current_step, current_step)

# FastAPI App
app = FastAPI(title="Order Confirmation Agent API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
db = SQLiteDatabase()
agent = OrderConfirmationAgent(db)

@app.get("/")
async def root():
    return {"message": "Order Confirmation Agent API"}

@app.get("/orders")
async def get_orders():
    """Get all orders with complete structure"""
    orders = []
    with db.Session() as session:
        db_orders = session.query(OrderModel).all()
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
                "items": items,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at,
                "confirmed_at": order.confirmed_at,
                "notes": order.notes
            })
    return {"orders": orders}

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get specific order with complete structure"""
    with db.Session() as session:
        order = session.query(OrderModel).filter_by(id=order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        items = order.items
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except Exception:
                items = []
        return {
            "order": {
                "id": order.id,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "items": items,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at,
                "confirmed_at": order.confirmed_at,
                "notes": order.notes
            }
        }

@app.post("/orders/{order_id}/confirm")
async def start_confirmation(order_id: str):
    """Start confirmation process for an order"""
    with db.Session() as session:
        order = session.query(OrderModel).filter_by(id=order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        items = order.items
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except Exception:
                items = []
        order_data = {
            "id": order.id,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "items": items,
            "total_amount": order.total_amount,
            "status": order.status,
            "created_at": order.created_at,
            "confirmed_at": order.confirmed_at,
            "notes": order.notes
        }
    # Start conversation
    initial_response = agent.process_message(order_id, "Bonjour")
    return {
        "order_id": order_id,
        "message": initial_response,
        "status": "confirmation_started"
    }

@app.post("/orders/{order_id}/message")
async def send_message(order_id: str, message: dict):
    """Send a message to the agent"""
    user_input = message.get("text", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="Message text is required")
    
    response = agent.process_message(order_id, user_input)
    return {
        "order_id": order_id,
        "user_message": user_input,
        "agent_response": response
    }

@app.get("/orders/{order_id}/conversation")
async def get_conversation(order_id: str):
    """Get conversation history"""
    conversation = db.get_conversation(order_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation": conversation}

class CreateOrder(BaseModel):
    customer_name: str
    customer_phone: str
    items: List[OrderItem]
    total_amount: float
    notes: Optional[str] = None

@app.post("/orders")
async def create_order(order: CreateOrder):
    """Add a new order to the database"""
    order_id = f"order_{str(uuid.uuid4())[:8]}"
    now = datetime.utcnow()
    with db.Session() as session:
        new_order = OrderModel(
            id=order_id,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            items=[item.dict() for item in order.items],  # Store as list, not JSON string
            total_amount=order.total_amount,
            status="pending",
            created_at=now,
            confirmed_at=None,
            notes=order.notes
        )
        session.add(new_order)
        session.commit()
    return {"id": order_id, "status": "created"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)