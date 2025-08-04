# Business Admin Panel Feature - MVP with WooCommerce Integration

This document outlines the complete plan for implementing a business admin panel with WooCommerce order detection, designed to be completed within one week.

## 1. Overview

The goal is to create a complete order confirmation system where:

1. Customers make orders on WooCommerce sites
2. Browser extension detects order details
3. Customer confirms order via Messenger
4. Order appears in business owner's admin panel

This MVP version prioritizes speed of development while maintaining core functionality using session-based authentication, API keys for order submission, and a simplified database structure.

## 2. Complete User Flow

1. **Business Setup**: Business owner registers and gets API key + site ID
2. **WooCommerce Order**: Customer completes purchase on WooCommerce site
3. **Order Detection**: Browser extension detects order details from confirmation page
4. **Messenger Confirmation**: Customer confirms order details via Messenger
5. **Order Submission**: Extension submits confirmed order to API using business API key
6. **Admin Notification**: Order appears in business owner's admin panel

## 3. Database Schema Changes

### Modify existing `orders` table

Add new columns to the existing `orders` table:

| Column        | Type          | Description                                     |
| ------------- | ------------- | ----------------------------------------------- |
| `business_id` | `String(100)` | Business identifier (matches business owner)    |
| `site_url`    | `String(255)` | The WooCommerce site URL where order originated |
| `site_id`     | `String(100)` | Unique identifier for the specific site         |

### New `business_users` table

| Column          | Type          | Description                                      |
| --------------- | ------------- | ------------------------------------------------ |
| `id`            | `Integer`     | Primary Key (auto-increment)                     |
| `username`      | `String(50)`  | Unique username for login                        |
| `password_hash` | `String(255)` | Bcrypt hashed password                           |
| `business_id`   | `String(100)` | Business identifier (matches orders.business_id) |
| `api_key`       | `String(100)` | Unique API key for order submissions             |
| `created_at`    | `DateTime`    | Timestamp of creation                            |

## 4. API Endpoints

### Business Authentication & Management

- `POST /api/business/login`: Authenticate business user

  - Input: `username`, `password`
  - Output: `token`, `business_id`
  - Uses bcrypt for password verification

- `GET /api/business/orders`: Get all orders for authenticated business

  - Requires: Bearer token authentication
  - Filters orders by `business_id`
  - Returns: List of orders with site information

- `GET /api/business/orders/{order_id}`: Get specific order details

  - Requires: Bearer token authentication
  - Validates order belongs to authenticated business
  - Returns: Complete order information including conversation data

- `GET /api/business/api-key`: Get API key for authenticated business
  - Requires: Bearer token authentication
  - Returns: API key for configuring extension

### Order Submission (for Extension)

- `POST /api/orders/submit`: Submit confirmed order from WooCommerce
  - Headers: `X-API-Key: {business_api_key}`
  - Input: `site_id`, `site_url`, `order_data`, `customer_info`
  - Validates API key and creates order record
  - Returns: Order confirmation with order ID

## 5. Authentication Systems

### Business Admin Authentication

- Session-based authentication for admin panel
- Bearer token for API access
- Client-side token storage using localStorage

### Order Submission Authentication

- API key validation for extension submissions
- Business-level data isolation
- Site-specific order routing

## 6. Frontend - Business Admin Panel

Single-page application structure:

### File Structure:

```
/static/
  ├── admin.html    # Main admin interface
  ├── admin.css     # Styling
  └── admin.js      # Application logic
```

### Admin Panel Features:

- **Login Interface**: Username/password authentication
- **Orders Dashboard**: Table view of all business orders with site information
- **Order Details**: Modal popup showing complete order and conversation data
- **API Settings**: Display API key and site registration
- **Site Management**: Register new WooCommerce sites with site IDs

## 7. Browser Extension Updates

### WooCommerce Integration:

- **Order Detection**: Identify WooCommerce order confirmation pages
- **Data Extraction**: Parse order details (items, prices, customer info, order ID)
- **API Configuration**: Store business API key and site ID in extension settings
- **Order Submission**: POST confirmed orders to business API

### Extension Flow:

1. Detect WooCommerce order success page
2. Extract order details from DOM
3. Prompt customer for Messenger confirmation
4. Submit order to API with business credentials
5. Show confirmation to customer

## 8. Implementation Timeline (6 Days, 5 Hours Each)

### Day 1: Database & Core Backend (5 hours)

- **Database Schema**: Update orders table, create business_users table with migration
- **API Key System**: Generate and validate API keys
- **Basic Models**: Create BusinessUser model with API key field

### Day 2: Authentication APIs (5 hours)

- **Business Authentication**: Login endpoint with session management
- **Password Security**: Bcrypt hashing and validation
- **Session Middleware**: Token validation for protected endpoints

### Day 3: Business Management APIs (5 hours)

- **Orders API**: Get orders filtered by business_id
- **Order Details API**: Individual order retrieval with validation
- **API Key Endpoint**: Return API key for authenticated business

### Day 4: Order Submission & Extension (5 hours)

- **Order Submission API**: Accept orders from extension with API key auth
- **WooCommerce Detection**: Update extension for order page recognition
- **Extension Integration**: API key configuration and order posting

### Day 5: Admin Panel Frontend (5 hours)

- **Core UI**: Login form, dashboard layout, orders table
- **JavaScript Logic**: AdminApp class with authentication flow
- **API Integration**: Connect all frontend components to backend APIs

### Day 6: Complete Integration & Testing (5 hours)

- **Order Details Modal**: Full order information display
- **API Settings UI**: Show API key and basic site management
- **End-to-End Testing**: Full WooCommerce → Extension → Admin flow
- **Basic Styling**: Minimal responsive design for usability

## 9. Technical Implementation

### Backend Dependencies:

- `python-jose[cryptography]`: Token handling
- `passlib[bcrypt]`: Password hashing
- FastAPI security utilities

### API Key Generation:

```python
import secrets
api_key = secrets.token_urlsafe(32)
```

### Frontend Architecture:

- Vanilla JavaScript with class-based structure
- Fetch API for all backend communication
- LocalStorage for session persistence
- Modal-based UI for order details

### Extension Integration:

- WooCommerce DOM parsing for order data
- Configuration UI for API key and site ID
- Error handling for API submission failures

## 10. Business Onboarding Process

1. **Registration**: Business creates account in admin panel
2. **API Key**: System generates unique API key automatically
3. **Site Registration**: Business adds their WooCommerce site with custom site ID
4. **Extension Setup**: Business configures browser extension with API key and site ID
5. **Testing**: Verify complete flow with test order

## 11. Security Considerations

- API key validation for all order submissions
- Business-level data isolation (orders only visible to correct business)
- Session token expiration for admin panel
- Input validation for all WooCommerce order data
- Rate limiting on order submission endpoint

## 12. Future Enhancements

**Phase 2:**

- Multiple API keys per business
- Advanced WooCommerce integration (webhooks)
- Real-time order notifications
- Analytics dashboard

**Phase 3:**

- Support for other e-commerce platforms
- Mobile admin app
- Advanced reporting features
- Webhook integrations for third-party systems

This plan provides a complete order confirmation system that bridges WooCommerce, Messenger confirmation, and business administration in a single integrated solution.
