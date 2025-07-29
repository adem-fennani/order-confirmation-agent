# Purchase Detection and Data Extraction Strategy

This document outlines potential strategies for implementing the automatic detection of online purchases and the extraction of order details. This is a critical first step in the order confirmation process.

## 1. Core Requirements

The system must be able to:
1.  Detect when a user completes a purchase on an e-commerce website (including Facebook Marketplace).
2.  Extract the following information from the purchase:
    *   A list of items purchased.
    *   The quantity of each item.
    *   The price of each item.
    *   The total price of the order.
3.  Initiate the order confirmation flow with the extracted data.

## 2. Proposed Implementation Strategies

Below are the primary methods considered for implementing this feature. Each has its own set of advantages and disadvantages.

### Method 1: Browser Extension (Recommended Approach)

This approach involves creating a browser extension that the user would install. The extension would monitor browsing activity for signs of a completed purchase.

#### How it Works:

1.  **URL Matching:** The extension would maintain a list of URL patterns for supported e-commerce sites (e.g., `facebook.com/marketplace/`, `amazon.com/gp/buy/spc/handlers/display.html`).
2.  **Content Scraping:** When the user navigates to a URL that matches a "purchase complete" or "thank you" page pattern, the extension's content script would activate.
3.  **Data Extraction:** The content script would parse the HTML of the page to find and extract the order details (items, quantities, prices). This would require custom selectors for each supported site.
4.  **API Communication:** The extracted data would be securely sent to the Order Confirmation Agent's API to create a new order and begin the confirmation process.

#### Pros:

*   **Real-time:** Detection happens immediately after the purchase.
*   **Broad Compatibility:** Can be adapted to work with almost any website, even those without official APIs.
*   **Rich Data:** Can extract a wide range of data present on the confirmation page.

#### Cons:

*   **User Friction:** Requires the user to install a browser extension.
*   **Maintenance:** The web scrapers are brittle. If a website changes its layout, the scraper for that site will break and need to be updated.
*   **Security & Privacy:** Users may have concerns about an extension reading their browsing data. The extension must be built with a strong focus on security and transparency, only activating on specific, known e-commerce pages.
*   **Development Complexity:** Requires development and maintenance for multiple browsers (Chrome, Firefox, etc.).

### Method 2: Email Parsing (Alternative Approach)

This method involves the user granting the agent permission to access their email inbox (e.g., via the Gmail or Outlook APIs). The agent would then scan for order confirmation emails.

#### How it Works:

1.  **Authorization:** The user would connect their email account to the agent via an OAuth flow.
2.  **Email Scanning:** A background service would periodically scan the user's inbox for emails that appear to be order confirmations (e.g., by looking at the sender, subject line, or keywords).
3.  **Content Parsing:** When a confirmation email is found, the service would parse the email's content (HTML or plain text) to extract the order details.
4.  **API Communication:** The extracted data is sent to the agent's API to create the order.

#### Pros:

*   **Reliable:** Order confirmation emails are a standard and relatively stable part of the online shopping process.
*   **No User Installation:** Beyond the initial authorization, there is nothing for the user to install on their devices.
*   **Centralized Logic:** All parsing logic is on the backend, making it easier to update and maintain.

#### Cons:

*   **Privacy:** This is a major concern. Many users will be hesitant to grant access to their email inboxes.
*   **Complexity of Parsing:** Email templates vary wildly between retailers. A robust and flexible parsing system would be needed.
*   **Not Real-time:** There can be a delay between the purchase and when the confirmation email is received and processed.

### Method 3: Webhook/API Integration (Future Expansion)

This method is not a general solution for third-party sites but is the ideal solution for platforms we can partner with or for our own e-commerce systems.

#### How it Works:

The e-commerce platform would be configured to send a webhook to our agent's API whenever a new order is created. The webhook payload would contain the structured order data (e.g., in JSON format).

#### Pros:

*   **Most Reliable:** The data is structured, accurate, and sent directly from the source.
*   **Real-time:** The notification is instantaneous.
*   **Secure:** No need to access user's personal accounts or data.

#### Cons:

*   **Limited Applicability:** Only works for platforms that support webhooks and that we can integrate with. It does not solve the problem of detecting purchases from a wide range of external websites.

## 3. Recommendation

For the initial implementation, the **Browser Extension (Method 1)** is the recommended approach. It strikes the best balance between feasibility for a wide range of sites and providing a real-time user experience.

While the maintenance of scrapers is a challenge, it is a solvable one. We can start with support for a few major websites (like Facebook Marketplace) and expand over time. The privacy and security aspects must be handled with extreme care, with clear communication to the user about what the extension does and when it is active.

**Email Parsing (Method 2)** should be considered as a powerful future alternative or a complementary feature for users who are comfortable with the privacy trade-offs.
