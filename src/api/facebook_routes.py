
from fastapi import APIRouter, Request, Response, HTTPException, Depends
import os
import logging
from src.services.facebook_service import FacebookService
from src.agent.agent import OrderConfirmationAgent
from src.api.dependencies import get_agent, get_db
from src.agent.database.base import DatabaseInterface

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# This must be a secret string you create and set in your Facebook App settings.
VERIFY_TOKEN = os.environ.get("FACEBOOK_VERIFY_TOKEN")

# Verify that required environment variables are set
if not os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN"):
    logger.warning("FACEBOOK_PAGE_ACCESS_TOKEN not set. Messenger features will be limited.")
if VERIFY_TOKEN == "YOUR_VERY_SECRET_TOKEN":
    logger.warning("Using default FACEBOOK_VERIFY_TOKEN. Please set a secure token for production.")

router = APIRouter()

@router.get("/webhook")
async def facebook_webhook_verify(request: Request):
    """
    Handles the verification GET request from Facebook to confirm the webhook.
    """
    try:
        # Log all query parameters for debugging
        params = dict(request.query_params)
        logger.info(f"Received webhook verification request with params: {params}")
        
        hub_mode = params.get("hub.mode")
        hub_verify_token = params.get("hub.verify_token")
        hub_challenge = params.get("hub.challenge")
        
        # Log detailed verification attempt
        logger.info(f"""
        Webhook Verification Attempt:
        - Mode: {hub_mode}
        - Token Match: {hub_verify_token == VERIFY_TOKEN}
        - Challenge Present: {bool(hub_challenge)}
        - Full Params: {params}
        """)
        
        # Verify all required parameters are present
        if not all([hub_mode, hub_verify_token, hub_challenge]):
            logger.error(f"Missing required parameters. Received: mode={hub_mode}, token={hub_verify_token}, challenge={hub_challenge}")
            raise HTTPException(
                status_code=400,
                detail="Missing required parameters for webhook verification"
            )
        
        # Verify the mode and token
        if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
            logger.info(f"Webhook verified successfully! Challenge: {hub_challenge}")
            # Facebook expects the challenge value as plain text
            return Response(
                content=hub_challenge,
                media_type="text/plain",
                status_code=200
            )
        
        logger.warning(f"Verification failed. Mode: {hub_mode}, Token match: {hub_verify_token == VERIFY_TOKEN}")
        raise HTTPException(
            status_code=403,
            detail="Verification token mismatch"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during webhook verification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during webhook verification"
        )

@router.post("/webhook")
async def facebook_webhook(request: Request):
    """
    Handles incoming messages and events from Facebook Messenger.
    """
    try:
        facebook_service = FacebookService()
        data = await request.json()
        logger.info(f"Received webhook payload: {data}")
        
        # Verify the request is from Facebook
        if "object" not in data:
            logger.warning("Received invalid webhook payload")
            return Response(status_code=400)
            
        # Return 200 OK for any page object to acknowledge receipt
        if data["object"] == "page":
            logger.info("Received valid page webhook")
            parsed_message = facebook_service.parse_incoming_message(data)
            
            if parsed_message:
                sender_id = parsed_message["sender_id"]
                message_text = parsed_message.get("message_text")
                if message_text:
                    logger.info(f"Received message from {sender_id}: {message_text}")
                else:
                    logger.info(f"Received event from {sender_id} with no message text.")
                
                # Send immediate acknowledgment
                try:
                    await facebook_service.send_message(
                        sender_id,
                        "Message received! I'll process it shortly."
                    )
                except Exception as e:
                    logger.error(f"Error sending acknowledgment: {e}")
            
            # Always return 200 OK to acknowledge receipt
            return Response(status_code=200)
            
        return Response(status_code=404, content="Unsupported object type")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # Still return 200 OK to prevent Facebook from retrying
        return Response(status_code=200)

@router.get("/webhook/test")
async def test_webhook():
    """
    Test endpoint to verify webhook configuration.
    """
    return {
        "status": "webhook endpoint operational",
        "verify_token": "..." + VERIFY_TOKEN[-4:] if len(VERIFY_TOKEN) > 4 else "not set",
        "page_token": "..." + os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "not set")[-4:] if os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") else "not set"
    }

@router.post("/send-test-message")
async def send_test_message(payload: dict):
    """
    Sends a test message to a specified Facebook user.
    This is for testing purposes.
    """
    recipient_id = payload.get("recipient_id")
    message = payload.get("message", "This is a test message from the Order Confirmation Agent.")

    if not recipient_id:
        raise HTTPException(status_code=400, detail="recipient_id is required.")

    facebook_service = FacebookService()
    result = await facebook_service.send_message(recipient_id, message)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return {"status": "success", "response": result}
