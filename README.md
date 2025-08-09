# Order Confirmation Agent

## Overview

Order Confirmation Agent is a modern, AI-powered system for confirming customer orders. It features a browser extension to automatically detect purchases from e-commerce sites (like Facebook Marketplace and WooCommerce) and initiates a confirmation flow via Facebook Messenger, web chat, or SMS. The system leverages FastAPI, a Chrome Extension, and Google Generative AI to provide a seamless, multilingual (French/English) conversational experience for order validation, modification, and final confirmation. It also includes a Business Admin Panel for businesses to manage their orders and API keys.

---

## Core Workflow

1.  **Business Setup**: A business owner registers and gets an API key and a site ID from the Business Admin Panel.
2.  **Order Detection**: A browser extension, running on sites like Facebook Marketplace or WooCommerce, automatically scrapes order details upon checkout completion.
3.  **Order Creation**: The extension sends the scraped data to the backend API, which creates a new order in the database.
4.  **Automated Confirmation**: Upon order creation, the agent automatically sends a confirmation message to the user via Facebook Messenger.
5.  **Conversational Agent**: The user interacts with the AI agent on Messenger to confirm, modify, or cancel their order.
6.  **Status Update**: The order status is updated in the database based on the conversation outcome.
7.  **Admin Notification**: The order appears in the business owner's admin panel.

---

## Features

- **Automated Order Detection**: A browser extension automatically captures order details from e-commerce confirmation pages (Facebook Marketplace and WooCommerce).
- **Facebook Messenger Integration**: Proactively sends order confirmation messages and handles the conversation on Messenger.
- **AI-Powered Dialogues**: Uses Google Generative AI for natural, context-aware, multilingual (French/English) conversations.
- **Multi-channel Support**: Also supports confirmation via a web interface and SMS (Twilio).
- **Order Management**: A web UI to view, manage, and interact with all orders and conversations.
- **Business Admin Panel**: A dedicated panel for businesses to manage their orders, API keys, and sites.
- **Persistent Storage**: Uses a SQLite database to store all order and conversation data.
- **Extensible & Modular**: Cleanly separates the agent logic, API, external services, and the browser extension.

---

## Project Structure

```
order-confirmation-agent/
├── config/               # Configuration files
├── docs/                 # Documentation
├── scripts/              # Utility scripts
├── src/
│   ├── main.py           # FastAPI app entry point
│   ├── agent/            # Core agent logic
│   ├── api/              # FastAPI endpoints and schemas
│   ├── extension/        # Browser extension source
│   ├── services/         # External services (AI, Twilio, Facebook)
│   └── web/              # Frontend for order management UI
│       ├── admin/        # Business Admin Panel
│       └── internal/     # Internal web interface
├── tests/                # Test scripts
├── requirements.txt      # Python dependencies
└── README.md
```

---

## Installation & Setup

### Prerequisites

- Python 3.11+
- A Chrome-based browser
- A Facebook Page and a Facebook Developer App
- `ngrok` for local webhook testing

### Steps

1.  **Clone the repository**
    ```bash
    git clone https://github.com/adem-fennani/order-confirmation-agent.git
    cd order-confirmation-agent
    ```
2.  **Create a virtual environment & install dependencies**
    ```bash
    python -m venv venv
    source venv/bin/activate   # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```
3.  **Configure environment variables**
    Create a `.env` file in the `config` directory. See `docs/SETUP.md` for detailed instructions on getting Facebook credentials.

    ```
    # Google AI
    GOOGLE_API_KEY=...

    # Facebook Messenger
    FACEBOOK_VERIFY_TOKEN=...        # A secret token of your choice
    FACEBOOK_PAGE_ACCESS_TOKEN=...   # From your Facebook App
    FACEBOOK_PSID=...                # The user's Page-Scoped ID to send messages to

    # (Optional) Twilio for SMS
    TWILIO_ACCOUNT_SID=...
    TWILIO_AUTH_TOKEN=...
    TWILIO_PHONE_NUMBER=...
    ```

