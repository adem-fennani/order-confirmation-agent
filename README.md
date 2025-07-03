# Agent Vocal de Confirmation de Commande

## Description du projet

Ce projet vise à créer un prototype d’agent vocal (ou textuel) capable de :

- Recevoir une commande client (depuis WhatsApp ou un formulaire web).
- Contacter ou répondre au client pour confirmer les détails de la commande.
- Reformuler la commande, poser des questions de validation.
- Confirmer la commande et mettre à jour une base de données simulée.

L’objectif est de simuler un assistant vocal intelligent qui interagit avec les clients afin d’assurer la bonne prise en compte de leurs commandes.

---

## Fonctionnalités principales

- **Réception des commandes** : via messages WhatsApp ou formulaire web.
- **Transcription vocale** : utilisation de Whisper pour convertir la voix en texte.
- **Analyse intelligente** : LangChain pour reformuler, questionner et valider la commande.
- **Synthèse vocale** : ElevenLabs ou Coqui pour répondre vocalement au client.
- **Interface d’échange** : via Twilio (en production) ou en mode local (micro/casque).
- **Base de données simulée** : stockage des commandes confirmées dans un fichier JSON ou SQLite.
- **Interaction** : confirmation de commande par appel vocal ou chat.

---

## Technologies & outils utilisés

| Fonction         | Technologie / Outil           |
| ---------------- | ----------------------------- |
| Speech-to-Text   | Whisper                       |
| Text-to-Speech   | ElevenLabs ou Coqui           |
| Interface vocale | Twilio Voice ou local         |
| Backend API      | Python + FastAPI (ou Node.js) |
| Agent IA         | LangChain (prompt + mémoire)  |
| Orchestration    | Flowise ou CrewAI (optionnel) |
| Base de données  | JSON ou SQLite (mockée)       |

---

## Installation et configuration

### Prérequis

- Python 3.11+
- pip
- (Optionnel) Compte Twilio avec numéro vocal configuré
- Clés API ElevenLabs (pour TTS)
- Accès à Whisper (local ou API)

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
   ELEVENLABS_API_KEY=xxxxxxx
   ```

5. (Optionnel) Préparer la base de données simulée (`orders.json` ou SQLite).

---

## Utilisation

### Lancer le serveur backend

```bash
uvicorn main:app --reload
```
