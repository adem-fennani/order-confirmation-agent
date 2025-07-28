import httpx
import os
import logging
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# It's best practice to use the latest version, but pinning to a specific version ensures stability.
FACEBOOK_GRAPH_API_VERSION = "v20.0"
FACEBOOK_GRAPH_URL = f"https://graph.facebook.com/{FACEBOOK_GRAPH_API_VERSION}"

class FacebookService:
    """
    A service to interact with the Facebook Messenger API.
    """
    def __init__(self, page_access_token: Optional[str] = None):
        """
        Initializes the FacebookService.

        Args:
            page_access_token: The Page Access Token for your Facebook App.
                               It's recommended to load this from environment variables.
        """
        self.page_access_token = page_access_token or os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
        if not self.page_access_token:
            logger.error("Facebook Page Access Token is not provided or set as an environment variable.")
            raise ValueError("Facebook Page Access Token is not provided or set as an environment variable.")
        
        self.headers = {
            "Authorization": f"Bearer {self.page_access_token}",
            "Content-Type": "application/json",
        }

    async def send_message(self, recipient_id: str, message_text: str) -> Dict[str, Any]:
        """
        Sends a text message to a specific user.

        Args:
            recipient_id: The Page-Scoped User ID (PSID) of the recipient.
            message_text: The text of the message to send.

        Returns:
            A dictionary containing the API response from Facebook.
        """
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text},
            "messaging_type": "RESPONSE",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{FACEBOOK_GRAPH_URL}/me/messages",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                logger.info(f"Successfully sent message to {recipient_id}")
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error sending Facebook message: {e.response.text}")
                return {"error": e.response.text}
            except httpx.RequestError as e:
                logger.error(f"An error occurred while requesting Facebook API: {e}")
                return {"error": str(e)}

    def parse_incoming_message(self, webhook_payload: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Parses an incoming message from the Facebook webhook payload.
        """
        if webhook_payload.get("object") == "page":
            for entry in webhook_payload.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    if "message" in messaging_event and "text" in messaging_event["message"]:
                        sender_id = messaging_event["sender"]["id"]
                        message_text = messaging_event["message"]["text"]
                        logger.info(f"Parsed message from {sender_id}: {message_text}")
                        return {
                            "sender_id": sender_id,
                            "message_text": message_text,
                        }
        return None
