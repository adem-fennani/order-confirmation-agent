from fastapi import APIRouter, HTTPException, Body, Depends, Form, Response, Request
from typing import List, Optional, Dict
from src.agent.models import OrderItem, Order, ConversationState, Message
from src.agent.database.models import OrderModel, BusinessUser
from src.api.schemas import CreateOrder, OrderSubmission, Order as OrderSchema
from src.api.dependencies import get_db_interface, get_agent, verify_api_key
from src.agent.database.base import DatabaseInterface
from src.agent.agent import OrderConfirmationAgent as Agent
import uuid
from datetime import datetime
import json
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func
from src.services.twilio_service import send_sms
from src.services.facebook_service import FacebookService
from twilio.twiml.messaging_response import MessagingResponse
import os

router = APIRouter()

@router.get("/orders")
async def get_orders(db=Depends(get_db_interface), skip: int = 0, limit: int = 10):
    orders = []
    async with db.AsyncSession() as session:
        
        # Get total count
        count_result = await session.execute(select(func.count(OrderModel.id)))
        total_count = count_result.scalar_one()

        # Get paginated orders
        result = await session.execute(select(OrderModel).order_by(OrderModel.created_at.desc()).offset(skip).limit(limit))
        db_orders = result.scalars().all()
        
        for order in db_orders:
            items = order.items
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except Exception:
                    items = []
            
            conversation = await db.get_conversation(order.id)
            
            orders.append({
                "id": order.id,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "items": items,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at,
                "confirmed_at": order.confirmed_at,
                "notes": order.notes,
                "conversation": conversation['messages'] if conversation else []
            })
    return {"orders": orders, "total_count": total_count}

@router.get("/orders/{order_id}")
async def get_order(order_id: str, db=Depends(get_db_interface)):
    async with db.AsyncSession() as session:
        result = await session.execute(select(OrderModel).filter_by(id=order_id))
        order = result.scalars().first()
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

@router.post("/orders/{order_id}/confirm")
async def start_confirmation(
    order_id: str,
    payload: dict = Body(...),
    db: DatabaseInterface = Depends(get_db_interface),
    agent: Agent = Depends(get_agent)
):
    """Starts a confirmation conversation in either 'web' or 'sms' mode."""
    mode = payload.get("mode", "web")

    # Get the order details
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Start the conversation with the agent to get the initial message
    initial_response = await agent.start_conversation(order_id, language="fr")

    # If in SMS mode, send the initial message via SMS
    if mode == "sms":
        customer_phone = order.get("customer_phone")
        if not customer_phone:
            raise HTTPException(status_code=400, detail="Customer phone number is missing for SMS mode.")
        try:
            send_sms(to_number=customer_phone, message=initial_response)
        except Exception as e:
            # If SMS fails, we should still proceed, but log the error.
            print(f"ERROR: Failed to send initial confirmation SMS to {customer_phone}: {e}")
    elif mode == "messenger":
        # Hardcoded PSID for now
        PSID = "24195304350131271"
        facebook_service = FacebookService()
        try:
            await facebook_service.send_message(recipient_id=PSID, message_text=initial_response)
        except Exception as e:
            print(f"ERROR: Failed to send initial confirmation Messenger message to {PSID}: {e}")

    # Return the response to the frontend for both modes
    return {
        "order_id": order_id,
        "message": initial_response,
        "status": "confirmation_started"
    }

@router.post("/orders/{order_id}/message")
async def send_message(order_id: str, message: dict, agent=Depends(get_agent)):
    from langdetect import detect
    user_input = message.get("text", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="Message text is required")
    try:
        language = detect(user_input)
    except Exception:
        language = "fr"  # Default to French if detection fails
    response = await agent.process_message(order_id, user_input, language=language)
    return {
        "order_id": order_id,
        "user_message": user_input,
        "agent_response": response
    }

