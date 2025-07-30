# Facebook Marketplace Integration Strategy

This document outlines the implementation plan for capturing order data from Facebook Marketplace and integrating it into the Order Confirmation Agent.

## 1. Objective

Automatically create a new order in our system when the user makes a purchase on Facebook Marketplace. This will trigger the confirmation conversation with the user.

## 2. Technical Approach: Browser Extension as a Webhook

Direct server-to-server webhooks for individual user purchases on Facebook Marketplace are not available. Instead, we will create a browser extension that the user installs. This extension will act as a "client-side webhook," detecting when a purchase is completed and sending the order data to our API.

### How It Works

1.  **Installation**: The user installs a simple browser extension (e.g., for Chrome).

2.  **URL Monitoring**: A background script in the extension will monitor the user's browser tabs for URLs matching Facebook Marketplace's post-purchase or receipt pages. The specific URL pattern will need to be identified (e.g., `https://www.facebook.com/marketplace/buy/confirmation/...` or similar).

3.  **Content Injection**: When a matching URL is detected, the extension injects a `content_script.js` into that specific page.

4.  **Data Scraping**: The content script will securely parse the page's HTML to extract the necessary order details:

    - Item Name(s)
    - Item Quantity
    - Item Price(s)
    - Total Order Amount
    - (Optional) Seller Name

5.  **API Call**: The content script sends the extracted data to the background script, which then makes a secure `POST` request to our existing `/orders` API endpoint. This creates the new order in our database.

### Data Flow

```
[User completes purchase on FB Marketplace]
        |
        v
[Navigates to Confirmation Page]
        |
        v
[Browser Extension detects URL and injects script]
        |
        v
[Content Script scrapes order data from HTML]
        |
        v
[Extension sends data via POST to /orders API]
        |
        v
[API creates order in SQLite DB]
        |
        v
[Agent starts confirmation flow (SMS/Messenger)]
```

## 3. Implementation Details

### Browser Extension Components

We will create a new directory `src/extension` for the browser extension files.

- **`manifest.json`**: The core configuration file for the extension.

  - Defines permissions (`tabs`, `storage`, host permissions for `https://www.facebook.com/*`).
  - Registers the `background.js` script.
  - Defines the `content_script.js` and the URL patterns it should activate on.

- **`background.js`**: The background service worker.

  - Listens for tab updates to detect navigation to the target URLs.
  - Receives scraped data from the content script.
  - Handles the `fetch` call to our API's `/orders` endpoint.

- **`content_script.js`**: The script that runs on the Facebook Marketplace page.
  - Contains the logic for querying the DOM (e.g., using `document.querySelectorAll`) to find and extract the order information.
  - Sends the extracted data back to the `background.js` script.

### API Integration

The extension will use the existing `POST /orders` endpoint defined in `src/api/routes.py`. The JSON payload sent by the extension will conform to the `CreateOrder` schema, for example:

```json
{
  "customer_name": "John Doe", // This may need to be pre-configured or fetched
  "customer_phone": "+15551234567", // This will need to be pre-configured
  "items": [{ "name": "Vintage Armchair", "quantity": 1, "price": 75.0 }],
  "total_amount": 75.0,
  "notes": "Order automatically detected from Facebook Marketplace."
}
```

**Note**: Customer details like name and phone number are not typically available on the confirmation page. For the initial version, these will need to be configured by the user within the extension's settings page.

## 4. Security & Privacy

- **Minimal Permissions**: The extension will request the minimum permissions necessary to function.
- **Host Permissions**: It will only have permission to access and run on `facebook.com` pages, and will only inject the content script on the specific marketplace confirmation URLs.
- **Transparency**: We must be fully transparent with the user about what the extension does and why it needs the permissions it requests.
