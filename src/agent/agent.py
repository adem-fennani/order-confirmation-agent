from .models import Order, ConversationState, OrderItem
from .database.sqlite import SQLiteDatabase
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json
import re
from difflib import get_close_matches
from src.services.ai_service import call_llm, LLMServiceError

class OrderConfirmationAgent:
    def __init__(self, db: SQLiteDatabase): 
        self.db = db

    def _detect_language(self, text: str) -> str:
        en_words = ['yes', 'no', 'ok', 'correct', 'thanks', 'thank you', 'please', 'order', 'remove', 'add', 'help', 'cancel']
        fr_words = ['oui', 'non', "d'accord", 'merci', 'commande', 'retirer', 'ajouter', 'supprimer', 'aider', 'annuler']
        en_count = sum(1 for w in en_words if w in text.lower())
        fr_count = sum(1 for w in fr_words if w in text.lower())
        if en_count > fr_count:
            return 'en'
        if fr_count > en_count:
            return 'fr'
        if len([c for c in text if ord(c) < 128]) / max(1, len(text)) > 0.9:
            return 'en'
        return 'fr'

    async def process_message(self, order_id: str, user_input: str, language: str = "fr") -> str:
        try:
            conversation_data = await self.db.get_conversation(order_id)
            conversation = ConversationState(**conversation_data) if conversation_data else None
            user_input_lower = user_input.strip().lower()
            user_confirms = any(word in user_input_lower for word in ["yes", "oui", "ok", "correct", "d'accord"])
            last_assistant_message = None
            if conversation and conversation.messages:
                for msg in reversed(conversation.messages):
                    if msg["role"] == "assistant":
                        last_assistant_message = msg["content"]
                        break
            awaiting_confirmation = False
            if last_assistant_message:
                confirmation_phrases = [
                    "is your order now correct?",
                    "est-ce correct ?",
                    "est-ce que tout est correct",
                    "is everything correct",
                    "is that correct",
                    "est-ce en ordre",
                    "is your order correct"
                ]
                for phrase in confirmation_phrases:
                    if phrase in last_assistant_message.lower():
                        awaiting_confirmation = True
                        break
            only_want_match = re.search(r'(only want|seulement|juste)\s+(\d+)?\s*([\w\s]+)', user_input_lower)
            if only_want_match:
                qty = only_want_match.group(2)
                item = only_want_match.group(3).strip()
                order_data = await self.db.get_order(order_id)
                if order_data:
                    order = Order(**order_data)
                    for o_item in order.items:
                        if o_item.name.lower() != item.lower():
                            o_item.quantity = 0
                    for o_item in order.items:
                        if o_item.name.lower() == item.lower():
                            if qty:
                                o_item.quantity = int(qty)
                    order.items = [i for i in order.items if i.quantity > 0]
                    await self.db.update_order(order_id, {
                        'items': json.dumps([item.dict() if hasattr(item, 'dict') else item for item in order.items]),
                        'total_amount': sum(item.price * item.quantity for item in order.items)
                    })
                    items_str = ", ".join([f"{item.name} x{item.quantity}" for item in order.items])
                    total = sum(item.price * item.quantity for item in order.items)
                    lang = self._detect_language(user_input)
                    if lang.startswith("en"):
                        confirmation_message = f"Your order now contains: {items_str}. The total is {total}€. Is your order now correct?"
                    else:
                        confirmation_message = f"Votre commande contient maintenant : {items_str}. Le total est de {total}€. Est-ce correct ?"
                    if conversation:
                        conversation.messages.append({"role": "assistant", "content": confirmation_message})
                        await self.db.update_conversation(order_id, conversation.dict())
                    return confirmation_message
            if awaiting_confirmation and user_confirms:
                lang = self._detect_language(user_input)
                # Only transition if not already in confirming_address and no pending_address
                if conversation and not (conversation.current_step == "confirming_address" and getattr(conversation, 'pending_address', None)):
                    conversation.current_step = "confirming_address"
                    conversation.pending_address = None
                    if lang.startswith("en"):
                        address_prompt = "Could you please provide your delivery address?"
                    else:
                        address_prompt = "Pouvez-vous me donner votre adresse de livraison, s'il vous plaît ?"
                    conversation.messages.append({"role": "assistant", "content": address_prompt})
                    await self.db.update_conversation(order_id, conversation.dict())
                    return address_prompt
                # If already in confirming_address and address is pending, fall through to address confirmation logic below

            # Handle address confirmation step
            if conversation and getattr(conversation, 'current_step', None) == "confirming_address":
                address = user_input.strip()
                lang = self._detect_language(user_input)
                # If user confirms and pending_address exists, finalize
                if address.lower() in ["oui", "yes", "ok", "d'accord", "correct"]:
                    if conversation.pending_address:
                        await self.db.update_order(order_id, {"delivery_address": conversation.pending_address, "status": "confirmed", "confirmed_at": datetime.utcnow().isoformat()})
                        if lang.startswith("en"):
                            final_message = "Thank you! Your address is confirmed and your order is now being prepared."
                        else:
                            final_message = "Merci ! Votre adresse est confirmée et votre commande est en préparation."
                        conversation.messages.append({"role": "assistant", "content": final_message})
                        conversation.current_step = "completed"
                        conversation.pending_address = None
                        await self.db.update_conversation(order_id, conversation.dict())
                        return final_message
                    else:
                        # No pending address, reprompt
                        if lang.startswith("en"):
                            reprompt = "Could you please provide your delivery address?"
                        else:
                            reprompt = "Pouvez-vous me donner votre adresse de livraison, s'il vous plaît ?"
                        conversation.messages.append({"role": "assistant", "content": reprompt})
                        await self.db.update_conversation(order_id, conversation.dict())
                        return reprompt
                # If user says no, clear pending address and reprompt
                if address.lower() in ["non", "no", "incorrect", "erreur"]:
                    conversation.pending_address = None
                    if lang.startswith("en"):
                        reprompt = "Sorry, could you please provide your correct delivery address?"
                    else:
                        reprompt = "Désolé, pouvez-vous me donner votre adresse de livraison correcte ?"
                    conversation.messages.append({"role": "assistant", "content": reprompt})
                    await self.db.update_conversation(order_id, conversation.dict())
                    return reprompt
                # Otherwise, treat input as address and ask for confirmation
                conversation.pending_address = address
                if lang.startswith("en"):
                    confirm_prompt = f"Just to confirm, is this your delivery address: '{address}'? (yes/no)"
                else:
                    confirm_prompt = f"Pour confirmer, est-ce bien votre adresse de livraison : '{address}' ? (oui/non)"
                conversation.messages.append({"role": "assistant", "content": confirm_prompt})
                await self.db.update_conversation(order_id, conversation.dict())
                return confirm_prompt

            # Don't fall through to LLM if we're in confirming_address step
            if conversation and conversation.current_step == "confirming_address":
                # If we reach here, it means the address confirmation logic above didn't handle the input
                # This shouldn't happen, but as a safety net, prompt for address again
                lang = self._detect_language(user_input)
                if lang.startswith("en"):
                    fallback_prompt = "Could you please provide your delivery address?"
                else:
                    fallback_prompt = "Pouvez-vous me donner votre adresse de livraison, s'il vous plaît ?"
                conversation.messages.append({"role": "assistant", "content": fallback_prompt})
                await self.db.update_conversation(order_id, conversation.dict())
                return fallback_prompt

            llm_response = await self.llm_process_message(order_id, user_input, language=language)
            if llm_response and isinstance(llm_response, str) and llm_response.strip():
                return llm_response
            else:
                raise ValueError("LLM returned empty or invalid response")
        except LLMServiceError as e:
            if str(e) == "quota_exceeded":
                if language.startswith("en"):
                    return "Our assistant is temporarily unavailable (quota exceeded). Please try again later or contact support."
                else:
                    return "Notre assistant est temporairement indisponible (quota dépassé). Merci de réessayer plus tard ou de contacter le support."
            print(f"[LLM ERROR] {e}. Falling back to rule-based agent.")
            return await self.process_message_basic(order_id, user_input)
        except Exception as e:
            print("[LLM EXCEPTION]", e)
            print(f"[LLM PARSE ERROR] {e}")
            return "Sorry, I had trouble understanding your last message. Could you please rephrase or clarify? If the problem persists, a human agent will assist you."

    async def llm_process_message(self, order_id: str, user_input: str, language: str = "fr") -> str:
        order_data = await self.db.get_order(order_id)
        if not order_data:
            return "Désolé, je ne trouve pas cette commande. Pouvez-vous vérifier le numéro de commande?"
        order = Order(**order_data)
        if order.status == "confirmed":
            return "Votre commande a déjà été confirmée. Merci!"
        conversation_data = await self.db.get_conversation(order_id)
        if not conversation_data:
            conversation = ConversationState(
                order_id=order_id,
                messages=[],
                current_step="greeting"
            )
        else:
            conversation = ConversationState(**conversation_data)
        if conversation.current_step == "completed":
            return "Cette conversation est terminée. Merci!"
        
        # Don't use LLM for address confirmation - let the rule-based logic handle it
        if conversation.current_step == "confirming_address":
            lang = self._detect_language(user_input)
            if lang.startswith("en"):
                return "Could you please provide your delivery address?"
            else:
                return "Pouvez-vous me donner votre adresse de livraison, s'il vous plaît ?"
        
        conversation.messages.append({"role": "user", "content": user_input})
        conversation.last_active = datetime.utcnow()

        detected_language = self._detect_language(user_input)
        language = detected_language
        prev_assistant_lang = None
        for msg in reversed(conversation.messages[:-1]):
            if msg["role"] == "assistant":
                if any(word in msg["content"].lower() for word in ["votre commande", "est-ce correct", "merci", "parfait"]):
                    prev_assistant_lang = "fr"
                elif any(word in msg["content"].lower() for word in ["your order", "is your order", "thank you", "perfect"]):
                    prev_assistant_lang = "en"
                break
        if prev_assistant_lang and prev_assistant_lang != detected_language:
            conversation_history = f"Client: {user_input}"
        else:
            conversation_history = self._format_conversation_history(conversation.messages)
        order_context = self._format_order_context(order, language=language)
        conversation_history = self._format_conversation_history(conversation.messages)
        # Add explicit clarification examples for ambiguous/help requests
        if language.startswith("en"):
            language_instruction = (
                "Always reply in English, matching the user's message language. "
                "The user may switch between French and English (or other languages) at any time. "
                f"Detected language for this message: {language}.\n"
                "STRICT JSON RULES: Use ONLY these keys: message, action, modification, old_item, new_item, item, quantity.\n"
                "NEVER invent new keys (e.g., quantity_new, old_quantity, etc).\n"
                "ALWAYS use double quotes for all property names and string values.\n"
                "NEVER use single quotes. NEVER add trailing commas.\n"
                "If a field is not needed, set it to null.\n"
                "If you are unsure, ask for clarification.\n"
                "If you cannot parse the user's intent, reply with action: 'none'.\n"
                "NEGATIVE EXAMPLES (DO NOT DO THIS):\n"
                "{ 'message': '...', 'action': 'replace', 'modification': { 'old_item': 'Table', 'new_item': 'Chair', 'quantity_new': 2 } }\n"
                "{\"message\": \"...\", 'action': 'replace', 'modification': { 'old_item': 'Table', 'new_item': 'Chair', 'quantity': 2, } }\n"
                "POSITIVE EXAMPLES (DO THIS):\n"
                "{\"message\": \"...\", \"action\": \"replace\", \"modification\": {\"old_item\": \"Table\", \"new_item\": \"Chair\", \"quantity\": 2, \"item\": null} }\n"
                "If the user's request is ambiguous or a help request (e.g., 'Can you help?', 'I need help', 'What can you do?'), reply with:\n"
                "{\"message\": \"Could you please clarify what you would like to do with your order?\", \"action\": \"none\", \"modification\": null}\n"
            )
            prompt = f"""
{language_instruction}

You are a professional and friendly order confirmation agent. Here is the order context:
{order_context}

Conversation history:
{conversation_history}

The client said: "{user_input}"

IMPORTANT DELIVERY ADDRESS RULE:
- NEVER use action "confirm" unless the customer has already provided and confirmed their delivery address
- If the customer confirms their order details but hasn't provided a delivery address yet, use action "none" and ask for their delivery address
- Only after collecting and confirming the delivery address should you use action "confirm"
- The delivery address collection is MANDATORY before final confirmation

Reply strictly with a JSON in the following format:
{{
  "message": "...",  // What the agent should say to the client
  "action": "confirm|modify|cancel|add|remove|replace|none",  // The action to take (use 'none' if no action is required)
  "modification": {{ "old_item": "...", "new_item": "...", "item": "...", "quantity": ... }} // if applicable, otherwise null
}}
Do not add any text before or after the JSON.

Examples:
- If the client says "Yes" or "Correct", reply with the confirm action and a final closing message:
{{
  "message": "Great, your order is confirmed! We are preparing it now.",
  "action": "confirm",
  "modification": null
}}
- If the client wants to add an item, use the add action:
{{
  "message": "I've added 2 more motorcycles to your order. The total has been updated. Is there anything else?",
  "action": "add",
  "modification": {{ "item": "Motorcycle", "quantity": 2, "old_item": null, "new_item": null }}
}}
- If the client wants to modify an item's quantity, use the modify action:
{{
  "message": "The total number of bicycles in your order is now 2. Does that look right?",
  "action": "modify",
  "modification": {{ "item": "Bicycle", "quantity": 2, "old_item": null, "new_item": null }}
}}
- If the client wants to replace an item, use the replace action with old_item and new_item:
{{
  "message": "Lasagna has been replaced by Pizza in your order. Anything else?",
  "action": "replace",
  "modification": {{ "old_item": "Lasagna", "new_item": "Pizza", "item": null, "quantity": null }}
}}
- If the client says "Thank you", reply with the none action:
{{
  "message": "You're welcome! Feel free to contact us if you need anything else.",
  "action": "none",
  "modification": null
}}
- If the client's request is ambiguous or a help request (e.g., "Can you help?", "I need help", "What can you do?"), reply with:
{{
  "message": "Could you please clarify what you would like to do with your order?",
  "action": "none",
  "modification": null
}}
"""
        else:
            # French prompt with explicit clarification example
            language_instruction = (
                "Réponds toujours en français, en fonction de la langue du client. "
                "Le client peut passer du français à l'anglais (ou à une autre langue) à tout moment. "
                f"Langue détectée pour ce message : {language}.\n"
                "RÈGLES STRICTES JSON : Utilise UNIQUEMENT ces clés : message, action, modification, old_item, new_item, item, quantity.\n"
                "N'invente JAMAIS de nouvelles clés (ex : quantity_new, old_quantity, etc).\n"
                "Utilise TOUJOURS des guillemets doubles pour les noms de propriétés et les valeurs de chaîne.\n"
                "N'utilise JAMAIS de guillemets simples. N'ajoute JAMAIS de virgule finale.\n"
                "Si un champ n'est pas nécessaire, mets-le à null.\n"
                "Si tu n'es pas sûr, demande une clarification.\n"
                "Si tu ne peux pas comprendre l'intention du client, réponds avec action : 'none'.\n"
                "EXEMPLES NÉGATIFS (À NE PAS FAIRE) :\n"
                "{ 'message': '...', 'action': 'replace', 'modification': { 'old_item': 'Table', 'new_item': 'Chaise', 'quantity_new': 2 } }\n"
                "{\"message\": \"...\", 'action': 'replace', 'modification': { 'old_item': 'Table', 'new_item': 'Chaise', 'quantity': 2, } }\n"
                "EXEMPLES POSITIFS (À FAIRE) :\n"
                "{\"message\": \"...\", \"action\": \"replace\", \"modification\": {\"old_item\": \"Table\", \"new_item\": \"Chaise\", \"quantity\": 2, \"item\": null} }\n"
                "Si la demande du client est ambiguë ou une demande d'aide (ex : 'Pouvez-vous m'aider ?', 'J'ai besoin d'aide', 'Que pouvez-vous faire ?'), réponds :\n"
                "{\"message\": \"Pouvez-vous préciser ce que vous souhaitez faire avec votre commande ?\", \"action\": \"none\", \"modification\": null}\n"
            )
            prompt = f"""
{language_instruction}

Vous êtes un agent de confirmation de commande professionnel et amical. Voici le contexte de la commande :
{order_context}

Historique de la conversation :
{conversation_history}

Le client a dit : "{user_input}"

RÈGLE IMPORTANTE POUR L'ADRESSE DE LIVRAISON :
- N'utilisez JAMAIS l'action "confirm" sauf si le client a déjà fourni et confirmé son adresse de livraison
- Si le client confirme les détails de sa commande mais n'a pas encore fourni d'adresse de livraison, utilisez l'action "none" et demandez son adresse de livraison
- Une fois que le client a fourni une adresse ET confirmé cette adresse (en disant "oui", "correct", "exact", etc.), utilisez alors l'action "confirm" pour finaliser la commande
- La collecte de l'adresse de livraison est OBLIGATOIRE avant la confirmation finale
- IMPORTANT: Évitez les apostrophes dans vos messages JSON (utilisez "est" au lieu de "cest", "ne" au lieu de "nest", etc.)

Répondez strictement avec un JSON dans le format suivant :
{{
  "message": "...",  // Ce que l'agent doit dire au client
  "action": "confirm|modify|cancel|add|remove|replace|none",  // L'action à effectuer (utilise 'none' si aucune action n'est requise)
  "modification": {{ "old_item": "...", "new_item": "...", "item": "...", "quantity": ... }} // si applicable, sinon null
}}
N'ajoute aucun texte avant ou après le JSON.

Exemples :
- Si le client dit "Oui" ou "Correct", réponds avec l'action confirm et un message de clôture :
{{
  "message": "Parfait, votre commande est confirmée ! Nous la préparons dès maintenant.",
  "action": "confirm",
  "modification": null
}}
- Si le client veut ajouter un article, utilise l'action add :
{{
  "message": "J'ai ajouté 2 motos supplémentaires à votre commande. Le total a été mis à jour. Souhaitez-vous autre chose ?",
  "action": "add",
  "modification": {{ "item": "Moto", "quantity": 2, "old_item": null, "new_item": null }}
}}
- Si le client veut modifier la quantité d'un article, utilise l'action modify :
{{
  "message": "Le nombre total de vélos dans votre commande est maintenant de 2. Cela vous convient-il ?",
  "action": "modify",
  "modification": {{ "item": "Vélo", "quantity": 2, "old_item": null, "new_item": null }}
}}
- Si le client veut remplacer un article, utilise l'action replace avec old_item et new_item :
{{
  "message": "La lasagne a été remplacée par une pizza dans votre commande. Autre chose ?",
  "action": "replace",
  "modification": {{ "old_item": "Lasagne", "new_item": "Pizza", "item": null, "quantity": null }}
}}
- Si le client dit "Merci", réponds avec l'action none :
{{
  "message": "Avec plaisir ! N'hésitez pas à nous contacter si besoin.",
  "action": "none",
  "modification": null
}}
- Si la demande du client est ambiguë ou une demande d'aide (ex : "Pouvez-vous m'aider ?", "J'ai besoin d'aide", "Que pouvez-vous faire ?"), réponds :
{{
  "message": "Pouvez-vous préciser ce que vous souhaitez faire avec votre commande ?",
  "action": "none",
  "modification": null
}}
"""
        # End of prompt construction
        try:
            llm_raw = await call_llm(prompt, max_tokens=256)
            print("[LLM RAW]", llm_raw)
            json_str = llm_raw.strip()
            # Robust JSON repair/validation
            import re, json
            def repair_json(s):
                # Replace single quotes with double quotes
                s = re.sub(r"'", '"', s)
                # Remove trailing commas before closing braces/brackets
                s = re.sub(r',([ \t\r\n]*[}\]])', r'\1', s)
                # Remove non-breaking spaces and invisible characters
                s = s.replace('\u00A0', ' ')
                # Remove unquoted property names (rare)
                s = re.sub(r'([,{\[])(\s*)([a-zA-Z0-9_]+)(\s*):', r'\1\2"\3"\4:', s)
                return s
            try:
                match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if not match:
                    raise ValueError("No JSON found in LLM output")
                cleaned_json = repair_json(match.group(0))
                print("[LLM CLEANED JSON]", cleaned_json)
                data = json.loads(cleaned_json)
            except Exception as e:
                print(f"[LLM PARSE ERROR] {e}")
                # Fallback: try to extract action and modification fields with regex
                action_match = re.search(r'"action"\s*:\s*"(\w+)"', json_str)
                mod_match = re.search(r'"modification"\s*:\s*(\{.*?\}|null)', json_str, re.DOTALL)
                msg_match = re.search(r'"message"\s*:\s*"([^"]*)"', json_str)
                data = {"action": None, "modification": None, "message": "[LLM parse fallback]"}
                if action_match:
                    data["action"] = action_match.group(1)
                if mod_match:
                    mod_val = mod_match.group(1)
                    if mod_val == 'null':
                        data["modification"] = None
                    else:
                        try:
                            data["modification"] = json.loads(repair_json(mod_val))
                        except Exception:
                            data["modification"] = None
                if msg_match:
                    data["message"] = msg_match.group(1)
            # If the LLM action is confirm, update the order status
            if data.get("action") == "confirm":
                # Always use the language detected from the most recent user message
                if detected_language.startswith("en"):
                    final_message = "Perfect, your order is confirmed. We are now preparing it. Thank you!"
                else:
                    final_message = "Parfait, votre commande est confirmée. Nous procédons à sa préparation. Merci !"
                
                await self.db.update_order(
                    order_id,
                    {
                        "status": "confirmed",
                        "confirmed_at": datetime.utcnow().isoformat()
                    }
                )
                # Move conversation to final state after confirmation
                conversation.messages.append({"role": "assistant", "content": final_message})
                conversation.current_step = "completed"
                await self.db.update_conversation(order_id, conversation.dict())
                return final_message
            elif data.get("action") == "cancel":
                await self.db.update_order(
                    order_id,
                    {
                        "status": "cancelled",
                        "cancelled_at": datetime.utcnow().isoformat()
                    }
                )
            # Handle action if needed (e.g., apply modification)
            # Only apply modification if not already pending
            if data.get("action") in {"modify", "replace", "remove", "add"} and data.get("modification"):
                applied_successfully = await self._apply_llm_modification(order_id, order, data["modification"], data["action"], conversation, user_input)
                # --- Inform user if fewer items were removed than requested ---
                if data.get("action") == "remove":
                    norm = self._normalize_modification(data["modification"], data["action"])
                    actually_removed = None
                    if "actually_removed" in norm:
                        actually_removed = norm["actually_removed"]
                    # Try to get from the last applied norm if not present
                    if not actually_removed and "actually_removed" in data["modification"]:
                        actually_removed = data["modification"]["actually_removed"]
                    requested = norm.get("old_qty", 1)
                    removed = actually_removed
                    if removed is not None and removed < requested:
                        if language.startswith("en"):
                            data["message"] = (data["message"] + f" Note: Only {removed} {norm['old_item']}(s) were removed because that was all that remained in your order.")
                        else:
                            data["message"] = (data["message"] + f" Note : Seulement {removed} {norm['old_item']}(s) ont été supprimé(s) car c'est tout ce qui restait dans votre commande.")
                if not applied_successfully:
                    if language.startswith("en"):
                        data["message"] = "I'm sorry, I didn't understand that. Could you please clarify your request?"
                    else:
                        data["message"] = "Je suis désolé, je n'ai pas compris. Pouvez-vous clarifier votre demande ?"
                else:
                    updated_order_data = await self.db.get_order(order_id)
                    if isinstance(updated_order_data, str) and updated_order_data is not None:
                        try:
                            updated_order_data = json.loads(updated_order_data)
                        except Exception as e:
                            print(f"[ERROR] Could not parse updated_order_data: {e}")
                            updated_order_data = None
                    if isinstance(updated_order_data, dict):
                        updated_order = Order(**updated_order_data)
                        items_str = ", ".join([f"{item.name} x{item.quantity}" for item in updated_order.items])
                        total = updated_order.total_amount
                        if language.startswith("en"):
                            confirmation_message = f"Your order now contains: {items_str}. The total is {total}€. Is your order now correct?"
                        else:
                            confirmation_message = f"Votre commande contient maintenant : {items_str}. Le total est de {total}€. Est-ce correct ?"
                        data["message"] = confirmation_message
            else:
                # Clear pending_modification if not a modification action
                pass
            # Save conversation state
            # Force the agent to always generate its own message in the detected language for confirm/final state
            if data.get("action") == "confirm":
                if detected_language.startswith("en"):
                    agent_message = "Perfect, your order is confirmed. We are now preparing it. Thank you!"
                else:
                    agent_message = "Parfait, votre commande est confirmée. Nous procédons à sa préparation. Merci !"
                conversation.messages.append({"role": "assistant", "content": agent_message})
                await self.db.update_conversation(order_id, conversation.dict())
                return agent_message
            else:
                conversation.messages.append({"role": "assistant", "content": data["message"]})
                await self.db.update_conversation(order_id, conversation.dict())
                return data["message"]
        except Exception as e:
            print(f"[LLM PARSE ERROR] {e}")
            raise

    def _normalize_modification(self, modification, action=None):
        mod = modification if isinstance(modification, dict) else {}
        # Use the parent action if not present in the modification dict
        mod_action = mod.get('action') or action
        # Handle 'modify' action as a set operation
        if mod_action == 'modify' and mod.get('item') and mod.get('quantity'):
            norm = {
                "action": "modify",
                "old_item": mod.get('item'),
                "new_item": mod.get('item'),
                "old_qty": None,
                "new_qty": int(mod.get('quantity', 1))
            }
            return norm
        """
        Normalize any LLM modification dict to a canonical format:
        {"action": ..., "old_item": ..., "new_item": ..., "old_qty": ..., "new_qty": ...}
        For 'replace' with a 'quantity' field, always treat as: remove old_item (1 or specified), add new_item with the specified quantity.
        """
        norm = {"action": None, "old_item": None, "new_item": None, "old_qty": 1, "new_qty": 1}
        # Handle cancel action
        if mod.get('action') == 'cancel':
            norm['action'] = 'cancel'
            return norm
        # Handle add with 'item' key (fallback and LLM)
        if mod.get('action') == 'add' and mod.get('item'):
            norm['action'] = 'add'
            norm['new_item'] = mod.get('item')
            norm['new_qty'] = int(mod.get('quantity', 1))
            return norm

        # Handle remove with 'item' key (fallback and LLM)
        if mod.get('action') == 'remove' and mod.get('item'):
            norm['action'] = 'remove'
            norm['old_item'] = mod.get('item')
            norm['old_qty'] = int(mod.get('quantity', 1))
            return norm
        # Handle standard remove (LLM: {"old_item": ..., "quantity": ...})
        if mod.get('old_item') and mod.get('quantity') and not mod.get('new_item') and not mod.get('item'):
            norm["action"] = "remove"
            norm["old_item"] = mod["old_item"]
            norm["old_qty"] = mod["quantity"]
            return norm
        # Handle remove with 'old_item' and 'old_quantity' (new fix)
        if mod.get('old_item') and mod.get('old_quantity') and not mod.get('new_item') and not mod.get('item'):
            norm["action"] = "remove"
            norm["old_item"] = mod["old_item"]
            norm["old_qty"] = mod["old_quantity"]
            return norm
        # 1. quantity dict (delta)
        if isinstance(mod.get('quantity'), dict):
            for name, delta in mod['quantity'].items():
                if delta < 0:
                    norm["action"] = "remove"
                    norm["old_item"] = name
                    norm["old_qty"] = abs(delta)
                elif delta > 0:
                    norm["action"] = "add"
                    norm["new_item"] = name
                    norm["new_qty"] = delta
            return norm
        # 2. oldItem/newItem with articleName or name
        if ("oldItem" in mod and "newItem" in mod):
            old = mod["oldItem"]
            new = mod["newItem"]
            norm["action"] = "replace"
            norm["old_item"] = old.get("articleName") or old.get("name")
            norm["old_qty"] = old.get("quantity", 1)
            norm["new_item"] = new.get("articleName") or new.get("name")
            norm["new_qty"] = new.get("quantity", 1)
            return norm
        # 3. old/new with article_name
        if ("old" in mod and "new" in mod):
            old = mod["old"]
            new = mod["new"]
            norm["action"] = "replace"
            norm["old_item"] = old.get("article_name")
            norm["old_qty"] = old.get("quantity", 1)
            norm["new_item"] = new.get("article_name")
            norm["new_qty"] = new.get("quantity", 1)
            return norm
        # 4. product/new_product
        if ("product" in mod and "new_product" in mod):
            norm["action"] = "replace"
            norm["old_item"] = mod["product"]
            norm["new_item"] = mod["new_product"]
            norm["old_qty"] = mod.get("quantity", 1)
            norm["new_qty"] = mod.get("quantity", 1)
            return norm
        # 5. article_old/article_new
        if ("article_old" in mod and "article_new" in mod):
            old = mod["article_old"]
            new = mod["article_new"]
            norm["action"] = "replace"
            norm["old_item"] = old.get("name")
            norm["old_qty"] = old.get("quantity", 1)
            norm["new_item"] = new.get("name")
            norm["new_qty"] = new.get("quantity", 1)
            return norm
        # 6. item_id_to_remove/article_id_to_remove
        if "item_id_to_remove" in mod or "article_id_to_remove" in mod:
            norm["action"] = "remove"
            norm["old_item"] = mod.get("item_id_to_remove") or mod.get("article_id_to_remove")
            norm["old_qty"] = mod.get("quantity", 1)
            return norm
        # 8. old_item/new_item or old_item/item (handle 'replace' or 'remove')
        if mod.get("old_item") is not None and (mod.get("new_item") is not None or mod.get("item") is not None):
            if mod.get("action") == "remove" or (
                mod.get("action") is None and (
                    (mod.get("new_item") is None or mod.get("new_item") == mod.get("old_item")) or
                    (mod.get("item") is not None and mod.get("item") == mod.get("old_item"))
                )
            ):
                # Treat as remove
                norm["action"] = "remove"
                norm["old_item"] = mod["old_item"]
                norm["old_qty"] = mod.get("quantity", 1)
                return norm
            else:
                # Treat as replace
                norm["action"] = "replace"
                norm["old_item"] = mod["old_item"]
                norm["new_item"] = mod.get("new_item") or mod.get("item")
                if "quantity" in mod and mod["quantity"]:
                    norm["old_qty"] = 1
                    norm["new_qty"] = mod["quantity"]
                else:
                    norm["old_qty"] = 1
                    norm["new_qty"] = 1
                return norm
        # 7. item/article_id_to_add
        if "item" in mod or "article_id_to_add" in mod:
            norm["action"] = "add"
            norm["new_item"] = mod.get("item") or mod.get("article_id_to_add")
            norm["new_qty"] = mod.get("quantity", 1)
            return norm
        print(f"[WARN] Could not normalize LLM modification: {mod}")
        return norm

    async def _apply_llm_modification(self, order_id, order, modification, action, conversation, user_input=None) -> bool:
        """Apply the modification as instructed by the LLM. Uses normalized canonical format. Prevents duplicate modifications."""
        norm = self._normalize_modification(modification, action)
        print(f"[NORM] Normalized modification: {norm}")
        # --- Prevent duplicate modifications ---
        # conversation_data = await self.db.get_conversation(order_id) # This line is removed as conversation is passed as an argument
        # if conversation_data: # This line is removed as conversation is passed as an argument
        #     conversation = ConversationState(**conversation_data) # This line is removed as conversation is passed as an argument
        #     last_mod = getattr(conversation, 'last_modification', None) # This line is removed as conversation is passed as an argument
        # Use a tuple for easy comparison
        current_mod_tuple = (norm["action"], norm["old_item"], norm["new_item"], norm["old_qty"], norm["new_qty"])
        # if last_mod == current_mod_tuple: # This line is removed as conversation is passed as an argument
        #     print(f"[WARN] Duplicate modification detected, skipping: {current_mod_tuple}") # This line is removed as conversation is passed as an argument
        #     return False # This line is removed as conversation is passed as an argument
        # else: # This line is removed as conversation is passed as an argument
        #     conversation = None # This line is removed as conversation is passed as an argument
        #     last_mod = None # This line is removed as conversation is passed as an argument
        applied = False
        if norm["action"] == "replace" and norm["old_item"] and norm["new_item"]:
            # Always remove the old item completely
            order.items = [i for i in order.items if i.name.lower() != norm["old_item"].lower()]
            # Add new item(s) with the specified quantity
            existing = next((item for item in order.items if item.name.lower() == norm["new_item"].lower()), None)
            if existing:
                existing.quantity += norm["new_qty"]
            else:
                # Try to infer price from any item with the same name (case-insensitive)
                price = 0
                for item in order.items:
                    if item.name.lower() == norm["new_item"].lower():
                        price = item.price
                        break
                # If not found, try to use the price of the last item as a fallback
                if price == 0 and order.items:
                    price = order.items[-1].price
                order.items.append(OrderItem(
                    name=norm["new_item"],
                    quantity=norm["new_qty"],
                    price=price,
                    notes='Ajouté via LLM (replace)'))
            applied = True
        elif norm["action"] == "add" and norm["new_item"]:
            existing = next((item for item in order.items if item.name.lower() == norm["new_item"].lower()), None)
            if existing:
                existing.quantity += norm["new_qty"]
            else:
                # Try to infer price from any item with the same name (case-insensitive)
                price = 0
                for item in order.items:
                    if item.name.lower() == norm["new_item"].lower():
                        price = item.price
                        break
                # If not found, try to use the price of the last item as a fallback
                if price == 0 and order.items:
                    price = order.items[-1].price
                order.items.append(OrderItem(
                    name=norm["new_item"],
                    quantity=norm["new_qty"],
                    price=price,
                    notes='Ajouté via LLM (add)'))
            applied = True
        elif norm["action"] == "remove" and norm["old_item"]:
            removed_count = 0
            for item in order.items:
                if item.name.lower() == norm["old_item"].lower():
                    to_remove = min(norm["old_qty"], item.quantity)
                    removed_count = to_remove
                    item.quantity -= to_remove
                    if item.quantity <= 0:
                        order.items = [i for i in order.items if i.name.lower() != norm["old_item"].lower()]
                    break
            applied = True
            # Store removed_count in the object for later use in the confirmation message if needed
            norm["actually_removed"] = removed_count
        elif norm["action"] == "modify" and norm["old_item"] and norm["new_item"] and norm["new_qty"] is not None:
            # Set the quantity of the item directly
            for item in order.items:
                if item.name.lower() == norm["old_item"].lower():
                    item.quantity = norm["new_qty"]
                    applied = True
                    break
        if not applied:
            print(f"[WARN] Could not apply normalized modification: {norm}")
            return False
        await self.db.update_order(order_id, {
            'items': json.dumps([item.dict() if hasattr(item, 'dict') else item for item in order.items]),
            'total_amount': sum(item.price * item.quantity for item in order.items)
        })
        # --- Store last modification in conversation state ---
        # if conversation: # This line is removed as conversation is passed as an argument
        #     conversation.last_modification = (norm["action"], norm["old_item"], norm["new_item"], norm["old_qty"], norm["new_qty"]) # This line is removed as conversation is passed as an argument
        #     await self.db.update_conversation(order_id, conversation.dict()) # This line is removed as conversation is passed as an argument
        return True

    async def process_message_basic(self, order_id: str, user_input: str) -> str:
        # The old rule-based logic, unchanged. Just call the previous process_message logic here if fallback is needed.
        # For now, call the previous implementation (copy the old process_message logic here if needed).
        # This is a placeholder for the fallback.
        return "[Fallback] LLM n'a pas compris. (Ancienne logique à implémenter ici.)"

    async def _handle_modification_request(self, order_context: str) -> str:
        # Stub implementation for missing method
        return "Je ne peux pas traiter cette demande de modification pour le moment."

    def _is_clear_confirmation(self, user_input: str) -> bool:
        # Stub implementation for missing method
        return any(word in user_input.lower() for word in ["oui", "non", "correct", "incorrect", "yes", "no"])

    async def _parse_modification_request(self, user_input: str, order_context: str, order_items: List[str]) -> Optional[Dict]:
        # Stub implementation for missing method
        return None

    def _get_modification_confirmation_prompt(self, modification: Dict) -> str:
        # Stub implementation for missing method
        return "Confirmation de modification non disponible."

    async def _process_modification(self, order_context: str, user_input: str, conversation=None) -> Tuple[str, ConversationState]:
        # Stub implementation for missing method
        if conversation:
            conversation.current_step = "confirming_items"
        return "Modification traitée.", conversation or ConversationState(order_id="", messages=[], current_step="confirming_items")

    def _format_order_context(self, order: Order, language: str = "fr") -> str:
        item_price_lang = "each" if language.startswith("en") else "chacun"
        items_str = "\n".join([
            f"- {item.name} x{item.quantity} ({item.price}€ {item_price_lang})"
            for item in order.items
        ])

        if language.startswith("en"):
            return f"""
Order ID: {order.id}
Customer: {order.customer_name}
Phone: {order.customer_phone}
Items:
{items_str}
Total: {order.total_amount}€
Status: {order.status}
"""
        else:
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
        history = [f"{ 'Client' if msg['role'] == 'user' else 'Agent'}: {msg['content']}" 
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

    async def _generate_response(self, order_context: str, current_step: str, 
                        conversation_history: str, user_input: str, conversation=None) -> Tuple[str, ConversationState]:
        print(f"[DEBUG] _generate_response: current_step={current_step}, modification_request={getattr(conversation, 'modification_request', None) if conversation else None}")
        order_id_match = re.search(r"Commande ID: (.+)", order_context)
        order_id = order_id_match.group(1).strip() if order_id_match else ""
        if not conversation:
            conversation_data = await self.db.get_conversation(order_id)
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
                return (await self._handle_modification_request(order_context), conversation)
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
                modification = await self._parse_modification_request(user_input, order_context, order_items)
                if modification:
                    if conversation:
                        conversation.modification_request = modification
                        conversation.current_step = "modifying_items"
                    return (self._get_modification_confirmation_prompt(modification), conversation)
                return ("Je ne suis pas sûr de comprendre. Pouvez-vous me dire si les articles de votre commande sont corrects ?", conversation)
        elif current_step == "modifying_items":
            print(f"[DEBUG] _generate_response (modifying_items): modification_request={getattr(conversation, 'modification_request', None)}")
            result, conversation = await self._process_modification(order_context, user_input, conversation=conversation)
            print(f"[DEBUG] _generate_response (after _process_modification): modification_request={getattr(conversation, 'modification_request', None)}")
            return (result, conversation)
        elif current_step == "confirming_address":
            # Prompt user for delivery address or confirm it
            address = getattr(conversation, 'pending_address', None)
            lang = self._detect_language(user_input)
            if not address:
                # Try to extract address from user_input
                user_address = user_input.strip()
                if any(word in user_address.lower() for word in ["oui", "correct", "ok", "d'accord"]):
                    # User just said yes, but no address provided; ask for address
                    if lang.startswith("en"):
                        return ("Could you please provide your delivery address?", conversation)
                    else:
                        return ("Pouvez-vous me donner votre adresse de livraison, s'il vous plaît ?", conversation)
                # Save address in conversation state for confirmation
                conversation.pending_address = user_address
                if lang.startswith("en"):
                    return (f"Just to confirm, is this your delivery address: '{user_address}'? (Yes/No)", conversation)
                else:
                    return (f"Pour confirmer, est-ce bien votre adresse de livraison : '{user_address}' ? (Oui/Non)", conversation)
            else:
                # User confirms the address
                if any(word in user_input.lower() for word in ["oui", "correct", "ok", "d'accord"]):
                    # Save address to order and clear pending_address
                    order_id = conversation.order_id
                    await self.db.update_order(order_id, {"delivery_address": address})
                    conversation.delivery_address = address
                    conversation.pending_address = None
                    conversation.current_step = "confirming_details"
                    if lang.startswith("en"):
                        return ("Thank you! Now, could you confirm your name and any other delivery details?", conversation)
                    else:
                        return ("Merci ! Maintenant, pouvez-vous confirmer votre nom et d'autres détails de livraison ?", conversation)
                else:
                    # User said no, ask for address again
                    conversation.pending_address = None
                    if lang.startswith("en"):
                        return ("Okay, please provide the correct delivery address.", conversation)
                    else:
                        return ("D'accord, merci de fournir la bonne adresse de livraison.", conversation)

        elif current_step == "confirming_details":
            # Ask for explicit final confirmation before proceeding
            conversation.current_step = "final_confirmation"
            return ("Merci, nous récapitulons votre commande. Confirmez-vous que tout est correct avant que nous procédions à la préparation ?", conversation)
        elif current_step == "final_confirmation":
            if any(word in user_input_lower for word in ["oui", "confirme", "ok", "d'accord"]):
                await self.db.update_order(
                    order_id=order_context.split('Commande ID: ')[1].split('\n')[0],
                    updates={"status": "confirmed", "confirmed_at": datetime.utcnow().isoformat()})
                return ("Parfait, nous procédons à la préparation de votre commande.", conversation)
            else:
                await self.db.update_order(
                    order_id=order_context.split('Commande ID: ')[1].split('\n')[0],
                    updates={"status": "cancelled"}
                )
                return ("Très bien, votre commande est annulée. N'hésitez pas à nous recontacter. Bonne journée !", conversation)
        return ("Je ne suis pas sûr de comprendre. Pouvez-vous répéter ?", conversation)

    def _determine_next_step(self, current_step: str, user_input: str, response: str) -> str:
        step_transitions = {
            "greeting": "confirming_items",
            "confirming_items": "confirming_address",
            "confirming_address": "confirming_details",
            "modifying_items": "confirming_items",
            "confirming_details": "final_confirmation",
            "final_confirmation": "completed"
        }
        # If user wants to modify items
        if current_step == "confirming_items" and any(word in user_input.lower() 
        for word in ["changer", "modifier", "remplacer", "supprimer", "ajouter"]):
            return "modifying_items"
        # If we just finished confirming items, go to confirming_address
        if current_step == "confirming_items" and any(word in user_input.lower() for word in ["oui", "correct", "ok", "d'accord"]):
            return "confirming_address"
        # If address is confirmed, move to confirming_details
        if current_step == "confirming_address" and any(word in user_input.lower() for word in ["oui", "correct", "ok", "d'accord"]):
            return "confirming_details"
        # If confirming details, move to final confirmation
        if current_step == "confirming_details" and any(word in user_input.lower() for word in ["oui", "correct", "ok", "d'accord"]):
            return "final_confirmation"
        # If final confirmation, complete
        if current_step == "final_confirmation" and any(word in user_input.lower() for word in ["oui", "confirme", "ok", "d'accord"]):
            return "completed"
        return step_transitions.get(current_step, current_step)

    async def reset_conversation(self, order_id: str) -> dict:
        await self.db.delete_conversation(order_id)
        conversation = ConversationState(
            order_id=order_id,
            messages=[],
            current_step="greeting",
            last_active=datetime.utcnow()
        )
        await self.db.update_conversation(order_id, conversation.dict())
        order_data = await self.db.get_order(order_id)
        if not order_data:
            return {"message": "Commande non trouvée"}
        order = Order(**order_data)
        order_context = self._format_order_context(order, language=self._detect_language("Bonjour"))
        # Only use the string part of the tuple returned by _generate_response
        response, _ = await self._generate_response(
            order_context,
            "greeting",
            "Pas d'historique",
            "Bonjour",
            conversation=conversation
        )
        return {
            "message": "Conversation réinitialisée. " + response
        }   

    async def start_conversation(self, order_id: str, language: str = "fr") -> str:
        order_data = await self.db.get_order(order_id)
        if not order_data:
            return "Sorry, I can't find this order." if language.startswith("en") else "Désolé, je ne trouve pas cette commande."
        order = Order(**order_data)
        conversation = ConversationState(
            order_id=order_id,
            messages=[],
            current_step="greeting"
        )
        # Use the new natural summary for the first message
        order_summary = self._format_order_summary_natural(order, language=language)
        if language.startswith("en"):
            message = f"Hello {order.customer_name}, I'm confirming your order. {order_summary} Is this correct?"
        else:
            message = f"Bonjour {order.customer_name}, je vous appelle pour confirmer votre commande. {order_summary} Est-ce que c'est correct ?"
        conversation.messages.append({"role": "assistant", "content": message})
        await self.db.update_conversation(order_id, conversation.dict())
        return message   

    def _format_order_summary_natural(self, order: Order, language: str = "fr") -> str:
        items = order.items
        if not items:
            return ""
        if language.startswith("en"):
            if len(items) == 1:
                item = items[0]
                total = item.price * item.quantity
                return f"You ordered {item.quantity}x {item.name.lower()} for a total of {total:.1f}€."
            else:
                item_strs = []
                for item in items:
                    if item.quantity == 1:
                        item_strs.append(f"1x {item.name.lower()} ({item.price:.1f}€)")
                    else:
                        item_strs.append(f"{item.quantity}x {item.name} ({item.price:.1f}€ each)")
                total = sum(item.price * item.quantity for item in items)
                return f"You ordered {', '.join(item_strs)} for a total of {total:.1f}€."
        else:
            if len(items) == 1:
                item = items[0]
                total = item.price * item.quantity
                return f"Vous avez commandé {item.quantity}x {item.name.lower()} pour un total de {total:.1f}€."
            else:
                item_strs = []
                for item in items:
                    if item.quantity == 1:
                        item_strs.append(f"1x {item.name.lower()} ({item.price:.1f}€)")
                    else:
                        item_strs.append(f"{item.quantity}x {item.name} ({item.price:.1f}€ chacun)")
                total = sum(item.price * item.quantity for item in items)
                return f"Vous avez commandé {', '.join(item_strs)} pour un total de {total:.1f}€."  