@router.get("/orders/{order_id}/conversation")
async def get_conversation(order_id: str, db=Depends(get_db_interface)):
    conversation = await db.get_conversation(order_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation": conversation}

@router.post("/orders")
async def create_order(order: CreateOrder, db=Depends(get_db_interface), agent: Agent = Depends(get_agent)):
    order_id = f"order_{str(uuid.uuid4())[:8]}"
    now = datetime.utcnow()
    async with db.AsyncSession() as session:
        new_order = OrderModel(
            id=order_id,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            items=[item.dict() for item in order.items],
            total_amount=order.total_amount,
            status="pending",
            created_at=now,
            confirmed_at=None,
            notes=order.notes
        )
        session.add(new_order)
        await session.commit()

    # Automatically trigger the confirmation message
    try:
        initial_response = await agent.start_conversation(order_id, language="fr")
        # Hardcoded PSID for now
        PSID = os.environ.get("FACEBOOK_PSID")
        facebook_service = FacebookService()
        await facebook_service.send_message(recipient_id=PSID, message_text=initial_response)
    except Exception as e:
        print(f"ERROR: Failed to send initial confirmation Messenger message to {PSID}: {e}")

    return {"id": order_id, "status": "created"}

@router.post("/orders/webhook")
async def woocommerce_webhook(
    request: Request,
    db: DatabaseInterface = Depends(get_db_interface),
    agent: Agent = Depends(get_agent)
):
    """Handle WooCommerce webhook for new orders"""
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        print(f"DEBUG: Received webhook body: {body_str}")

        # Check for WooCommerce test webhook
        if "webhook_id=1" in body_str:
            print("INFO: Received WooCommerce test webhook. Returning success.")
            return {"status": "test_webhook_received"}

        if not body_str:
            print("INFO: Received empty webhook request. Likely a test from WooCommerce.")
            return {"status": "empty_request"}

        webhook_data = json.loads(body_str)
        
        print(f"DEBUG: Received WooCommerce webhook: {webhook_data}")
        
        # Extract order information from WooCommerce format
        order_id = f"woo_order_{webhook_data.get('id')}"
        customer_name = f"{webhook_data.get('billing', {}).get('first_name', '')} {webhook_data.get('billing', {}).get('last_name', '')}"
        customer_phone = webhook_data.get('billing', {}).get('phone', '')
        customer_email = webhook_data.get('billing', {}).get('email', '')
        
        shipping_info = webhook_data.get('shipping', {})
        delivery_address = ", ".join(filter(None, [
            shipping_info.get('address_1'),
            shipping_info.get('address_2'),
            shipping_info.get('city'),
            shipping_info.get('state'),
            shipping_info.get('postcode'),
            shipping_info.get('country')
        ]))
        
        # Convert WooCommerce line items to your format
        items = []
        for item in webhook_data.get('line_items', []):
            items.append({
                "name": item.get('name'),
                "quantity": item.get('quantity'),
                "price": float(item.get('price', 0)),
                "total": float(item.get('total', 0))
            })
        
        total_amount = float(webhook_data.get('total', 0))
        
        # Create order in your system
        new_order_data = {
            "id": order_id,
            "customer_name": customer_name.strip(),
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "items": items,
            "total_amount": total_amount,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "confirmed_at": None,
            "notes": f"WooCommerce Order #{webhook_data.get('id')}",
            "delivery_address": delivery_address, # Add this line
            "woocommerce_order_id": webhook_data.get('id'),  # Store original WooCommerce ID
            "site_url": "ai-agent-test.local"  # Your local WooCommerce site
        }
        
        await db.create_order(new_order_data)
        
        print(f"DEBUG: Created order in system: {order_id}")
        
        # Trigger AI agent conversation
        try:
            initial_response = await agent.start_conversation(order_id, language="fr")
            
            # Send via Messenger (using your existing logic)
            PSID = os.environ.get("FACEBOOK_PSID")
            if PSID:
                facebook_service = FacebookService()
                await facebook_service.send_message(recipient_id=PSID, message_text=initial_response)
                print(f"DEBUG: Sent Messenger message to {PSID}")
                
        except Exception as e:
            print(f"ERROR: Failed to send initial confirmation message: {e}")
        
        return {"status": "success", "order_id": order_id}
        
    except Exception as e:
        print(f"ERROR processing WooCommerce webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")

@router.post("/orders/submit", response_model=OrderSchema)
async def submit_order(
    order_data: OrderSubmission,
    business_user: BusinessUser = Depends(verify_api_key),
    db: DatabaseInterface = Depends(get_db_interface),
    agent: Agent = Depends(get_agent)
):
    order_id = f"order_{str(uuid.uuid4())[:8]}"
    now = datetime.utcnow()

    print(f"DEBUG: items before OrderModel: {order_data.order_data.items}")
    new_order_data = {
        "id": order_id,
        "customer_name": order_data.customer_info.customer_name,
        "customer_phone": order_data.customer_info.customer_phone,
        "items": [item.dict() for item in order_data.order_data.items],
        "total_amount": order_data.order_data.total_amount,
        "status": "pending",
        "created_at": now.isoformat(),
        "confirmed_at": None,
        "notes": order_data.order_data.notes,
        "business_id": business_user.business_id,
        "site_url": order_data.site_url,
        "site_id": order_data.site_id
    }
    await db.create_order(new_order_data)

    # Create an OrderSchema instance for the response
    response_order = OrderSchema(
        id=order_id,
        customer_name=order_data.customer_info.customer_name,
        customer_phone=order_data.customer_info.customer_phone,
        items=order_data.order_data.items,
        total_amount=order_data.order_data.total_amount,
        status="pending",
        created_at=now,
        confirmed_at=None,
        notes=order_data.order_data.notes,
        business_id=business_user.business_id,
        site_url=order_data.site_url,
        site_id=order_data.site_id
    )

    # Automatically trigger the confirmation message
    PSID = os.environ.get("FACEBOOK_PSID") # Ensure PSID is always defined
    try:
        initial_response = await agent.start_conversation(order_id, language="fr")
        # Hardcoded PSID for now
        facebook_service = FacebookService()
        await facebook_service.send_message(recipient_id=PSID, message_text=initial_response)
    except Exception as e:
        print(f"ERROR: Failed to send initial confirmation Messenger message to {PSID}: {e}")

    return response_order

@router.delete("/orders/{order_id}")
async def delete_order(order_id: str, db=Depends(get_db_interface)):
    async with db.AsyncSession() as session:
        result = await session.execute(select(OrderModel).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        await session.delete(order)
        await session.commit()
    await db.delete_conversation(order_id)
    return {"id": order_id, "status": "deleted"}

@router.put("/orders/{order_id}")
async def update_order(order_id: str, order: dict = Body(...), db=Depends(get_db_interface)):
    async with db.AsyncSession() as session:
        result = await session.execute(select(OrderModel).filter_by(id=order_id))
        db_order = result.scalars().first()
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        db_order.customer_name = order.get("customer_name", db_order.customer_name)
        db_order.customer_phone = order.get("customer_phone", db_order.customer_phone)
        db_order.items = order.get("items", db_order.items)
        db_order.total_amount = order.get("total_amount", db_order.total_amount)
        db_order.status = order.get("status", db_order.status)
        db_order.notes = order.get("notes", db_order.notes)
        await session.commit()
    return {"id": order_id, "status": "updated"}

@router.post("/orders/{order_id}/reset")
async def reset_conversation(order_id: str, db=Depends(get_db_interface), agent=Depends(get_agent)):
    try:
        result = await agent.reset_conversation(order_id)
        return jsonable_encoder(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la réinitialisation: {str(e)}") 

# --- Test SMS endpoint ---
@router.post("/test-sms", include_in_schema=False)
async def send_test_sms():
    """Send a test SMS to the number specified in VERIFIED_TEST_NUMBER env var."""
    to_number = os.getenv("VERIFIED_TEST_NUMBER")
    if not to_number:
        raise HTTPException(status_code=400, detail="VERIFIED_TEST_NUMBER env var not set")
    try:
        send_sms(to_number=to_number, message="Test")
        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sms-webhook")
async def sms_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: DatabaseInterface = Depends(get_db_interface),
    agent: Agent = Depends(get_agent)
):
    """Handle incoming SMS messages from Twilio and reply with TwiML."""
    customer_phone = From
    incoming_msg_text = Body

    # Find the most recent pending order for the customer's phone number
    order = await db.get_order_by_phone(customer_phone)

    # Prepare a TwiML response
    twiml_response = MessagingResponse()

    if not order or order.get("status") != "pending":
        # If no pending order is found, log it and send a polite generic message.
        print(f"Webhook received from {customer_phone} but no pending order found.")
        twiml_response.message("Désolé, je ne trouve aucune commande en attente de confirmation pour ce numéro.")
    else:
        # If a pending order is found, process the message with the agent
        order_id = order['id']
        agent_response = await agent.process_message(order_id, incoming_msg_text)
        
        # Add the agent's reply to the TwiML response
        twiml_response.message(agent_response)

    # Return the TwiML response to Twilio
    return Response(content=str(twiml_response), media_type="application/xml")