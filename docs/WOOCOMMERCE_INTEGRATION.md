# WooCommerce Integration Guide

This guide explains how to integrate your WooCommerce store with the Order Confirmation Agent, allowing for automated order detection, conversational updates, and synchronization of order details back to your WooCommerce store.

## Introduction

The Order Confirmation Agent can interact with your WooCommerce store in two primary ways:

1.  **Browser Extension**: Automatically detects new orders from your WooCommerce checkout confirmation page.
2.  **Webhooks**: Receives real-time notifications for new orders created directly on your WooCommerce store.

Once an order is in the system, the AI agent can engage with the customer to confirm or modify the order. Any modifications (e.g., quantity changes, item additions/removals) confirmed by the customer will be automatically pushed back and updated on the original WooCommerce order.

## Prerequisites

Before you begin, ensure you have:

*   A running WooCommerce store.
*   Administrator access to your WooCommerce store to generate API keys and set up webhooks.
*   The Order Confirmation Agent backend server running and accessible (e.g., via `ngrok` for local development).

## Setup

### 1. Generate WooCommerce API Keys

To allow the Order Confirmation Agent to update orders on your WooCommerce store, you need to generate a Consumer Key and Consumer Secret with Read/Write permissions.

1.  Log in to your WordPress admin panel.
2.  Navigate to **WooCommerce > Settings > Advanced > REST API**.
3.  Click **Add key**.
4.  Provide a **Description** (e.g., "Order Confirmation Agent").
5.  Select the **User** for whom the key will be generated (e.g., an administrator).
6.  Set the **Permissions** to `Read/Write`.
7.  Click **Generate API key**.
8.  **Copy the Consumer Key and Consumer Secret**. You will need these for your `.env` file. **Keep them secure, as they will only be shown once.**

### 2. Configure Environment Variables

Add the following variables to your `.env` file in the `config` directory of your Order Confirmation Agent project:

```
WOOCOMMERCE_STORE_URL=https://your-woocommerce-store.com
WOOCOMMERCE_CONSUMER_KEY=ck_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
WOOCOMMERCE_CONSUMER_SECRET=cs_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

*   Replace `https://your-woocommerce-store.com` with the actual URL of your WooCommerce store.
*   Replace `ck_...` and `cs_...` with the Consumer Key and Consumer Secret you generated in the previous step.

### 3. Set up WooCommerce Webhooks (for New Order Detection)

To automatically receive new orders from your WooCommerce store, you need to configure a webhook.

1.  Log in to your WordPress admin panel.
2.  Navigate to **WooCommerce > Settings > Advanced > Webhooks**.
3.  Click **Add webhook**.
4.  Provide a **Name** (e.g., "Order Confirmation Agent - New Order").
5.  Set the **Status** to `Active`.
6.  Set the **Topic** to `Order created`.
7.  Set the **Delivery URL** to your Order Confirmation Agent's webhook endpoint. If you are using `ngrok` for local development, this would look like:
    `https://<your-ngrok-subdomain>.ngrok.io/orders/webhook`
    Replace `<your-ngrok-subdomain>` with your actual ngrok URL.
8.  Set the **Secret** (optional but recommended for security). If you set a secret, you will need to configure your FastAPI application to verify it. (Note: The current agent implementation does not verify this secret, but it's good practice for future enhancements).
9.  Click **Save webhook**.

## Usage

### Receiving New Orders

*   **Via Browser Extension**: Ensure the browser extension is installed and configured in your browser. When a customer completes an order on your WooCommerce store, the extension will automatically detect the order details from the confirmation page and send them to your Order Confirmation Agent backend.
*   **Via Webhook**: Once the webhook is set up, any new order placed on your WooCommerce store will automatically trigger the webhook, sending the order details to your Order Confirmation Agent backend.

In both cases, the Order Confirmation Agent will create the order in its local database and initiate a confirmation conversation with the customer (e.g., via Facebook Messenger).

### Updating Orders in WooCommerce

When a customer interacts with the AI agent and confirms modifications to their order (e.g., changing quantities, adding or removing items), the Order Confirmation Agent will:

1.  Update the order details in its local database.
2.  Automatically send an update request to your WooCommerce store's REST API, synchronizing the changes back to the original order on your website. This ensures that your WooCommerce order reflects the latest confirmed details from the customer conversation.

## Troubleshooting

*   **Orders not appearing in the agent**:
    *   **Check Webhook Status**: In WooCommerce, go to **WooCommerce > Settings > Advanced > Webhooks** and ensure your webhook is `Active` and has a green checkmark. Check the "Logs" section for any delivery failures.
    *   **Backend Server**: Ensure your Order Confirmation Agent backend server is running and accessible from the internet (if using webhooks).
    *   **Ngrok**: If using `ngrok`, ensure it's running and its URL is correctly configured in the WooCommerce webhook.
    *   **Browser Extension**: If relying on the extension, ensure it's installed, enabled, and its settings (backend URL) are correct.
*   **Order updates not synchronizing to WooCommerce**:
    *   **API Keys**: Double-check your `WOOCOMMERCE_CONSUMER_KEY` and `WOOCOMMERCE_CONSUMER_SECRET` in your `.env` file. Ensure they have `Read/Write` permissions.
    *   **Store URL**: Verify that `WOOCOMMERCE_STORE_URL` in your `.env` file is correct and accessible from your backend server.
    *   **Backend Logs**: Check your Order Confirmation Agent's backend logs for any errors related to `WooCommerceService` when an order is confirmed or modified.
*   **"Invalid JSON" or "Expecting ',' delimiter" errors in backend logs**:
    *   This usually indicates an issue with the LLM's output not being perfectly valid JSON. While the agent has some robust parsing, occasional malformed output can occur. Ensure your LLM prompt instructions are clear about JSON formatting (double quotes, no trailing commas).
    *   If this persists, it might require further debugging of the LLM's response parsing in `src/agent/agent.py`.
