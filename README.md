# Agent Vocal de Confirmation de Commande

## Description du projet

Ce projet vise à créer un prototype d’agent vocal capable de :

- Recevoir une commande client (depuis WhatsApp ou un formulaire web).
- Contacter ou répondre au client pour confirmer les détails de la commande.
- Reformuler la commande, poser des questions de validation.
- Confirmer la commande et mettre à jour une base de données simulée.

L’objectif est de simuler un assistant vocal intelligent qui interagit avec les clients afin d’assurer la bonne prise en compte de leurs commandes.

---

## Fonctionnalités principales

- **Réception des commandes** : via messages WhatsApp ou formulaire web.
- **Analyse intelligente** : LangChain pour reformuler, questionner et valider la commande.
- **Interface d’échange** : via Twilio (en production) ou en mode local (micro/casque).
- **Base de données** : stockage des commandes confirmées dans une base de données SQLite.
- **Interaction** : confirmation de commande par appel vocal ou chat.

---

## Technologies & outils utilisés

| Fonction         | Technologie / Outil          |
| ---------------- | ---------------------------- |
| Interface vocale | Twilio Voice ou local        |
| Backend API      | Python + FastAPI             |
| Agent IA         | LangChain (prompt + mémoire) |
| LLM              | Google Generative AI         |
| Base de données  | SQLite                       |
| Interface Web    | HTML, CSS, JavaScript        |

---

## Installation et configuration

### Prérequis

- Python 3.11+
- pip
- (Optionnel) Compte Twilio avec numéro vocal configuré

### Étapes d’installation

1. Cloner le dépôt :

   ```bash
   git clone https://github.com/adem-fennani/order-confirmation-agent.git
   cd order-confirmation-agent
   ```

2. Créer un environnement virtuel Python :

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux / MacOS
   venv\Scripts\activate      # Windows
   ```

3. Installer les dépendances :

   ```bash
   pip install -r requirements.txt
   ```

4. Configurer les variables d’environnement (exemple `.env`) :

   ```
   TWILIO_ACCOUNT_SID=xxxxxxx
   TWILIO_AUTH_TOKEN=xxxxxxx
   GOOGLE_API_KEY=xxxxxxx
   ```

---

## Utilisation

### Lancer le serveur backend

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

## Structure du projet

```
.
├───src/
│   ├───main.py             # Point d'entrée de l'application FastAPI
│   ├───agent/              # Logique de l'agent de confirmation de commande
│   │   ├───agent.py        # Implémentation de l'agent (LangChain, LLM)
│   │   ├───models.py       # Modèles de données (Pydantic)
│   │   └───database/       # Gestion de la base de données
│   │       ├───sqlite.py   # Implémentation SQLite
│   │       └───models.py   # Modèles SQLAlchemy
│   ├───api/                # Définition des routes API
│   │   ├───routes.py       # Routes FastAPI
│   │   ├───schemas.py      # Schémas de validation (Pydantic)
│   │   └───dependencies.py # Dépendances FastAPI (DB, Agent)
│   ├───services/           # Services externes (LLM, TTS, STT)
│   │   └───ai_service.py   # Intégration avec les modèles d'IA
│   └───web/                # Fichiers statiques pour l'interface web
│       ├───index.html      # Interface utilisateur
│       ├───script.js       # Logique JavaScript du frontend
│       └───style.css       # Styles CSS
├───tests/                  # Tests unitaires et d'intégration
├───config/                 # Fichiers de configuration
├───docs/                   # Documentation additionnelle
├───requirements.txt        # Dépendances Python
├───README.md               # Ce fichier
└───.env                    # Fichier d'environnement
```

---

## Contribution

Les contributions sont les bienvenues ! Veuillez suivre les étapes suivantes :

1.  Fork le dépôt.
2.  Créez une nouvelle branche (`git checkout -b feature/nouvelle-fonctionnalite`).
3.  Effectuez vos modifications et commitez-les (`git commit -am 'feat: ajouter une nouvelle fonctionnalité'`).
4.  Poussez la branche (`git push origin feature/nouvelle-fonctionnalite`).
5.  Créez une Pull Request.

---

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

## Contact

Pour toute question ou suggestion, veuillez contacter [Adem Fennani](mailto:ademfennani7@gmail.com).
