# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-07-31

### Added

- **Browser Extension**: A Chrome extension that automatically detects order details from e-commerce confirmation pages (e.g., Facebook Marketplace) and sends them to the agent.
- **Facebook Messenger Integration**: The agent now automatically sends order confirmation messages to users on Facebook Messenger upon order creation.
- **Automated End-to-End Workflow**: A complete, automated cycle from order detection to final confirmation via Messenger.
- **Extension Settings**: The browser extension includes a settings page to configure user details (name and phone number).

### Features

- **Automated Order Detection**: Seamlessly captures order information from websites without manual data entry.
- **Proactive Messenger Conversation**: Initiates the confirmation process on Messenger as soon as an order is detected.
- **User-configurable Extension**: Users can easily set their personal information for accurate order creation.

### Technical Details

- A new `extension` module in the `src` directory containing the Chrome extension's source code.
- A dedicated `facebook_routes.py` for handling Messenger webhooks.
- The `create_order` endpoint now triggers an automatic message via the `FacebookService`.

### Fixed

- The `content_script.js` now correctly injects a button for manual data extraction on test pages.

### Known Issues

- The Facebook Messenger integration currently relies on a hardcoded `FACEBOOK_PSID` for sending messages.
- The browser extension's selectors for scraping order data may need to be updated if the target websites change their layout.

---

## [0.2.0] - 2025-07-23

### Added

- **SMS Integration**: The agent can now send and receive order confirmation messages via SMS using Twilio.
- **Web / SMS Mode**: Users can choose to confirm orders via the web interface or through SMS, making the system more flexible and accessible.
- **Twilio Messaging Service Support**: Integration with Twilio’s Messaging Service for reliable SMS delivery and webhook handling.

### Features

- **Order Confirmation via SMS**: Customers can interact with the agent directly from their phones.
- **Dual Mode Support**: Seamless switching between web chat and SMS for order confirmation.
- **All previous features**: Order management, LLM-powered conversation, multilingual support, address collection, order modifications, and REST API endpoints remain available.

### Technical Details

- Twilio Messaging Service integration for SMS sending and receiving.
- Backend logic to handle both web and SMS confirmation flows.
- Environment variable support for Twilio configuration.

### Fixed

- Improved error handling for SMS delivery failures.
- Minor bug fixes to support SMS workflows.

### Known Issues

- **Carrier Short Code Flagging**: SMS messages may sometimes be flagged by the carrier as 'Short code', making it impossible for recipients to reply to the SMS.
- Still in development/prototype phase.
- Limited error handling for edge cases.
- No authentication/authorization system.

### Security

- Input validation and sanitization
- SQL injection prevention
- Error message sanitization
