# main.py - Order Confirmation Agent Core
import json
from src.agent.database.sqlite import SQLiteDatabase
from src.agent.database.models import OrderModel
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import re
from fastapi.staticfiles import StaticFiles
import os

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
    last_active: datetime = Field(default_factory=datetime.utcnow)

# Order Confirmation Agent
class OrderConfirmationAgent:
    def __init__(self, db: SQLiteDatabase): 
        self.db = db
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self._get_dynamic_system_prompt()),
            ("human", "{user_input}")
        ])
    
    def _get_dynamic_system_prompt(self) -> str:
        """Generate a dynamic system prompt based on time of day"""
        hour = datetime.now().hour
        greeting = "Bonne journée" if 6 <= hour < 18 else "Bonsoir"
        
        time_based_tone = ""
        if 6 <= hour < 9:
            time_based_tone = "Sois concis et direct, les clients sont probablement pressés le matin."
        elif 9 <= hour < 12:
            time_based_tone = "Sois professionnel mais amical."
        elif 12 <= hour < 14:
            time_based_tone = "Sois efficace, c'est l'heure du déjeuner."
        elif 14 <= hour < 18:
            time_based_tone = "Sois plus détendu et conversationnel."
        else:
            time_based_tone = "Sois courtois et concis, c'est le soir."
        
        return f"""Tu es un agent de confirmation de commande professionnel et sympathique. {greeting}!
        Ton rôle est de confirmer les détails d'une commande avec le client.
        
        Règles importantes:
        - {time_based_tone}
        - Adapte ton ton à l'humeur du client
        - Reformule clairement les détails de la commande
        - Pose des questions de clarification si nécessaire
        - Confirme chaque élément un par un si la commande est complexe
        - Demande confirmation finale avant de valider
        - Si le client veut modifier quelque chose, note-le clairement
        
        Contexte de la commande:
        {{order_context}}
        
        Étape actuelle: {{current_step}}
        Historique de conversation: {{conversation_history}}
        """
    
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
        
        # Check for conversation timeout (1 hour inactivity)
        if (datetime.utcnow() - conversation.last_active).seconds > 3600:
            # Create summary of conversation progress
            summary = f"nous confirmions votre commande {order_id}"
            if conversation.current_step == "confirming_items":
                summary = "nous vérifiions les articles de votre commande"
            elif conversation.current_step == "confirming_details":
                summary = "nous confirmions vos informations de livraison"
            elif conversation.current_step == "final_confirmation":
                summary = "nous étions sur le point de finaliser votre commande"
            
            return (
                "Nous reprenons notre conversation après une pause. "
                f"Pour rappel, {summary}.\n\n"
                "Voici un rappel de votre commande:\n"
                f"{self._format_order_context(order).split('Statut:')[0]}\n"
                "Comment puis-je vous aider ?"
            )
        
        # Add user message to conversation
        conversation.messages.append({"role": "user", "content": user_input})
        
        # Update last active timestamp
        conversation.last_active = datetime.utcnow()
        
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
        # Use sliding window with more context
        context_messages = messages[-10:]  # Increase context window
        # Add summary of earlier conversation if exists
        if len(messages) > 10:
            summary = f"[Résumé: Conversation commencée il y a {len(messages)} messages]\n"
        else:
            summary = ""
        history = [f"{'Client' if msg['role'] == 'user' else 'Agent'}: {msg['content']}" 
                  for msg in context_messages]
        return summary + "\n".join(history)
    
    def _analyze_sentiment(self, text: str) -> float:
        # Simple sentiment analysis (could be replaced with ML model)
        positive_words = ["merci", "parfait", "super", "content"]
        negative_words = ["fâché", "mécontent", "déçu", "insatisfait"]
        score = 0
        for word in positive_words:
            if word in text.lower():
                score += 1
        for word in negative_words:
            if word in text.lower():
                score -= 1
        return score

    def _generate_response(self, order_context: str, current_step: str, 
                          conversation_history: str, user_input: str) -> str:
        """Generate response based on current context with more natural transitions and better edge case handling"""
        sentiment = self._analyze_sentiment(user_input)
        if sentiment <= -1:
            return "Je m'excuse pour ce désagrément. Comment puis-je vous aider à résoudre ce problème ?"
        
        user_input_lower = user_input.lower()
        # Handle interruptions at any step
        if any(word in user_input_lower for word in ["annuler", "stop", "arrêter"]):
            return "Voulez-vous vraiment annuler la confirmation de commande ?"

        # Extract customer name and order time from order_context
        customer_name = None
        order_time = None
        match = re.search(r"Client: (.+)", order_context)
        if match:
            customer_name = match.group(1).strip()
        else:
            customer_name = "client"
        # Try to extract time from order_context (format: 2025-07-05T14:23:00 or similar)
        time_match = re.search(r"(\d{2}:\d{2})", order_context)
        time_str = time_match.group(1) if time_match else ""

        if current_step == "greeting":
            if "modifier" in user_input_lower:
                return self._handle_modification_request(order_context)
            return f"Bonjour {customer_name}! Je vous appelle pour confirmer votre commande. {order_context.split('Articles:')[1].split('Total:')[0]} pour un total de {order_context.split('Total: ')[1].split('€')[0]}€. Est-ce que ces informations sont correctes ?"
        elif current_step == "confirming_items":
            if not self._is_clear_confirmation(user_input):
                return ("Je ne suis pas certain d'avoir bien compris. "
                        "Pouvez-vous préciser si les articles mentionnés sont corrects "
                        "ou s'il y a des modifications à apporter ?")
            if any(word in user_input_lower for word in ["oui", "correct", "ok", "d'accord"]):
                return "Parfait ! Pouvez-vous me confirmer votre nom et votre adresse de livraison ?"
            elif any(word in user_input_lower for word in ["non", "incorrect", "erreur", "changer", "modifier"]):
                return self._handle_modification_request(order_context)
            else:
                return "Je ne suis pas sûr de comprendre. Pouvez-vous me dire si les articles de votre commande sont corrects ?"
        elif current_step == "confirming_details":
            return "Merci pour ces informations. Je récapitule : votre commande sera livrée sous 30 minutes. Confirmez-vous cette commande ?"
        elif current_step == "final_confirmation":
            if any(word in user_input_lower for word in ["oui", "confirme", "ok", "d'accord"]):
                # Update order status to confirmed
                self.db.update_order(
                    order_id=order_context.split('Commande ID: ')[1].split('\n')[0],
                    updates={"status": "confirmed", "confirmed_at": datetime.utcnow().isoformat()})
                return "Parfait ! Votre commande est confirmée. Vous recevrez un SMS de confirmation. Merci et à bientôt !"
        else:
            # Update order status to cancelled if they say no
            self.db.update_order(
                order_id=order_context.split('Commande ID: ')[1].split('\n')[0],
                updates={"status": "cancelled"}
            )
            return "Très bien, votre commande est annulée. N'hésitez pas à nous recontacter. Bonne journée !"
        return "Je ne suis pas sûr de comprendre. Pouvez-vous répéter ?"

    def _is_clear_confirmation(self, text: str) -> bool:
        positive = ["oui", "correct", "ok", "d'accord", "exact", "parfait"]
        negative = ["non", "incorrect", "erreur", "changer", "modifier"]
        text_lower = text.lower()
        return any(word in text_lower for word in positive + negative)

    def _handle_modification_request(self, order_context: str) -> str:
        """Handle a user's request to modify the order."""
        return ("Je peux vous aider à modifier votre commande. "
                "Quel article souhaitez-vous modifier ?\n"
                "Voici les articles actuels :\n"
                f"{order_context.split('Articles:')[1].split('Total:')[0]}")
    
    def _determine_next_step(self, current_step: str, user_input: str, response: str) -> str:
        step_transitions = {
            "greeting": "confirming_items",
            "confirming_items": "confirming_details",
            "confirming_details": "final_confirmation",
            "final_confirmation": "completed"
        }
        return step_transitions.get(current_step, current_step)
    
    def reset_conversation(self, order_id: str) -> str:
        """Completely reset a conversation"""
        # Delete existing conversation
        self.db.delete_conversation(order_id)
        
        # Create fresh conversation state
        conversation = ConversationState(
            order_id=order_id,
            messages=[],
            current_step="greeting",
            last_active=datetime.utcnow()
        )
        self.db.update_conversation(order_id, conversation.dict())
        
        # Process initial greeting
        order_data = self.db.get_order(order_id)
        if not order_data:
            return "Commande non trouvée"
            
        order = Order(**order_data)
        order_context = self._format_order_context(order)
        
        return (
            "Conversation réinitialisée. " +
            self._generate_response(
                order_context,
                "greeting",
                "Pas d'historique",
                "Bonjour"
            )
        )

