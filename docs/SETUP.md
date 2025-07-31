# Agent de Confirmation de Commande - Setup Instructions

## 📋 Vue d'ensemble

Ce document fournit les instructions détaillées pour configurer et lancer l'agent de confirmation de commande, y compris le backend, l'extension de navigateur et l'intégration avec Facebook Messenger.

## 🚀 Installation and Configuration

### Prerequisites

- Python 3.11+
- Un navigateur basé sur Chrome (Google Chrome, Brave, etc.)
- Un compte Facebook avec une Page Facebook
- Un compte développeur Facebook pour créer une application
- `ngrok` pour tester les webhooks en local

### 1. Backend Setup

1.  **Cloner le dépôt et créer un environnement virtuel**

    ```bash
    git clone https://github.com/adem-fennani/order-confirmation-agent.git
    cd order-confirmation-agent
    python -m venv venv
    source venv/bin/activate  # Sur Windows: venv\Scripts\activate
    ```

2.  **Installer les dépendances**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Configurer les variables d'environnement**

    Créez un fichier nommé `.env` à la racine du projet et ajoutez vos informations d'identification.

    ```env
    # Clé API pour le service Google Generative AI
    GOOGLE_API_KEY="AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxx"

    # Identifiants Facebook Messenger
    FACEBOOK_VERIFY_TOKEN="VOTRE_TOKEN_SECRET_PERSONNALISE"  # Créez un token secret
    FACEBOOK_PAGE_ACCESS_TOKEN="EAA..."      # Obtenu depuis votre application Facebook
    FACEBOOK_PSID="..."                      # L'ID de l'utilisateur pour envoyer des messages de test

    # (Optionnel) Identifiants Twilio pour les SMS
    TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    TWILIO_AUTH_TOKEN="your_auth_token"
    TWILIO_PHONE_NUMBER="+15017122661"
    ```

4.  **Lancer le serveur backend**

    ```bash
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
    ```

### 2. Facebook App and Page Setup

1.  **Créer une Page Facebook** si vous n'en avez pas déjà une.
2.  **Créer une App Facebook** sur le portail des développeurs Facebook (`developers.facebook.com`).
    - Sélectionnez le type d'application "Business".
3.  **Configurer le Webhook Messenger**
    - Dans le tableau de bord de votre application, ajoutez le produit "Messenger".
    - Allez dans "Messenger Platform Settings".
    - Dans la section "Webhooks", cliquez sur "Add Callback URL".
    - Lancez `ngrok http 8000` pour obtenir une URL publique.
    - L'URL de rappel sera `https://<votre-sous-domaine-ngrok>.ngrok.io/api/v1/facebook/webhook`.
    - Le "Verify Token" est la valeur de `FACEBOOK_VERIFY_TOKEN` que vous avez définie dans votre fichier `.env`.
4.  **Générer un Page Access Token**
    - Dans la section "Access Tokens", liez votre Page Facebook à votre application.
    - Cliquez sur "Generate Token" pour obtenir votre `FACEBOOK_PAGE_ACCESS_TOKEN`.
5.  **Obtenir un Page-Scoped User ID (PSID)**
    - Envoyez un message à votre Page Facebook depuis le compte utilisateur que vous utiliserez pour les tests.
    - Surveillez les logs du serveur backend. Lorsqu'un message est reçu, le `sender_id` (PSID) sera affiché. Copiez cette valeur dans la variable `FACEBOOK_PSID` de votre fichier `.env`.

### 3. Browser Extension Setup

1.  **Ouvrir Chrome** et naviguer vers `chrome://extensions`.
2.  **Activer le "Developer mode"** (Mode développeur).
3.  **Cliquer sur "Load unpacked"** (Charger l'extension non empaquetée) et sélectionner le dossier `src/extension` de ce projet.
4.  **Configurer l'extension**
    - Cliquez sur l'icône de l'extension dans la barre d'outils de Chrome.
    - Cliquez sur le bouton "Settings".
    - Entrez votre nom et votre numéro de téléphone. Ces informations seront utilisées lors de la création de commandes.

## 🎯 Utilisation et Test

1.  **Assurez-vous que votre serveur backend est en cours d'exécution.**
2.  **Servez la page de test HTML**
    - Pour simuler une page de confirmation de commande, vous pouvez utiliser un simple serveur Python.
    - Depuis le répertoire racine du projet, exécutez : `python -m http.server 8080`
3.  **Déclencher la détection de commande**
    - Ouvrez votre navigateur et allez sur `http://localhost:8080/test_order.html`.
    - L'extension de navigateur devrait automatiquement détecter les détails de la commande et les envoyer à votre backend.
4.  **Vérifier la confirmation sur Messenger**
    - Le backend créera une nouvelle commande et enverra immédiatement un message de confirmation à l'utilisateur Messenger spécifié par `FACEBOOK_PSID`.
    - Ouvrez Messenger pour interagir avec l'agent et confirmer la commande.
5.  **Consulter l'interface web**
    - Ouvrez `http://localhost:8000` dans votre navigateur pour voir la liste des commandes et observer les mises à jour de statut en temps réel.
