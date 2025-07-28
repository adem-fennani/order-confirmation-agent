# Order Confirmation Agent

## Overview

Order Confirmation Agent is a modern, AI-powered system for confirming customer orders via both web chat and SMS. It leverages FastAPI, Twilio, and Google Generative AI to provide a seamless, multilingual (French/English) conversational experience for order validation, modification, and confirmation.

---

## Features

- **Conversational Order Confirmation**: Interact with customers to confirm, modify, or cancel orders.
- **Web & SMS Support**: Customers can chat via a web interface or receive/respond to SMS (Twilio integration).
- **AI-Powered Dialogues**: Uses Google Generative AI (via LangChain) for natural, context-aware conversations.
- **Multilingual**: Detects and responds in French or English automatically.
- **Order Management**: Create, view, and update orders with customer details, items, and status.
- **Delivery Address Handling**: Ensures delivery address is collected and confirmed before finalizing orders.
- **Persistent Storage**: Uses SQLite for storing orders and conversation history.
- **Extensible & Modular**: Clean separation of agent logic, API, services, and database layers.

---

## Project Structure

```
order-confirmation-agent/
├── .env                  # Environment variables (Twilio, Google API, etc.)
├── docs/                 # Documentation and manual test cases
├── src/
│   ├── main.py           # FastAPI app entry point
│   ├── agent/            # Core agent logic (LLM, order, conversation)
│   │   ├── agent.py
│   │   ├── models.py
│   │   └── database/
│   │       ├── base.py
│   │       ├── models.py
│   │       └── sqlite.py
│   ├── api/              # FastAPI endpoints and schemas
│   │   ├── dependencies.py
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── services/         # External services (AI, Twilio)
│   │   ├── ai_service.py
│   │   └── twilio_service.py
│   └── web/              # Frontend (HTML, JS, CSS, assets)
│       ├── index.html
│       ├── script.js
│       ├── style.css
│       └── assets/
├── tests/                # Test scripts
├── requirements.txt      # Python dependencies
├── README.md
└── ...
```

---

## Installation & Setup

### Prerequisites

- Python 3.11+
- pip
- Twilio account with a Messaging Service (with phone number attached, SMS enabled)
- Google Generative AI API key
- ngrok account and auth token

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/adem-fennani/order-confirmation-agent.git
   cd order-confirmation-agent
   ```
2. **Create a virtual environment & install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```
   TWILIO_ACCOUNT_SID=...           # Your Twilio Account SID
   TWILIO_AUTH_TOKEN=...            # Your Twilio Auth Token
   TWILIO_PHONE_NUMBER=...          # Your Twilio phone number (E.164 format)
   TWILIO_MESSAGING_SERVICE_SID=... # Messaging Service SID (must have phone number, SMS enabled)
   VERIFIED_TEST_NUMBER=...         # For test SMS endpoint
   GOOGLE_API_KEY=...               # Google Generative AI API key
   NGROK_AUTHTOKEN=...              # Your ngrok authtoken
   USE_MOCK_SMS=false               # (Optional) Set to 'true' to disable real SMS sending
   ```
4. **Run the backend server**
   ```bash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```
   When you run the application, it will automatically create an ngrok tunnel and print the public URL to the console. You will need to use this URL to configure your Twilio webhook.

5. **Open the web interface**
   - Open `src/web/index.html` in your browser for the web chat UI.

---

## Usage

- **Web Chat**: Use the web interface to view, create, and confirm orders interactively.
- **SMS**: Customers can receive and reply to SMS for order confirmation. All SMS are handled via Twilio and the `/sms-webhook` endpoint.
- **API**: Interact programmatically with the REST API (see endpoints below).

---

## API Endpoints (Summary)

| Method | Endpoint                        | Description                              |
| ------ | ------------------------------- | ---------------------------------------- |
| GET    | /orders                         | List all orders                          |
| POST   | /orders                         | Create a new order                       |
| POST   | /orders/{order_id}/confirm      | Start confirmation (web or SMS)          |
| POST   | /orders/{order_id}/message      | Send a message to the agent for an order |
| GET    | /orders/{order_id}/conversation | Get conversation history for an order    |
| DELETE | /orders/{order_id}              | Delete an order                          |
| POST   | /sms-webhook                    | Handle incoming SMS from Twilio          |
| POST   | /test-sms                       | Send a test SMS to the verified number   |
| PUT    | /orders/{order_id}              | Update an existing order                 |
| POST   | /orders/{order_id}/reset        | Reset the conversation for an order      |

---

## Environment Variables

| Variable                     | Description                                                   |
| ---------------------------- | ------------------------------------------------------------- |
| TWILIO_ACCOUNT_SID           | Twilio Account SID                                            |
| TWILIO_AUTH_TOKEN            | Twilio Auth Token                                             |
| TWILIO_PHONE_NUMBER          | Twilio phone number (E.164)                                   |
| TWILIO_MESSAGING_SERVICE_SID | Messaging Service SID (must have phone number, SMS enabled)   |
| VERIFIED_TEST_NUMBER         | Phone number for test SMS endpoint                            |
| GOOGLE_API_KEY               | Google Generative AI API key                                  |
| USE_MOCK_SMS                 | (Optional) 'true' to disable real SMS sending (for local dev) |

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Make your changes and commit (`git commit -am 'feat: ...'`)
4. Push the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## Contact

For questions or suggestions, contact [Adem Fennani](mailto:ademfennani7@gmail.com).
