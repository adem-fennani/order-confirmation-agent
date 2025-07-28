# Agent de Confirmation de Commande - Setup Instructions

## 📋 Vue d'ensemble

Ce prototype d'agent vocal/textuel permet de :

- Recevoir des commandes depuis une base de données mockée
- Confirmer les détails avec les clients via chat textuel
- Reformuler et valider les commandes
- Mettre à jour le statut des commandes

## 🚀 Installation and Configuration

### Prerequisites

- Python 3.11+
- A Twilio account with a configured phone number capable of sending and receiving SMS.
- An `ngrok` account to expose your local server to the internet for Twilio webhooks.

### Installation

1.  **Clone the repository and create a virtual environment**

    ```bash
    git clone https://github.com/adem-fennani/order-confirmation-agent.git
    cd order-confirmation-agent
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables**

    Create a file named `.env` in the root of the project and add your credentials. You can use the `.env.example` file as a template.

    ```
    # Twilio Credentials
    TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    TWILIO_AUTH_TOKEN="your_auth_token"
    TWILIO_PHONE_NUMBER="+15017122661"

    # Phone number for testing, must be verified in your Twilio account
    VERIFIED_TEST_NUMBER="+1234567890"

    # Google API Key for the AI service
    GOOGLE_API_KEY="AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxx"

    # Facebook Credentials
    FACEBOOK_VERIFY_TOKEN="your_very_secret_token"
    FACEBOOK_PAGE_ACCESS_TOKEN="your_page_access_token"
    ```

4.  **Run the Backend Server**

    ```bash
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
    ```

5.  **Expose Your Server with Ngrok**

    In a new terminal, run ngrok to create a public URL for your local server.

    ```bash
    ngrok http 8000
    ```

6.  **Configure Twilio Webhook**

    - Go to your Twilio phone number's configuration page.
    - Under "Messaging", find the "A MESSAGE COMES IN" section.
    - Set the webhook to the `https/` URL provided by ngrok, followed by `/sms-webhook`. For example: `https://<your-ngrok-subdomain>.ngrok.io/sms-webhook`
    - Make sure the method is set to `HTTP POST`.

7.  **Open the Web Interface**

    Open the `src/web/index.html` file in your browser to interact with the application.

## 🎯 Utilisation

### 1. Test de l'API

```bash
# Lister les commandes
curl http://localhost:8000/orders

# Démarrer une confirmation
curl -X POST http://localhost:8000/orders/order_001/confirm

# Envoyer un message
curl -X POST http://localhost:8000/orders/order_001/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Oui, c'\''est correct"}'
```

### 2. Interface Web

1. Ouvrir `index.html` dans un navigateur
2. Voir les commandes en attente dans la sidebar
3. Cliquer sur "Démarrer confirmation" pour une commande
4. Interagir avec l'agent via le chat

## 🧠 Fonctionnement de l'Agent

### Étapes de Conversation

1. **Greeting** : Présentation de la commande
2. **Confirming Items** : Validation des articles
3. **Confirming Details** : Vérification des détails client
4. **Final Confirmation** : Confirmation finale

### Exemples de Dialogue

```
Agent: Bonjour ! Je vous appelle pour confirmer votre commande.
- Pizza Margherita x2 (12.50€ chacun)
- Coca-Cola x2 (2.50€ chacun)
pour un total de 30.00€. Est-ce que ces informations sont correctes ?

Client: Oui, c'est correct

Agent: Parfait ! Pouvez-vous me confirmer votre nom et votre adresse de livraison ?

Client: Marie Dubois, 123 rue de la Paix, Paris

Agent: Merci pour ces informations. Je récapitule : votre commande sera livrée sous 30 minutes. Confirmez-vous cette commande ?

Client: Oui, je confirme

Agent: Parfait ! Votre commande est confirmée. Vous recevrez un SMS de confirmation. Merci et à bientôt !
```

## 🔮 Évolutions Prévues (Phase 2)

### Intégration Vocale

```python
# Exemple d'intégration STT/TTS
import whisper
import requests

class VoiceAgent:
    def __init__(self):
        self.stt_model = whisper.load_model("base")
        self.tts_api = "https://api.elevenlabs.io/v1/text-to-speech"

    def speech_to_text(self, audio_file):
        result = self.stt_model.transcribe(audio_file)
        return result["text"]

    def text_to_speech(self, text):
        # Intégration ElevenLabs
        pass
```

### Intégration Twilio

```python
from twilio.rest import Client
from twilio.twiml import VoiceResponse

@app.post("/webhook/voice")
async def handle_voice_call(request: Request):
    response = VoiceResponse()
    # Logique d'appel vocal
    return str(response)
```

## 🛠️ Personnalisation

### Modifier les Commandes de Test

Dans `main.py`, section `_load_sample_orders()`:

```python
sample_orders = [
    Order(
        id="order_003",
        customer_name="Votre Client",
        customer_phone="+33123456789",
        items=[
            OrderItem(name="Votre Produit", quantity=1, price=15.00)
        ],
        total_amount=15.00,
        created_at=datetime.now().isoformat()
    )
]
```

### Personnaliser les Réponses de l'Agent

Dans `main.py`, méthode `_generate_response()`:

```python
if current_step == "greeting":
    return f"Bonjour {order.customer_name} ! Je vous appelle pour..."
```

## 🔍 Debugging

### Logs du Serveur

```bash
# Démarrer avec logs détaillés
uvicorn main:app --reload --log-level debug
```

### Vérification de l'État

```bash
# Vérifier une conversation
curl http://localhost:8000/orders/order_001/conversation
```

## 📱 Extensions Possibles

### 1. Base de Données Réelle

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Remplacer MockDatabase par une vraie DB
```

### 2. Intégration WhatsApp

```python
from twilio.rest import Client

def send_whatsapp_message(to, message):
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=message,
        from_='whatsapp:+14155238886',
        to=f'whatsapp:{to}'
    )
```

### 3. Agent LLM Réel

```python
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory

def setup_llm_agent():
    llm = ChatOpenAI(temperature=0.7, model="gpt-3.5-turbo")
    memory = ConversationBufferMemory()
    # Configuration de l'agent avec LangChain
```

## 🚨 Troubleshooting

### Problème CORS

Si l'interface web ne fonctionne pas :

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Port déjà utilisé

```bash
# Changer le port
uvicorn main:app --reload --port 8001
```

## 📊 Métriques et Monitoring

### Logs des Conversations

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dans l'agent
logger.info(f"Conversation started for order {order_id}")
```

### Statistiques

```python
@app.get("/stats")
async def get_stats():
    return {
        "total_orders": len(db.orders),
        "active_conversations": len(db.conversations),
        "confirmed_orders": len([o for o in db.orders.values() if o.status == "confirmed"])
    }
```

## 🎬 Démo et Présentation

### Scénario de Démo

1. Montrer l'interface avec les commandes en attente
2. Démarrer une confirmation
3. Simuler un dialogue client-agent
4. Montrer la mise à jour du statut

### Capture d'Écran

- Interface avec liste des commandes
- Chat en cours avec l'agent
- Statut mis à jour après confirmation

## 🔄 Prochaines Étapes

1. **Phase 2** : Intégration STT/TTS
2. **Phase 3** : Connexion Twilio
3. **Phase 4** : Déploiement en production
4. **Phase 5** : Analytics et optimisation

## 📞 Support

Pour toute question ou problème :

- Vérifier les logs du serveur
- Tester l'API avec curl
- Consulter la documentation Swagger à `/docs`