4.  **Run the backend server**
    ```bash
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
    ```
5.  **Load the Browser Extension**

    - Open Chrome and navigate to `chrome://extensions`.
    - Enable "Developer mode".
    - Click "Load unpacked" and select the `src/extension` directory.
    - Click the extension icon, go to "Settings", and enter your name and phone number.

6.  **Configure Facebook Webhook**
    - Run ngrok to expose your local server: `ngrok http 8000`
    - In your Facebook App's Messenger settings, set the webhook URL to `https://<your-ngrok-subdomain>.ngrok.io/api/v1/facebook/webhook` and use the `FACEBOOK_VERIFY_TOKEN` you created.

---

## Usage

1.  With the backend server running, navigate to a test order page (e.g., `http://localhost:8080/test_order.html` served locally).
2.  The browser extension will automatically detect the order and send it to the backend.
3.  The backend creates the order and immediately sends a confirmation message to the user specified by `FACEBOOK_PSID` in your `.env` file.
4.  Open Facebook Messenger to interact with the agent and complete the confirmation.
5.  Visit the web UI (`http://localhost:8000`) to see the order status update in real-time.

---

## Business Admin Panel

The Business Admin Panel allows businesses to manage their orders, API keys, and sites.

-   **URL**: `http://localhost:8000/static/admin/admin.html`
-   **Features**:
    -   Login with username and password.
    -   View all orders for the business.
    -   View order details and conversation history.
    -   Get API key for the browser extension.
    -   Register new WooCommerce sites.

---

## Scripts

The `scripts` directory contains utility scripts for managing the application.

-   `create_test_orders.py`: Creates test orders in the database.
-   `create_test_user.py`: Creates a test user in the database.
-   `delete_test_orders.py`: Deletes test orders from the database.
-   `migration.py`: Applies database migrations.
-   `show_db_data.py`: Shows the data in the database.
-   `test_api.py`: Tests the API endpoints.
-   `update_user_and_orders.py`: Updates user and order data.

---

## API Endpoints (Summary)

| Method | Endpoint                        | Description                                      |
| ------ | ------------------------------- | ------------------------------------------------ |
| GET    | /orders                         | List all orders                                  |
| POST   | /orders                         | Create a new order (used by the extension)       |
| POST   | /orders/{order_id}/message      | Send a message to the agent for a specific order |
| GET    | /orders/{order_id}/conversation | Get the conversation history for an order        |
| GET    | /api/v1/facebook/webhook        | Verifies the Facebook webhook                    |
| POST   | /api/v1/facebook/webhook        | Handles incoming messages from Messenger         |
| POST   | /api/business/login             | Authenticate business user                       |
| GET    | /api/business/orders            | Get all orders for authenticated business        |
| GET    | /api/business/orders/{order_id} | Get specific order details                       |
| GET    | /api/business/api-key           | Get API key for authenticated business           |
| POST   | /api/orders/submit              | Submit confirmed order from WooCommerce          |


---

## Environment Variables

| Variable                   | Description                                              |
| -------------------------- | -------------------------------------------------------- |
| GOOGLE_API_KEY             | Your Google Generative AI API key.                       |
| FACEBOOK_VERIFY_TOKEN      | A secret token you create for webhook verification.      |
| FACEBOOK_PAGE_ACCESS_TOKEN | The access token for your Facebook Page.                 |
| FACEBOOK_PSID              | The Page-Scoped ID of the user to send test messages to. |
| TWILIO_ACCOUNT_SID         | (Optional) Twilio Account SID for SMS functionality.     |
| TWILIO_AUTH_TOKEN          | (Optional) Twilio Auth Token for SMS functionality.      |
| TWILIO_PHONE_NUMBER        | (Optional) Your Twilio phone number for sending SMS.     |

---

## Contributing

Contributions are welcome! Please fork the repository and open a pull request with your changes.

---

## License

This project is licensed under the MIT License.