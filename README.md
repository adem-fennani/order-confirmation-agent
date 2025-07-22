# Order Confirmation Agent

## Project Description

This project aims to create a voice agent prototype capable of:

- Receiving customer orders (from WhatsApp or a web form).
- Contacting or responding to the customer to confirm order details.
- Reformulating the order, asking validation questions.
- Confirming the order and updating a simulated database.

The objective is to simulate an intelligent voice assistant that interacts with customers to ensure proper handling of their orders.

---

## Main Features

- **Order Reception**: via WhatsApp messages or web form.
- **Intelligent Analysis**: LangChain to reformulate, question, and validate the order.
- **Exchange Interface**: via Twilio (in production) or local mode (microphone/headset).
- **Database**: storage of confirmed orders in an SQLite database.
- **Interaction**: order confirmation via voice call or chat.

---

## Technologies & Tools Used

| Function        | Technology / Tool           |
| --------------- | --------------------------- |
| Voice Interface | Twilio Voice or local       |
| Backend API     | Python + FastAPI            |
| AI Agent        | LangChain (prompt + memory) |
| LLM             | Google Generative AI        |
| Database        | SQLite                      |
| Web Interface   | HTML, CSS, JavaScript       |

---

## Project Structure

```
order-confirmation-agent/
├── .env                  # Environment variables (Twilio keys, etc.)
├── docs/
│   ├── MANUAL_TEST_CASES.md
│   └── SETUP.md
├── src/
│   ├── main.py             # FastAPI application entry point
│   ├── agent/              # Core agent logic
│   │   ├── agent.py
│   │   ├── models.py
│   │   └── database/
│   ├── api/                # FastAPI endpoints and schemas
│   │   ├── dependencies.py
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── services/           # External services (Twilio, AI)
│   │   ├── ai_service.py
│   │   └── twilio_service.py
│   └── web/                # Frontend files
│       ├── index.html
│       ├── script.js
│       └── style.css
├── tests/
├── requirements.txt
└── README.md
```

---

## Installation and Configuration

### Prerequisites

- Python 3.11+
- pip
- (Optional) Twilio account with configured voice number

### Installation Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/adem-fennani/order-confirmation-agent.git
   cd order-confirmation-agent
   ```

2. Create a Python virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux / MacOS
   venv\Scripts\activate      # Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables (example `.env`):

   ```
   TWILIO_ACCOUNT_SID=xxxxxxx
   TWILIO_AUTH_TOKEN=xxxxxxx
   GOOGLE_API_KEY=xxxxxxx
   ```

---

## Usage

### Launch the backend server

```bash
uvicorn main:app --reload
```

---

## API Endpoints

The application exposes the following API endpoints:

- `GET /orders`: Retrieve a list of all orders.
- `GET /orders/{order_id}`: Retrieve details for a specific order.
- `POST /orders`: Create a new order.
- `POST /orders/{order_id}/confirm`: Initiate the order confirmation process for a given order.
- `POST /orders/{order_id}/message`: Send a message to the agent for a specific order, triggering a response.
- `GET /orders/{order_id}/conversation`: Retrieve the conversation history for a specific order.
- `DELETE /orders/{order_id}`: Delete an order.
- `POST /sms-webhook`: Handle incoming SMS messages from Twilio.
- `POST /test-sms`: Send a test SMS to a verified number.
- `PUT /orders/{order_id}`: Update an existing order.
- `POST /orders/{order_id}/reset`: Reset the conversation for a specific order.

---

## Project Structure

```
order-confirmation-agent/
├── .env                  # Environment variables (Twilio keys, etc.)
├── docs/
│   ├── MANUAL_TEST_CASES.md
│   └── SETUP.md
├── src/
│   ├── __init__.py
│   ├── main.py             # FastAPI application entry point
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py        # Core agent logic for processing conversations
│   │   ├── models.py       # Pydantic models for orders, conversations, etc.
│   │   └── database/
│   │       ├── __init__.py
│   │       ├── base.py     # Abstract database interface
│   │       ├── models.py   # SQLAlchemy ORM models
│   │       └── sqlite.py   # SQLite database implementation
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py # FastAPI dependencies (e.g., get_db)
│   │   ├── routes.py       # All API endpoints, including the SMS webhook
│   │   └── schemas.py      # Pydantic schemas for API request/response validation
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py   # Service for calling the language model
│   │   └── twilio_service.py # Service for sending SMS via Twilio
│   └── web/
│       ├── index.html      # Frontend for viewing orders and conversations
│       ├── script.js       # Frontend JavaScript logic
│       ├── style.css       # Frontend styles
│       └── assets/
├── tests/
├── requirements.txt
├── README.md
└── ... (other config files)
```

---

## Contributing

Contributions are welcome! Please follow these steps:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/new-feature`).
3.  Make your changes and commit them (`git commit -am 'feat: add new feature'`).
4.  Push the branch (`git push origin feature/new-feature`).
5.  Create a Pull Request.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

---

## Contact

For any questions or suggestions, please contact [Adem Fennani](mailto:ademfennani7@gmail.com).
