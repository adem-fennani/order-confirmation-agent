import os
from dotenv import load_dotenv

# Dynamically import the real Twilio client only if needed
try:
    from twilio.rest import Client
    TWILIO_SDK_AVAILABLE = True
except ImportError:
    TWILIO_SDK_AVAILABLE = False

load_dotenv()

# Check if we should use the mock service
USE_MOCK = os.getenv('USE_MOCK_SMS', 'false').lower() == 'true'

# Initialize real client only if not using mock and SDK is available
client = None
if not USE_MOCK and TWILIO_SDK_AVAILABLE:
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    if account_sid and auth_token:
        client = Client(account_sid, auth_token)
    else:
        print("WARNING: Twilio credentials not found. Real SMS sending will fail.")

def send_sms(to_number: str, message: str):
    """
    Sends an SMS using either the real Twilio client or a mock service.
    
    The behavior is controlled by the USE_MOCK_SMS environment variable.
    - If USE_MOCK_SMS is 'true', it uses the mock service.
    - Otherwise, it uses the real Twilio service.
    """
    
    # Proceed with the real Twilio service
    if not client or not TWILIO_SDK_AVAILABLE:
        error_msg = "Twilio SDK not installed or client not configured. Cannot send real SMS."
        print(f"ERROR: {error_msg}")
        raise RuntimeError(error_msg)
        
    twilio_phone_number = os.environ['TWILIO_PHONE_NUMBER']
    
    try:
        message = client.messages.create(
            body=message,
            from_=twilio_phone_number,
            to=to_number
        )
        print(f"Successfully sent SMS via Twilio. SID: {message.sid}")
        return {"sid": message.sid}
    except Exception as e:
        print(f"ERROR: Failed to send SMS via Twilio: {e}")
        # Propagate the error to be handled by the API route
        raise e