# FastAPI App
app = FastAPI(title="Order Confirmation Agent API", version="1.0.0")

# Serve static files from the 'src/web' directory at /static
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../web"), html=True), name="static")

# Redirect / to /static/index.html
@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

# CORS: allow frontend served from same origin (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = SQLiteDatabase()
agent = OrderConfirmationAgent(db)

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

@app.delete("/orders/{order_id}")
async def delete_order(order_id: str):
    """Delete an order from the database by ID"""
    with db.Session() as session:
        order = session.query(OrderModel).filter_by(id=order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        session.delete(order)
        session.commit()
    # Optionally, also delete conversation if you store it elsewhere
    db.delete_conversation(order_id) if hasattr(db, 'delete_conversation') else None
    return {"id": order_id, "status": "deleted"}

@app.put("/orders/{order_id}")
async def update_order(order_id: str, order: dict = Body(...)):
    """Update an order in the database by ID"""
    with db.Session() as session:
        db_order = session.query(OrderModel).filter_by(id=order_id).first()
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        # Update fields
        db_order.customer_name = order.get("customer_name", db_order.customer_name)
        db_order.customer_phone = order.get("customer_phone", db_order.customer_phone)
        db_order.items = order.get("items", db_order.items)
        db_order.total_amount = order.get("total_amount", db_order.total_amount)
        db_order.status = order.get("status", db_order.status)
        db_order.notes = order.get("notes", db_order.notes)
        session.commit()
    return {"id": order_id, "status": "updated"}

@app.post("/orders/{order_id}/reset")
async def reset_conversation(order_id: str):
    """Reset conversation for an order"""
    try:
        with db.Session() as session:
            order = session.query(OrderModel).filter_by(id=order_id).first()
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
        
        # Delete existing conversation
        if hasattr(db, 'delete_conversation'):
            db.delete_conversation(order_id)
        
        # Create fresh conversation state
        conversation = ConversationState(
            order_id=order_id,
            messages=[],
            current_step="greeting",
            last_active=datetime.utcnow()
        )
        db.update_conversation(order_id, conversation.dict())
        
        # Process the automatic "Bonjour" from user
        user_message = {"role": "user", "content": "Bonjour"}
        conversation.messages.append(user_message)
        
        # Generate agent response
        order_data = db.get_order(order_id)
        order = Order(**order_data)
        order_context = agent._format_order_context(order)
        agent_response = agent._generate_response(
            order_context,
            "greeting",
            "Pas d'historique",
            "Bonjour"
        )
        
        # Update conversation
        conversation.messages.append({"role": "assistant", "content": agent_response})
        conversation.current_step = "confirming_items"
        db.update_conversation(order_id, conversation.dict())
        
        return {
            "order_id": order_id,
            "user_message": "Bonjour",
            "agent_response": agent_response,
            "status": "conversation_reset"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la réinitialisation: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)