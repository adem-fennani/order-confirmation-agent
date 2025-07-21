from twilio.rest import Client
import os

_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
_FROM = os.getenv("TWILIO_PHONE_NUMBER")


def send_sms(to: str, body: str) -> None:
    """Send a simple SMS message via Twilio.

    Args:
        to (str): Recipient phone number in E.164 format.
        body (str): SMS body text.
    """
    if not _FROM:
        raise RuntimeError("TWILIO_PHONE_NUMBER env var not set")
    _client.messages.create(to=to, from_=_FROM, body=body)
