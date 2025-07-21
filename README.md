# Order Confirmation Voice Agent

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

| Function         | Technology / Tool            |
| ---------------- | ---------------------------- |
| Voice Interface  | Twilio Voice or local        |
| Backend API      | Python + FastAPI             |
| AI Agent         | LangChain (prompt + memory)  |
| LLM              | Google Generative AI         |
| Database         | SQLite                       |
| Web Interface    | HTML, CSS, JavaScript        |

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
- `PUT /orders/{order_id}`: Update an existing order.
- `POST /orders/{order_id}/reset`: Reset the conversation for a specific order.

---

## Project Structure

```
.
├───src/
│   ├───main.py             # FastAPI application entry point
│   ├───agent/              # Order confirmation agent logic
│   │   ├───agent.py        # Agent implementation (LangChain, LLM)
│   │   ├───models.py       # Data models (Pydantic)
│   │   └───database/       # Database management
│   │       ├───sqlite.py   # SQLite implementation
│   │       └───models.py   # SQLAlchemy models
│   ├───api/                # API routes definition
│   │   ├───routes.py       # FastAPI routes
│   │   ├───schemas.py      # Validation schemas (Pydantic)
│   │   └───dependencies.py # FastAPI dependencies (DB, Agent)
│   ├───services/           # External services (LLM, TTS, STT)
│   │   └───ai_service.py   # AI models integration
│   └───web/                # Static files for web interface
│       ├───index.html      # User interface
│       ├───script.js       # Frontend JavaScript logic
│       └───style.css       # CSS styles
├───tests/                  # Unit and integration tests
├───config/                 # Configuration files
├───docs/                   # Additional documentation
├───requirements.txt        # Python dependencies
├───README.md               # This file
└───.env                    # Environment file
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
