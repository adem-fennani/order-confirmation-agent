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
        
    messaging_service_sid = os.getenv('TWILIO_MESSAGING_SERVICE_SID')
    twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')

    if not messaging_service_sid and not twilio_phone_number:
        raise ValueError("Either TWILIO_MESSAGING_SERVICE_SID or TWILIO_PHONE_NUMBER must be set in .env")

    # Prepare arguments for the Twilio client
    create_args = {
        'body': message,
        'to': to_number
    }

    # Use Messaging Service SID if available, otherwise use the 'from' number
    if messaging_service_sid:
        create_args['messaging_service_sid'] = messaging_service_sid
        sender_info = f"Messaging Service SID: {messaging_service_sid}"
    else:
        if not twilio_phone_number:
            raise ValueError("TWILIO_PHONE_NUMBER must be set in .env if no Messaging Service SID is provided")
        create_args['from_'] = twilio_phone_number
        sender_info = f"From Number: {twilio_phone_number}"

    try:
        twilio_message = client.messages.create(**create_args)
        print(f"Successfully sent SMS via Twilio using {sender_info}. SID: {twilio_message.sid}")
        return {"sid": twilio_message.sid}
    except Exception as e:
        print(f"ERROR: Failed to send SMS via Twilio: {e}")
        # Propagate the error to be handled by the API route
        raise e
