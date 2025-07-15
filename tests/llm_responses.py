import json

def get_llm_response(test_name):
    responses = {
        "test_start_conversation_english": {
            "message": "Hello John Doe, I'm confirming your order. You ordered 1x laptop for a total of 1200.0€. Is this correct?",
            "action": "none",
            "modification": None
        },
        "test_cancel_order": {
            "message": "Your order has been cancelled.",
            "action": "cancel",
            "modification": None
        },
        "test_confirm_order_with_yes_or_oui": {
            "message": "Great, your order is confirmed! We are preparing it now.",
            "action": "confirm",
            "modification": None
        },
        "test_remove_item_english": {
            "message": "The chairs have been removed from your order. Now your order consists of 2x Table (20.0€ each). The total is now 40.0€. Is this correct?",
            "action": "modify",
            "modification": { "old_item": "Chair", "item": None, "quantity": None }
        },
        "test_remove_item_french": {
            "message": "The chairs have been removed from your order. Now your order consists of 2x Table (20.0€ each). The total is now 40.0€. Is this correct?",
            "action": "modify",
            "modification": { "old_item": "Chaise", "item": None, "quantity": None }
        },
        "test_add_item_english": {
            "message": "I've added 3 chairs to your order. The new total is 70.0€. Is there anything else?",
            "action": "add",
            "modification": { "item": "Chair", "quantity": 3, "old_item": None, "new_item": None }
        },
        "test_add_item_french": {
            "message": "J'ai ajouté 3 chaises à votre commande. Le nouveau total est de 70.0€. Y a-t-il autre chose?",
            "action": "add",
            "modification": { "item": "Chaise", "quantity": 3, "old_item": None, "new_item": None }
        },
        "test_replace_item_english": {
            "message": "Lasagna has been replaced by Salad in your order. The total has been updated. The new total is 44.0€. Is there anything else?",
            "action": "replace",
            "modification": { "old_item": "Lasagna", "new_item": "Salad", "item": None, "quantity": None }
        },
        "test_replace_item_french": {
            "message": "La lasagne a été remplacée par de la salade dans votre commande. Le total a été mis à jour. Le nouveau total est de 44.0€. Y a-t-il autre chose?",
            "action": "replace",
            "modification": { "old_item": "Lasagne", "new_item": "Salade", "item": None, "quantity": None }
        },
        "test_modify_quantity_english": {
            "message": "I've updated the number of tables in your order to 5. The total has been updated as well. Is there anything else I can help you with?",
            "action": "modify",
            "modification": { "item": "Table", "quantity": 5, "old_item": "Table", "new_item": None }
        },
        "test_modify_quantity_french": {
            "message": "J'ai mis à jour le nombre de tables dans votre commande à 5. Le total a également été mis à jour. Y a-t-il autre chose que je puisse faire pour vous?",
            "action": "modify",
            "modification": { "item": "Table", "quantity": 5, "old_item": "Table", "new_item": None }
        },
        "test_cancel_order_english": {
            "message": "Your order has been cancelled.",
            "action": "cancel",
            "modification": None
        },
        "test_cancel_order_french": {
            "message": "Votre commande a été annulée.",
            "action": "cancel",
            "modification": None
        },
        "test_ambiguous_request_english": {
            "message": "I'm not sure I understand. Could you please clarify your request?",
            "action": "none",
            "modification": None
        },
        "test_ambiguous_request_french": {
            "message": "Je ne suis pas sûr de comprendre. Pouvez-vous préciser votre demande?",
            "action": "none",
            "modification": None
        },
        "test_language_switch_mid_conversation": {
            "message": "I have added one more pizza to your order. Your total is now 15€. Is there anything else to add?",
            "action": "add",
            "modification": { "item": "Pizza", "quantity": 1, "old_item": None, "new_item": None }
        }
    }
    return json.dumps(responses[test_name])