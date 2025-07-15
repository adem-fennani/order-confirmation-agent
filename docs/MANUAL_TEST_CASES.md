# Manual Test Scenarios for Order Confirmation Agent

Below are manual test scenarios to validate the agent's behavior for various user intents, languages, and edge cases. For each scenario, start a new order and follow the steps. Observe the agent's responses and ensure they match the expected behavior.

---

## 1. Basic Order Confirmation (French)

- **Step 1:** Start a new order with 2x Chair, 2x Table.
- **Step 2:** Agent greets in French and summarizes the order.
- **Step 3:** User replies: `Oui`
- **Expected:** Agent confirms the order in French.

## 2. Basic Order Confirmation (English)

- **Step 1:** Start a new order with 2x Chair, 2x Table.
- **Step 2:** Agent greets in English and summarizes the order.
- **Step 3:** User replies: `yes`
- **Expected:** Agent confirms the order in English.

## 3. Remove Item (English)

- **Step 1:** Start a new order with 2x Chair, 2x Table.
- **Step 2:** User: `I want to remove the chairs from the order`
- **Expected:** Agent removes chairs, updates summary in English, asks for confirmation.
- **Step 3:** User: `yes`
- **Expected:** Agent confirms in English.

## 4. Remove Item (French)

- **Step 1:** Start a new order with 2x Chaise, 2x Table.
- **Step 2:** User: `Je veux supprimer les chaises de la commande`
- **Expected:** Agent removes chaises, updates summary in French, asks for confirmation.
- **Step 3:** User: `oui`
- **Expected:** Agent confirms in French.

## 5. Add Existing Item (English)

- **Step 1:** Start a new order with 2x Table,1x Chair.
- **Step 2:** User: `Add 3 more chairs`
- **Expected:** Agent increases the quantity of chairs, updates summary in English, asks for confirmation.
- **Step 3:** User: `yes`
- **Expected:** Agent confirms in English.

## 6. Add Existing Item (French)

- **Step 1:** Start a new order with 2x Table, 1x Chaise.
- **Step 2:** User: `Ajouter 3 chaises de plus`
- **Expected:** Agent increases the quantity of chaises, updates summary in French, asks for confirmation.
- **Step 3:** User: `oui`
- **Expected:** Agent confirms in French.

## 7. Replace Item (English)

- **Step 1:** Start a new order with 2x Pizza, 2x Lasagna.
- **Step 2:** User: `Replace lasagna with salad`
- **Expected:** Agent replaces lasagna with salad, updates summary in English, asks for confirmation.
- **Step 3:** User: `yes`
- **Expected:** Agent confirms in English.

## 8. Replace Item (French)

- **Step 1:** Start a new order with 2x Pizza, 2x Lasagne.
- **Step 2:** User: `Remplacer lasagne par salade`
- **Expected:** Agent replaces lasagne with salade, updates summary in French, asks for confirmation.
- **Step 3:** User: `oui`
- **Expected:** Agent confirms in French.

## 9. Modify Quantity (English)

- **Step 1:** Start a new order with 2x Table.
- **Step 2:** User: `Change the number of tables to 5`
- **Expected:** Agent updates quantity, updates summary in English, asks for confirmation.
- **Step 3:** User: `yes`
- **Expected:** Agent confirms in English.

## 10. Modify Quantity (French)

- **Step 1:** Start a new order with 2x Table.
- **Step 2:** User: `Changer le nombre de tables à 5`
- **Expected:** Agent updates quantity, updates summary in French, asks for confirmation.
- **Step 3:** User: `oui`
- **Expected:** Agent confirms in French.

## 11. Cancel Order (English)

- **Step 1:** Start a new order.
- **Step 2:** User: `I want to cancel my order`
- **Expected:** Agent cancels the order and confirms in English.

## 12. Cancel Order (French)

- **Step 1:** Start a new order.
- **Step 2:** User: `Je veux annuler ma commande`
- **Expected:** Agent cancels the order and confirms in French.

## 13. Ambiguous Request (English)

- **Step 1:** Start a new order.
- **Step 2:** User: `Can you help?`
- **Expected:** Agent asks for clarification in English.

## 14. Ambiguous Request (French)

- **Step 1:** Start a new order.
- **Step 2:** User: `Pouvez-vous m'aider ?`
- **Expected:** Agent asks for clarification in French.

## 15. Language Switch Mid-Conversation

- **Step 1:** Start a new order in French.
- **Step 2:** User: `Je veux ajouter une pizza`
- **Expected:** Agent responds in French.
- **Step 3:** User: `Remove the pizza`
- **Expected:** Agent responds in English.

---

Repeat these scenarios for different item names, quantities, and user phrasings to ensure robustness.
