from .models import Order, ConversationState, OrderItem
from .database.sqlite import SQLiteDatabase
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json
import re
from difflib import get_close_matches
from src.services.ai_service import call_llm, LLMServiceError
from fastapi.encoders import jsonable_encoder

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
    
    def process_message(self, order_id: str, user_input: str, language: str = "fr") -> str:
        try:
            # --- Heuristic parsing for user corrections ---
            conversation_data = self.db.get_conversation(order_id)
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
            # Heuristic: if user says 'only want X' or 'seulement X', remove all other items except X
            import re
            only_want_match = re.search(r'(only want|seulement|juste)\s+(\d+)?\s*([\w\s]+)', user_input_lower)
            if only_want_match:
                qty = only_want_match.group(2)
                item = only_want_match.group(3).strip()
                order_data = self.db.get_order(order_id)
                if order_data:
                    order = Order(**order_data)
                    # Remove all items except the specified one
                    for o_item in order.items:
                        if o_item.name.lower() != item.lower():
                            o_item.quantity = 0
                    # Set the quantity if specified
                    for o_item in order.items:
                        if o_item.name.lower() == item.lower():
                            if qty:
                                o_item.quantity = int(qty)
                    # Remove items with quantity 0
                    order.items = [i for i in order.items if i.quantity > 0]
                    self.db.update_order(order_id, {
                        'items': json.dumps([item.dict() if hasattr(item, 'dict') else item for item in order.items]),
                        'total_amount': sum(item.price * item.quantity for item in order.items)
                    })
                    items_str = ", ".join([f"{item.name} x{item.quantity}" for item in order.items])
                    total = sum(item.price * item.quantity for item in order.items)
                    if language.startswith("en"):
                        confirmation_message = f"Your order now contains: {items_str}. The total is {total}€. Is your order now correct?"
                    else:
                        confirmation_message = f"Votre commande contient maintenant : {items_str}. Le total est de {total}€. Est-ce correct ?"
                    if conversation:
                        conversation.messages.append({"role": "assistant", "content": confirmation_message})
                        self.db.update_conversation(order_id, conversation.dict())
                    return confirmation_message
            if awaiting_confirmation and user_confirms:
                if language.startswith("en"):
                    final_message = "Perfect, your order is confirmed. We are now preparing it. Thank you!"
                else:
                    final_message = "Parfait, votre commande est confirmée. Nous procédons à sa préparation. Merci !"
                self.db.update_order(
                    order_id,
                    {
                        "status": "confirmed",
                        "confirmed_at": datetime.utcnow().isoformat()
                    }
                )
                if conversation:
                    conversation.messages.append({"role": "assistant", "content": final_message})
                    conversation.current_step = "completed"
                    self.db.update_conversation(order_id, conversation.dict())
                else:
                    conversation = ConversationState(
                        order_id=order_id,
                        messages=[{"role": "assistant", "content": final_message}],
                        current_step="completed"
                    )
                    self.db.update_conversation(order_id, conversation.dict())
                return final_message
            # --- End message-history-based confirmation logic ---
            llm_response = self.llm_process_message(order_id, user_input, language=language)
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
            return self.process_message_basic(order_id, user_input)
        except Exception as e:
            print(f"[LLM ERROR] {e}. Falling back to rule-based agent.")
            return self.process_message_basic(order_id, user_input)

    def llm_process_message(self, order_id: str, user_input: str, language: str = "fr") -> str:
        """
        New LLM-centric conversation logic. Handles all steps: greeting, confirmation, modification, etc.
        Returns the agent's response as a string. Raises on LLM or parsing failure.
        """
        order_data = self.db.get_order(order_id)
        if not order_data:
            return "Désolé, je ne trouve pas cette commande. Pouvez-vous vérifier le numéro de commande?"
        order = Order(**order_data)
        if order.status == "confirmed":
            return "Votre commande a déjà été confirmée. Merci!"
        conversation_data = self.db.get_conversation(order_id)
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
        conversation.messages.append({"role": "user", "content": user_input})
        conversation.last_active = datetime.utcnow()
        order_context = self._format_order_context(order, language=language)
        conversation_history = self._format_conversation_history(conversation.messages)
        # Add language instruction and dynamic prompt/examples
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
            )
            prompt = f"""
{language_instruction}

You are a professional and friendly order confirmation agent. Here is the order context:
{order_context}

Conversation history:
{conversation_history}

The client said: \"{user_input}\"

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
"""
        else:
            language_instruction = (
                "Réponds toujours en français, en accord avec la langue du message de l'utilisateur. "
                "L'utilisateur peut passer du français à l'anglais (ou à d'autres langues) à tout moment. "
                f"Langue détectée pour ce message : {language}.\n"
                "RÈGLES STRICTES JSON : Utilise UNIQUEMENT ces clés : message, action, modification, old_item, new_item, item, quantity.\n"
                "NE JAMAIS inventer de nouvelles clés (ex: quantity_new, old_quantity, etc).\n"
                "TOUJOURS utiliser des guillemets doubles pour tous les noms de propriété et valeurs de chaîne.\n"
                "NE JAMAIS utiliser de guillemets simples. NE JAMAIS ajouter de virgule finale.\n"
                "Si un champ n'est pas utile, mets-le à null.\n"
                "Si tu n'es pas sûr, demande une clarification.\n"
                "Si tu ne peux pas comprendre l'intention de l'utilisateur, réponds avec action: 'none'.\n"
                "\n"
                "EXEMPLES NÉGATIFS (À NE PAS FAIRE) :\n"
                "{ 'message': '...', 'action': 'replace', 'modification': { 'old_item': 'Table', 'new_item': 'Chair', 'quantity_new': 2 } }\n"
                "{\"message\": \"...\", 'action': 'replace', 'modification': { 'old_item': 'Table', 'new_item': 'Chair', 'quantity': 2, } }\n"
                "\n"
                "EXEMPLES POSITIFS (À FAIRE) :\n"
                "{\"message\": \"...\", \"action\": \"replace\", \"modification\": {\"old_item\": \"Table\", \"new_item\": \"Chair\", \"quantity\": 2, \"item\": null} }\n"
                "\n"
                "CAS D'USAGE SUPPLÉMENTAIRES :\n"
                "- Ajouter 3 pizzas : {\"message\": \"3 pizzas ont été ajoutées à votre commande.\", \"action\": \"add\", \"modification\": {\"item\": \"Pizza\", \"quantity\": 3, \"old_item\": null, \"new_item\": null}}\n"
                "- Retirer 2 salades : {\"message\": \"2 salades ont été retirées de votre commande.\", \"action\": \"remove\", \"modification\": {\"item\": \"Salade\", \"quantity\": 2, \"old_item\": null, \"new_item\": null}}\n"
                "- Modifier la quantité de burger de 2 à 5 : {\"message\": \"La quantité de burgers est maintenant 5.\", \"action\": \"modify\", \"modification\": {\"item\": \"Burger\", \"quantity\": 5, \"old_item\": null, \"new_item\": null}}\n"
                "- Remplacer 2 lasagnes par 3 pizzas : {\"message\": \"2 lasagnes ont été remplacées par 3 pizzas.\", \"action\": \"replace\", \"modification\": {\"old_item\": \"Lasagne\", \"old_quantity\": 2, \"new_item\": \"Pizza\", \"new_quantity\": 3, \"item\": null}}\n"
                "- Annuler la commande : {\"message\": \"Votre commande a été annulée.\", \"action\": \"cancel\", \"modification\": null}\n"
                "- Demander une clarification : {\"message\": \"Pouvez-vous préciser votre demande ?\", \"action\": \"none\", \"modification\": null}\n"
                "\n"
                "Pour chaque action, explique clairement ce qui a été fait et demande une confirmation si nécessaire.\n"
            )
            prompt = f"""
{language_instruction}

Tu es un agent de confirmation de commande professionnel et sympathique. Voici le contexte de la commande :
{order_context}

Historique de la conversation :
{conversation_history}

Le client a dit : \"{user_input}\"

Réponds avec un JSON strictement de la forme :
{{
  "message": "...",  // Ce que l'agent doit dire au client
  "action": "confirm|modify|cancel|add|remove|replace|none",  // L'action à effectuer (utilise 'none' si aucune action n'est requise)
  "modification": {{ "old_item": "...", "new_item": "...", "item": "...", "quantity": ... }} // si applicable, sinon null
}}
Ne mets aucun texte avant ou après le JSON.

Exemples :
- Si le client dit "Non, c'est tout" ou "Oui", réponds avec l'action de confirmation et un message de clôture final:
{{
  "message": "Merci, votre commande est confirmée. Nous la préparons maintenant.",
  "action": "confirm",
  "modification": null
}}
- Si le client veut ajouter un article, utilise l'action d'ajout:
{{
  "message": "J'ai ajouté 2 vélos supplémentaires à votre commande. Le total a été mis à jour. Est-ce qu'il y a autre chose?",
  "action": "add",
  "modification": {{ "item": "Bicycle", "quantity": 2, "old_item": null, "new_item": null }}
}}
- Si le client veut modifier la quantité d'un article, utilise l'action de modification:
{{
  "message": "Le nombre total de vélos dans votre commande est maintenant 2. Est-ce que tout est en ordre?",
  "action": "modify",
  "modification": {{ "item": "Bicycle", "quantity": 2, "old_item": null, "new_item": null }}
}}
- Si le client veut remplacer un article, utilise l'action de remplacement avec old_item et new_item:
{{
  "message": "Lasagna a été remplacé par Pizza dans votre commande. Y a-t-il autre chose?",
  "action": "replace",
  "modification": {{ "old_item": "Lasagna", "new_item": "Pizza", "item": null, "quantity": null }}
}}
- Si le client dit "Merci", réponds avec l'action 'none':
{{
  "message": "Merci à vous ! N'hésitez pas à nous recontacter si besoin.",
  "action": "none",
  "modification": null
}}
- Si le client demande d'annuler la commande:
{{
  "message": "Votre commande a été annulée.",
  "action": "cancel",
  "modification": null
}}
- Si la demande n'est pas claire:
{{
  "message": "Pouvez-vous préciser votre demande ?",
  "action": "none",
  "modification": null
}}
- Si le client veut retirer un article sans le remplacer:
{{
  "message": "J'ai retiré 1 article de votre commande. Est-ce correct ?",
  "action": "remove",
  "modification": {{ "old_item": "Nom de l'article", "old_qty": 1, "new_item": null, "new_qty": null }}
}}
"""
        try:
            llm_raw = call_llm(prompt, max_tokens=256)
            print("[LLM RAW]", llm_raw)
            json_str = llm_raw.strip()
            # Robust JSON repair/validation
            import re, json
            def repair_json(s):
                # Replace single quotes with double quotes
                s = re.sub(r"'", '"', s)
                # Remove trailing commas before closing braces/brackets
                s = re.sub(r',([ \t\r\n]*[}}\]])', r'\1', s)
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
                mod_match = re.search(r'"modification"\s*:\s*(\{.*?\})', json_str, re.DOTALL)
                data = {"action": None, "modification": None, "message": "[LLM parse fallback]"}
                if action_match:
                    data["action"] = action_match.group(1)
                if mod_match:
                    try:
                        data["modification"] = json.loads(repair_json(mod_match.group(1)))
                    except Exception:
                        data["modification"] = None
            # If the LLM action is confirm, update the order status
            if data.get("action") == "confirm":
                if language.startswith("en"):
                    final_message = "Perfect, your order is confirmed. We are now preparing it. Thank you!"
                else:
                    final_message = "Parfait, votre commande est confirmée. Nous procédons à sa préparation. Merci !"
                
                self.db.update_order(
                    order_id,
                    {
                        "status": "confirmed",
                        "confirmed_at": datetime.utcnow().isoformat()
                    }
                )
                # Move conversation to final state after confirmation
                conversation.messages.append({"role": "assistant", "content": final_message})
                conversation.current_step = "completed"
                self.db.update_conversation(order_id, conversation.dict())
                return final_message
            elif data.get("action") == "cancel":
                self.db.update_order(
                    order_id,
                    {
                        "status": "cancelled",
                        "cancelled_at": datetime.utcnow().isoformat()
                    }
                )
            # Handle action if needed (e.g., apply modification)
            # Only apply modification if not already pending
            if data.get("action") in {"modify", "replace", "remove", "add"} and data.get("modification"):
                applied_successfully = self._apply_llm_modification(order_id, order, data["modification"], data["action"], conversation, user_input)
                if not applied_successfully:
                    if language.startswith("en"):
                        data["message"] = "I'm sorry, I didn't understand that. Could you please clarify your request?"
                    else:
                        data["message"] = "Je suis désolé, je n'ai pas compris. Pouvez-vous clarifier votre demande ?"
                else:
                    updated_order_data = self.db.get_order(order_id)
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
                pass # This line is removed as conversation is passed as an argument
            # Save conversation state
            conversation.messages.append({"role": "assistant", "content": data["message"]})
            self.db.update_conversation(order_id, conversation.dict())
            return data["message"]
        except Exception as e:
            print(f"[LLM PARSE ERROR] {e}")
            raise

    def _normalize_modification(self, modification):
        """
        Normalize any LLM modification dict to a canonical format:
        {"action": ..., "old_item": ..., "new_item": ..., "old_qty": ..., "new_qty": ...}
        For 'replace' with a 'quantity' field, always treat as: remove old_item (1 or specified), add new_item with the specified quantity.
        """
        mod = modification
        norm = {"action": None, "old_item": None, "new_item": None, "old_qty": 1, "new_qty": 1}
        # Handle remove with 'item' key (LLM: {"action": "remove", "item": ..., "quantity": ...})
        if (
            mod.get('action') == 'remove' or
            (
                mod.get('item') and mod.get('quantity') and (
                    mod.get('action') == 'remove' or
                    (mod.get('old_item') is None and mod.get('new_item') is None)
                )
            )
        ):
            norm["action"] = "remove"
            norm["old_item"] = mod.get("item")
            norm["old_qty"] = mod.get("quantity", 1)
            return norm
        # Handle standard add
        if mod.get('action') == 'add' or (mod.get('item') and mod.get('quantity')):
            norm["action"] = "add"
            norm["new_item"] = mod.get("item")
            norm["new_qty"] = mod.get("quantity", 1)
            return norm
        # Handle standard remove (LLM: {"old_item": ..., "quantity": ...})
        if mod.get('old_item') and mod.get('quantity') and not mod.get('new_item') and not mod.get('item'):
            norm["action"] = "remove"
            norm["old_item"] = mod["old_item"]
            norm["old_qty"] = mod["quantity"]
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
        # 8. old_item/new_item (handle 'replace' with quantity)
        if "old_item" in mod and ("new_item" in mod or "item" in mod):
            norm["action"] = "replace"
            norm["old_item"] = mod["old_item"]
            norm["new_item"] = mod.get("new_item") or mod.get("item")
            # If 'quantity' is present, treat as: remove old_item (1 or specified), add new_item with that quantity
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

    def _apply_llm_modification(self, order_id, order, modification, action, conversation, user_input=None) -> bool:
        """Apply the modification as instructed by the LLM. Uses normalized canonical format. Prevents duplicate modifications."""
        norm = self._normalize_modification(modification)
        print(f"[NORM] Normalized modification: {norm}")
        # --- Prevent duplicate modifications ---
        # conversation_data = self.db.get_conversation(order_id) # This line is removed as conversation is passed as an argument
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
                order.items.append(OrderItem(
                    name=norm["new_item"],
                    quantity=norm["new_qty"],
                    price=0,
                    notes='Ajouté via LLM (replace)'))
            applied = True
        elif norm["action"] == "add" and norm["new_item"]:
            existing = next((item for item in order.items if item.name.lower() == norm["new_item"].lower()), None)
            if existing:
                existing.quantity += norm["new_qty"]
            else:
                order.items.append(OrderItem(
                    name=norm["new_item"],
                    quantity=norm["new_qty"],
                    price=0,
                    notes='Ajouté via LLM (add)'))
            applied = True
        elif norm["action"] == "remove" and norm["old_item"]:
            for _ in range(norm["old_qty"]):
                for item in order.items:
                    if item.name.lower() == norm["old_item"].lower():
                        item.quantity -= 1
                        if item.quantity <= 0:
                            order.items = [i for i in order.items if i.name.lower() != norm["old_item"].lower()]
                        break
            applied = True
        if not applied:
            print(f"[WARN] Could not apply normalized modification: {norm}")
            return False
        self.db.update_order(order_id, {
            'items': json.dumps([item.dict() if hasattr(item, 'dict') else item for item in order.items]),
            'total_amount': sum(item.price * item.quantity for item in order.items)
        })
        # --- Store last modification in conversation state ---
        # if conversation: # This line is removed as conversation is passed as an argument
        #     conversation.last_modification = (norm["action"], norm["old_item"], norm["new_item"], norm["old_qty"], norm["new_qty"]) # This line is removed as conversation is passed as an argument
        #     self.db.update_conversation(order_id, conversation.dict()) # This line is removed as conversation is passed as an argument
        return True

    def process_message_basic(self, order_id: str, user_input: str) -> str:
        # The old rule-based logic, unchanged. Just call the previous process_message logic here if fallback is needed.
        # For now, call the previous implementation (copy the old process_message logic here if needed).
        # This is a placeholder for the fallback.
        return "[Fallback] LLM n'a pas compris. (Ancienne logique à implémenter ici.)"

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
            # Ask for explicit final confirmation before proceeding
            conversation.current_step = "final_confirmation"
            return ("Merci, nous récapitulons votre commande. Confirmez-vous que tout est correct avant que nous procédions à la préparation ?", conversation)
        elif current_step == "final_confirmation":
            if any(word in user_input_lower for word in ["oui", "confirme", "ok", "d'accord"]):
                self.db.update_order(
                    order_id=order_context.split('Commande ID: ')[1].split('\n')[0],
                    updates={"status": "confirmed", "confirmed_at": datetime.utcnow().isoformat()})
                return ("Parfait, nous procédons à la préparation de votre commande.", conversation)
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
  "quantity": "...", // Only for add/remove actions, if specified by the user (e.g., "add 2 laptops")
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
            match = re.search(r'(\d+)\s*(.*?)', cleaned_input_lower)
            if match:
                quantity = int(match.group(1))
                item = match.group(2).strip()
                return {
                    'action': 'add',
                    'item': item,
                    'quantity': quantity
                }
            else:
                addition = cleaned_input_lower.replace("ajouter", "").replace("ajoutez", "").replace("ajoute", "").strip()
                return {
                    'action': 'add',
                    'item': addition,
                    'quantity': 1
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
            item_name_to_add = modification['item']
            quantity_to_add = modification.get('quantity', 1)
            existing_item = next((item for item in order.items if item.name.lower() == item_name_to_add.lower()), None)
            if existing_item:
                existing_item.quantity += quantity_to_add
            else:
                price = 0
                # Try to find a similar item to get its price from the current order items
                for item in order.items:
                    if item.name.lower() == item_name_to_add.lower():
                        price = item.price
                        break
                order.items.append(OrderItem(
                    name=item_name_to_add,
                    quantity=quantity_to_add,
                    price=price,
                    notes='Ajouté lors de la confirmation'
                ))
        self.db.update_order(order_id, {
            'items': json.dumps([item.dict() if hasattr(item, 'dict') else item for item in order.items]),
            'total_amount': sum(item.price * item.quantity for item in order.items)
        })
        print(f"[DEBUG] _process_modification: applied modification, clearing modification_request")
        conversation.modification_request = None
        conversation.current_step = "confirming_items"
        updated_context = self._format_order_context(order, language=self._infer_language_from_conversation(conversation))
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
        if current_step == "final_confirmation" and any(word in user_input.lower() for word in ["oui", "confirme", "ok", "d'accord"]):
            return "completed"
        return step_transitions.get(current_step, current_step)
    
    def reset_conversation(self, order_id: str) -> dict:
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
            return {"message": "Commande non trouvée"}
        order = Order(**order_data)
        order_context = self._format_order_context(order, language=self._infer_language_from_conversation(conversation))
        # Only use the string part of the tuple returned by _generate_response
        response, _ = self._generate_response(
            order_context,
            "greeting",
            "Pas d'historique",
            "Bonjour",
            conversation=conversation
        )
        return {
            "message": "Conversation réinitialisée. " + response
        }   

    def start_conversation(self, order_id: str, language: str = "fr") -> str:
        order_data = self.db.get_order(order_id)
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
        self.db.update_conversation(order_id, conversation.dict())
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

    def _infer_language_from_conversation(self, conversation):
        # Try to infer language from the last user message
        import re
        for msg in reversed(conversation.messages):
            if msg['role'] == 'user':
                text = msg['content'].strip()
                # Heuristic: if message is a single word like 'yes', 'no', etc., check for English/French
                if re.fullmatch(r"yes|no|ok|correct|thanks|thank you", text.lower()):
                    return 'en'
                if re.fullmatch(r"oui|non|d'accord|merci|parfait", text.lower()):
                    return 'fr'
                # Otherwise, use a simple heuristic: more English or French words
                en_words = ['yes', 'no', 'ok', 'correct', 'thanks', 'thank you', 'please', 'order', 'remove', 'add']
                fr_words = ['oui', 'non', "d'accord", 'merci', 'commande', 'retirer', 'ajouter', 'supprimer']
                en_count = sum(1 for w in en_words if w in text.lower())
                fr_count = sum(1 for w in fr_words if w in text.lower())
                if en_count > fr_count:
                    return 'en'
                if fr_count > en_count:
                    return 'fr'
                # Fallback: if message contains mostly ascii, guess English
                if len([c for c in text if ord(c) < 128]) / max(1, len(text)) > 0.9:
                    return 'en'
                return 'fr'
        return 'fr'