from .models import Order, ConversationState, OrderItem
from .database.sqlite import SQLiteDatabase
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json
import re
from difflib import get_close_matches
from src.services.ai_service import call_llm, LLMServiceError

class OrderConfirmationAgent:
    def __init__(self, db: SQLiteDatabase): 
        self.db = db
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self._get_dynamic_system_prompt()),
            ("human", "{user_input}")
        ])
    
    def _get_dynamic_system_prompt(self) -> str:
        hour = datetime.now().hour
        greeting = "Bonne journée" if 6 <= hour < 18 else "Bonsoir"
        time_based_tone = ""
        if 6 <= hour < 9:
            time_based_tone = "Sois concis et direct, les clients sont probablement pressés le matin."
        elif 9 <= hour < 12:
            time_based_tone = "Sois professionnel mais amical."
        elif 12 <= hour < 14:
            time_based_tone = "Sois efficace, c'est l'heure du déjeuner."
        elif 14 <= hour < 18:
            time_based_tone = "Sois plus détendu et conversationnel."
        else:
            time_based_tone = "Sois courtois et concis, c'est le soir."
        return f"""Tu es un agent de confirmation de commande professionnel et sympathique. {greeting}!
        Ton rôle est de confirmer les détails d'une commande avec le client.
        
        Règles importantes:
        - {time_based_tone}
        - Adapte ton ton à l'humeur du client
        - Reformule clairement les détails de la commande
        - Pose des questions de clarification si nécessaire
        - Confirme chaque élément un par un si la commande est complexe
        - Demande confirmation finale avant de valider
        - Si le client veut modifier quelque chose, note-le clairement
        
        Contexte de la commande:
        {{order_context}}
        
        Étape actuelle: {{current_step}}
        Historique de conversation: {{conversation_history}}
        """
    
    def process_message(self, order_id: str, user_input: str) -> str:
        """
        LLM-first: Try to process the message using the LLM pipeline. If it fails, fallback to the old rule-based logic.
        """
        try:
            llm_response = self.llm_process_message(order_id, user_input)
            if llm_response and isinstance(llm_response, str) and llm_response.strip():
                return llm_response
            else:
                raise ValueError("LLM returned empty or invalid response")
        except Exception as e:
            print(f"[LLM ERROR] {e}. Falling back to rule-based agent.")
            # Fallback to the old logic
            return self.process_message_basic(order_id, user_input)

    def llm_process_message(self, order_id: str, user_input: str) -> str:
        """
        New LLM-centric conversation logic. Handles all steps: greeting, confirmation, modification, etc.
        Returns the agent's response as a string. Raises on LLM or parsing failure.
        """
        order_data = self.db.get_order(order_id)
        if not order_data:
            return "Désolé, je ne trouve pas cette commande. Pouvez-vous vérifier le numéro de commande?"
        order = Order(**order_data)
        conversation_data = self.db.get_conversation(order_id)
        if not conversation_data:
            conversation = ConversationState(
                order_id=order_id,
                messages=[],
                current_step="greeting"
            )
        else:
            conversation = ConversationState(**conversation_data)
        conversation.messages.append({"role": "user", "content": user_input})
        conversation.last_active = datetime.utcnow()
        order_context = self._format_order_context(order)
        conversation_history = self._format_conversation_history(conversation.messages)
        # Improved LLM prompt with explicit instructions and examples
        prompt = f"""
Tu es un agent de confirmation de commande. Voici le contexte de la commande :
{order_context}

Historique de la conversation :
{conversation_history}

Le client a dit : "{user_input}"

Réponds avec un JSON strictement de la forme :
{{
  "message": "...",  // Ce que l'agent doit dire au client
  "action": "confirm|modify|cancel|add|remove|replace|none",  // L'action à effectuer (utilise 'none' si aucune action n'est requise)
  "modification": {{ "old_item": "...", "new_item": "...", "item": "..." }} // si applicable, sinon null
}}
Ne mets aucun texte avant ou après le JSON.

Exemples :
- Si le client dit "Non, c'est tout", réponds :
{{
  "message": "Merci, votre commande est confirmée.",
  "action": "confirm",
  "modification": null
}}
- Si le client dit "Oui", réponds :
{{
  "message": "Parfait, nous procédons à la préparation.",
  "action": "confirm",
  "modification": null
}}
- Si le client dit "Je veux ajouter Pizza x1", réponds :
{{
  "message": "Votre commande comprend maintenant également une Pizza x1. Le total de votre commande est désormais mis à jour. Avez-vous une autre commande à ajouter ?",
  "action": "add",
  "modification": {{ "item": "Pizza", "old_item": null, "new_item": null }}
}}
- Si le client dit "Je veux remplacer Lasagna par Pizza", réponds :
{{
  "message": "Lasagna a été remplacé par Pizza dans votre commande.",
  "action": "replace",
  "modification": {{ "old_item": "Lasagna", "new_item": "Pizza", "item": null }}
}}
- Si le client dit "Merci", réponds :
{{
  "message": "Merci à vous ! N'hésitez pas à nous recontacter si besoin.",
  "action": "none",
  "modification": null
}}
"""
        try:
            llm_raw = call_llm(prompt, max_tokens=256)
            print("[LLM RAW]", llm_raw)
            json_str = llm_raw.strip()
            # Replace smart quotes with standard quotes
            json_str = json_str.replace('"', '"').replace("'", "'")
            json_str = json_str.replace("'", "'")
            # Remove trailing commas before closing braces/brackets
            json_str = re.sub(r',([ \t\r\n]*[}}\]])', r'\1', json_str)
            # Remove non-breaking spaces and invisible characters
            json_str = json_str.replace('\u00A0', ' ')
            match = re.search(r'\{.*\}', json_str, re.DOTALL)
            if not match:
                raise ValueError("No JSON found in LLM output")
            cleaned_json = match.group(0)
            print("[LLM CLEANED JSON]", cleaned_json)
            data = json.loads(cleaned_json)
            # If the LLM action is confirm, update the order status
            if data.get("action") == "confirm":
                self.db.update_order(
                    order_id,
                    {
                        "status": "confirmed",
                        "confirmed_at": datetime.utcnow().isoformat()
                    }
                )
            # Handle action if needed (e.g., apply modification)
            if data.get("action") in {"modify", "replace", "remove", "add"} and data.get("modification"):
                self._apply_llm_modification(order_id, order, data["modification"], data["action"])
            # Save conversation state
            conversation.messages.append({"role": "assistant", "content": data["message"]})
            self.db.update_conversation(order_id, conversation.dict())
            return data["message"]
        except Exception as e:
            print(f"[LLM PARSE ERROR] {e}")
            raise

    def _apply_llm_modification(self, order_id, order, modification, action):
        """Apply the modification as instructed by the LLM."""
        if action in {"remove"} and modification.get("item"):
            order.items = [item for item in order.items if item.name != modification["item"]]
        elif action in {"replace", "modify"} and modification.get("old_item") and modification.get("new_item"):
            from difflib import get_close_matches
            old_item_name = modification["old_item"]
            item_names = [item.name for item in order.items]
            closest = get_close_matches(old_item_name, item_names, n=1, cutoff=0.6)
            if closest:
                for item in order.items:
                    if item.name == closest[0]:
                        item.name = modification["new_item"]
                        break
        elif action == "add" and modification.get("item"):
            order.items.append(OrderItem(
                name=modification["item"],
                quantity=1,
                price=0,  # Should be fetched from DB
                notes='Ajouté via LLM'
            ))
        self.db.update_order(order_id, {
            'items': [item.dict() if hasattr(item, 'dict') else item for item in order.items],
            'total_amount': sum(item.price * item.quantity for item in order.items)
        })

    def process_message_basic(self, order_id: str, user_input: str) -> str:
        # The old rule-based logic, unchanged. Just call the previous process_message logic here if fallback is needed.
        # For now, call the previous implementation (copy the old process_message logic here if needed).
        # This is a placeholder for the fallback.
        return "[Fallback] LLM n'a pas compris. (Ancienne logique à implémenter ici.)"

    def _format_order_context(self, order: Order) -> str:
        items_str = "\n".join([
            f"- {item.name} x{item.quantity} ({item.price}€ chacun)" 
            for item in order.items
        ])
        return f"""
        Commande ID: {order.id}
        Client: {order.customer_name}
        Téléphone: {order.customer_phone}
        Articles:
        {items_str}
        Total: {order.total_amount}€
        Statut: {order.status}
        """
    
    def _format_conversation_history(self, messages: List[Dict[str, str]]) -> str:
        context_messages = messages[-10:]
        if len(messages) > 10:
            summary = f"[Résumé: Conversation commencée il y a {len(messages)} messages]\n"
        else:
            summary = ""
        history = [f"{'Client' if msg['role'] == 'user' else 'Agent'}: {msg['content']}" 
                  for msg in context_messages]
        return summary + "\n".join(history)
    
    def _analyze_sentiment(self, text: str) -> float:
        positive_words = ["merci", "parfait", "super", "content"]
        negative_words = ["fâché", "mécontent", "déçu", "insatisfait"]
        score = 0
        for word in positive_words:
            if word in text.lower():
                score += 1
        for word in negative_words:
            if word in text.lower():
                score -= 1
        return score

    def _generate_response(self, order_context: str, current_step: str, 
                        conversation_history: str, user_input: str, conversation=None) -> Tuple[str, ConversationState]:
        print(f"[DEBUG] _generate_response: current_step={current_step}, modification_request={getattr(conversation, 'modification_request', None) if conversation else None}")
        order_id_match = re.search(r"Commande ID: (.+)", order_context)
        order_id = order_id_match.group(1).strip() if order_id_match else ""
        if not conversation:
            conversation_data = self.db.get_conversation(order_id)
            if not conversation_data:
                conversation = ConversationState(
                    order_id=order_id,
                    messages=[],
                    current_step="greeting",
                    last_active=datetime.utcnow()
                )
            else:
                conversation = ConversationState(**conversation_data)
        conversation.last_active = datetime.utcnow()
        sentiment = self._analyze_sentiment(user_input)
        if sentiment <= -1:
            return ("Je m'excuse pour ce désagrément. Comment puis-je vous aider à résoudre ce problème ?", conversation)
        user_input_lower = user_input.lower()
        if any(word in user_input_lower for word in ["annuler", "stop", "arrêter"]):
            return ("Voulez-vous vraiment annuler la confirmation de commande ?", conversation)
        customer_name = "client"
        match = re.search(r"Client: (.+)", order_context)
        if match:
            customer_name = match.group(1).strip()
        items_text = order_context.split('Articles:')[1].split('Total:')[0]
        order_items = [line.split(' x')[0].strip('- ').strip() for line in items_text.split('\n') if line.strip() and 'x' in line]
        if current_step == "greeting":
            if "modifier" in user_input_lower:
                return (self._handle_modification_request(order_context), conversation)
            return (f"Bonjour {customer_name}! Je vous appelle pour confirmer votre commande. {order_context.split('Articles:')[1].split('Total:')[0]} pour un total de {order_context.split('Total: ')[1].split('€')[0]}€. Est-ce que ces informations sont correctes ?", conversation)
        elif current_step == "confirming_items":
            if not self._is_clear_confirmation(user_input):
                return ("Je ne suis pas certain d'avoir bien compris. "
                        "Pouvez-vous préciser si les articles mentionnés sont corrects "
                        "ou s'il y a des modifications à apporter ?", conversation)
            if any(word in user_input_lower for word in ["oui", "correct", "ok", "d'accord"]):
                return ("Parfait ! Pouvez-vous me confirmer votre nom et votre adresse de livraison ?", conversation)
            elif any(word in user_input_lower for word in ["non", "incorrect", "erreur"]):
                return ("Je vois qu'il y a un problème avec votre commande. "
                        "Pouvez-vous me préciser quel article vous souhaitez modifier ou supprimer ?\n"
                        "Par exemple:\n"
                        "- 'Je veux changer la pizza en lasagne'\n"
                        "- 'Je veux supprimer les frites'", conversation)
            else:
                modification = self._parse_modification_request(user_input, order_context, order_items)
                if modification:
                    if conversation:
                        conversation.modification_request = modification
                        conversation.current_step = "modifying_items"
                    return (self._get_modification_confirmation_prompt(modification), conversation)
                return ("Je ne suis pas sûr de comprendre. Pouvez-vous me dire si les articles de votre commande sont corrects ?", conversation)
        elif current_step == "modifying_items":
            print(f"[DEBUG] _generate_response (modifying_items): modification_request={getattr(conversation, 'modification_request', None)}")
            result, conversation = self._process_modification(order_context, user_input, conversation=conversation)
            print(f"[DEBUG] _generate_response (after _process_modification): modification_request={getattr(conversation, 'modification_request', None)}")
            return (result, conversation)
        elif current_step == "confirming_details":
            return ("Merci pour ces informations. Je récapitule : votre commande sera livrée sous 30 minutes. Confirmez-vous cette commande ?", conversation)
        elif current_step == "final_confirmation":
            if any(word in user_input_lower for word in ["oui", "confirme", "ok", "d'accord"]):
                self.db.update_order(
                    order_id=order_context.split('Commande ID: ')[1].split('\n')[0],
                    updates={"status": "confirmed", "confirmed_at": datetime.utcnow().isoformat()})
                return ("Parfait ! Votre commande est confirmée. Vous recevrez un SMS de confirmation. Merci et à bientôt !", conversation)
            else:
                self.db.update_order(
                    order_id=order_context.split('Commande ID: ')[1].split('\n')[0],
                    updates={"status": "cancelled"}
                )
                return ("Très bien, votre commande est annulée. N'hésitez pas à nous recontacter. Bonne journée !", conversation)
        return ("Je ne suis pas sûr de comprendre. Pouvez-vous répéter ?", conversation)

    def _is_clear_confirmation(self, text: str) -> bool:
        positive = ["oui", "correct", "ok", "d'accord", "exact", "parfait"]
        negative = ["non", "incorrect", "erreur", "changer", "modifier"]
        text_lower = text.lower()
        return any(word in text_lower for word in positive + negative)

    def _handle_modification_request(self, order_context: str, user_input: str = "") -> str:
        items_text = order_context.split('Articles:')[1].split('Total:')[0]
        # Extract item names from items_text
        order_items = [line.split(' x')[0].strip('- ').strip() for line in items_text.split('\n') if line.strip() and 'x' in line]
        if not user_input:
            return ("Je peux vous aider à modifier votre commande. "
                    "Quel article souhaitez-vous modifier ou supprimer ?\n"
                    "Voici les articles actuels :\n"
                    f"{items_text}\n"
                    "Vous pouvez dire par exemple :\n"
                    "- 'Je veux changer le burger classique en burger végétarien'\n"
                    "- 'Je veux supprimer les frites'\n"
                    "- 'Je veux ajouter une boisson'")
        modification = self._parse_modification_request(user_input, items_text, order_items)
        if not modification:
            return ("Je n'ai pas bien compris quelle modification vous souhaitez faire. "
                    "Pouvez-vous reformuler ? Par exemple:\n"
                    "- 'Je veux changer le burger classique en burger végétarien'\n"
                    "- 'Je veux supprimer les frites'")
        conversation_data = self.db.get_conversation(order_context.split('Commande ID: ')[1].split('\n')[0])
        if conversation_data:
            conversation = ConversationState(**conversation_data)
            conversation.modification_request = modification
            conversation.current_step = "modifying_items"
            self.db.update_conversation(conversation.order_id, conversation.dict())
        return self._get_modification_confirmation_prompt(modification)

    def _parse_modification_request(self, user_input: str, items_text: str, order_items: list) -> Optional[Dict]:
        items_json = json.dumps(order_items)
        prompt = f"""
Voici la liste des articles de la commande : {items_json}
Le client a dit : \"{user_input}\"

Déduis l'intention de modification. Réponds uniquement avec un JSON strictement de la forme :
{{
  "action": "replace" | "remove" | "add" | "none",
  "old_item": "...",
  "new_item": "...",
  "item": "...",
  "raw": "..."
}}
Ne mets aucun texte avant ou après le JSON.
"""
        try:
            llm_response = call_llm(prompt, max_tokens=256)
            print("LLM RAW RESPONSE:", llm_response)  # For debugging
            json_str = llm_response.strip()
            json_str = json_str.replace("'", '"')
            json_str = re.sub(r'//.*', '', json_str)
            json_str = re.sub(r',([ \t\r\n]*[}\]])', r'\1', json_str)
            match = re.search(r'\{.*\}', json_str, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                # Fuzzy match old_item/new_item/item to actual order items
                for key in ["old_item", "new_item", "item"]:
                    if data.get(key):
                        closest = self._find_closest_item(data[key], order_items)
                        if closest:
                            data[key] = closest
                if data.get("action") in {"replace", "remove", "add"}:
                    return data
        except (LLMServiceError, json.JSONDecodeError, Exception) as e:
            print("LLM parsing error:", e)
            pass  # Fallback to old logic below
        # --- Fallback: old heuristic logic ---
        cleaned_input = ' '.join(user_input.splitlines()).strip()
        cleaned_input_lower = cleaned_input.lower()
        items_in_order = [item.lower() for item in order_items]
        if any(word in cleaned_input_lower for word in ["supprimer", "enlever", "retirer"]):
            for item in items_in_order:
                if item in cleaned_input_lower:
                    return {
                        'action': 'remove',
                        'item': item,
                        'original_text': next(line for line in items_text.split('\n') if item in line.lower())
                    }
        change_words = ["changer", "remplacer", "modifier", "échange"]
        if any(word in cleaned_input_lower for word in change_words):
            change_word = next(word for word in change_words if word in cleaned_input_lower)
            parts = cleaned_input.split(change_word, 1)
            if len(parts) > 1:
                before_change = parts[0].strip()
                after_change = parts[1].strip()
                for connector in ["le", "la", "les", "de", "par", "en", "pour"]:
                    after_change = after_change.replace(connector, "").strip()
                old_item = self._find_best_match(before_change, items_in_order)
                new_item = after_change
                if old_item:
                    return {
                        'action': 'replace',
                        'old_item': old_item,
                        'new_item': new_item
                    }
        if any(word in cleaned_input_lower for word in ["ajouter", "ajoutez", "ajoute"]):
            addition = cleaned_input_lower.replace("ajouter", "").replace("ajoutez", "").replace("ajoute", "").strip()
            return {
                'action': 'add',
                'item': addition
            }
        return None

    def _find_closest_item(self, name, items):
        matches = get_close_matches(name, items, n=1, cutoff=0.6)
        return matches[0] if matches else name

    def _find_best_match(self, text: str, items: List[str]) -> Optional[str]:
        text_lower = text.lower()
        for item in items:
            if item in text_lower:
                return item
        return None

    def _get_modification_confirmation_prompt(self, modification: Dict) -> str:
        if modification['action'] == 'remove':
            item_name = modification['item'].capitalize()
            return (f"Je comprends que vous souhaitez supprimer '{item_name}' de votre commande. "
                    "Est-ce correct ? (Oui/Non)")
        elif modification['action'] == 'replace':
            old_item = modification['old_item'].capitalize()
            new_item = modification['new_item'].capitalize()
            return (f"Je comprends que vous souhaitez remplacer '{old_item}' "
                    f"par '{new_item}'. Est-ce correct ? (Oui/Non)")
        elif modification['action'] == 'add':
            item_name = modification['item'].capitalize()
            return (f"Je comprends que vous souhaitez ajouter '{item_name}' "
                    "à votre commande. Est-ce correct ? (Oui/Non)")
        return "Je n'ai pas compris la modification demandée. Pouvez-vous reformuler ?"

    def _process_modification(self, order_context: str, user_input: str, conversation=None) -> Tuple[str, ConversationState]:
        order_id = order_context.split('Commande ID: ')[1].split('\n')[0]
        if conversation is None:
            conversation_data = self.db.get_conversation(order_id)
            if not conversation_data or not conversation_data.get('modification_request'):
                # Always return a ConversationState object
                conversation = ConversationState(order_id=order_id, messages=[], current_step="confirming_items")
                return ("Je ne trouve pas la demande de modification. Pouvez-vous répéter ?", conversation)
            conversation = ConversationState(**conversation_data)
        print(f"[DEBUG] _process_modification: modification_request={getattr(conversation, 'modification_request', None)}")
        modification = conversation.modification_request
        if modification is None:
            return ("Je ne trouve pas la demande de modification. Pouvez-vous répéter ?", conversation)
        user_input_lower = user_input.lower()
        if any(word in user_input_lower for word in ["non", "incorrect", "erreur"]):
            conversation.modification_request = None
            conversation.current_step = "confirming_items"
            return ("D'accord, annulons cette modification. Quel article souhaitez-vous modifier ?", conversation)
        if not any(word in user_input_lower for word in ["oui", "correct", "ok", "d'accord"]):
            return ("Je ne suis pas sûr d'avoir compris. Confirmez-vous cette modification ? (Oui/Non)", conversation)
        order_data = self.db.get_order(order_id)
        if not order_data:
            return ("Désolé, je ne trouve pas cette commande.", conversation)
        order = Order(**order_data)
        if modification['action'] == 'remove':
            order.items = [item for item in order.items if item.name != modification['item']]
        elif modification['action'] == 'replace':
            old_item_name = modification['old_item']
            item_names = [item.name for item in order.items]
            closest = get_close_matches(old_item_name, item_names, n=1, cutoff=0.6)
            if closest:
                for item in order.items:
                    if item.name == closest[0]:
                        item.name = modification['new_item']
                        break
        elif modification['action'] == 'add':
            order.items.append(OrderItem(
                name=modification['item'],
                quantity=1,
                price=0,  # Should be fetched from database
                notes='Ajouté lors de la confirmation'
            ))
        self.db.update_order(order_id, {
            'items': [item.dict() if hasattr(item, 'dict') else item for item in order.items],
            'total_amount': sum(item.price * item.quantity for item in order.items)
        })
        print(f"[DEBUG] _process_modification: applied modification, clearing modification_request")
        conversation.modification_request = None
        conversation.current_step = "confirming_items"
        updated_context = self._format_order_context(order)
        return (f"Modification effectuée ! Voici votre commande mise à jour:\n"
                f"{updated_context.split('Articles:')[1].split('Total:')[0]}\n"
                f"Total: {updated_context.split('Total: ')[1].split('€')[0]}€\n"
                "Est-ce que tout est correct maintenant ?", conversation)
    
    def _determine_next_step(self, current_step: str, user_input: str, response: str) -> str:
        step_transitions = {
            "greeting": "confirming_items",
            "confirming_items": "confirming_items",
            "modifying_items": "confirming_items",
            "confirming_details": "final_confirmation",
            "final_confirmation": "completed"
        }
        if current_step == "confirming_items" and any(word in user_input.lower() 
        for word in ["changer", "modifier", "remplacer", "supprimer", "ajouter"]):
            return "modifying_items"
        if current_step == "confirming_items" and any(word in response.lower() 
        for word in ["nom et votre adresse", "détails de livraison"]):
            return "confirming_details"
        return step_transitions.get(current_step, current_step)
    
    def reset_conversation(self, order_id: str) -> str:
        self.db.delete_conversation(order_id)
        conversation = ConversationState(
            order_id=order_id,
            messages=[],
            current_step="greeting",
            last_active=datetime.utcnow()
        )
        self.db.update_conversation(order_id, conversation.dict())
        order_data = self.db.get_order(order_id)
        if not order_data:
            return "Commande non trouvée"
        order = Order(**order_data)
        order_context = self._format_order_context(order)
        # Only use the string part of the tuple returned by _generate_response
        response, _ = self._generate_response(
            order_context,
            "greeting",
            "Pas d'historique",
            "Bonjour",
            conversation=conversation
        )
        return (
            "Conversation réinitialisée. " + response
        )   