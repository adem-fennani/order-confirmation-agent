
# Business Admin Panel Feature

This document outlines the plan for implementing a business admin panel, allowing businesses to access and manage their orders.

## 1. Overview

The goal is to create a secure area for businesses to view their orders and conversations. This will be achieved by extending the existing FastAPI application with new models, API endpoints, and a dedicated admin page.

## 2. Database Schema Changes

We will add two new tables to the database: `businesses` and `users`. We will also add a `business_id` to the `orders` table.

### `businesses` table

| Column | Type | Description |
|---|---|---|
| `id` | `String(50)` | Primary Key |
| `name` | `String(100)` | Name of the business |
| `api_key` | `String(100)` | Unique API key for the business |
| `site_id` | `String(100)` | Unique ID for the business's site |
| `created_at` | `DateTime` | Timestamp of creation |

### `users` table

| Column | Type | Description |
|---|---|---|
| `id` | `Integer` | Primary Key |
| `username` | `String(50)` | Unique username for login |
| `password_hash` | `String(100)` | Hashed password |
| `business_id` | `String(50)` | Foreign key to `businesses` table |

### `orders` table modification

Add a new column to the existing `orders` table:

| Column | Type | Description |
|---|---|---|
| `business_id` | `String(50)` | Foreign key to `businesses` table |

## 3. API Endpoints

We will create the following new API endpoints:

### Authentication

*   `POST /api/v1/business/register`: Register a new business and user.
*   `POST /api/v1/business/login`: Log in a user and return a JWT token.

### Business Admin

*   `GET /api/v1/business/orders`: Get all orders for the authenticated business.
*   `GET /api/v1/business/orders/{order_id}`: Get a specific order and its conversation.
*   `GET /api/v1/business/api_key`: Get the API key and site ID for the authenticated business.

## 4. Frontend

We will create a new admin page at `/static/admin.html`. This page will include:

*   A login form.
*   A dashboard to display a list of orders.
*   A detail view to show the order details and conversation history.
*   A section to display the business's API key and site ID.

## 5. Implementation Steps

1.  **Create new database models:** Implement the `Business` and `User` models in `src/agent/database/models.py`.
2.  **Update `OrderModel`:** Add the `business_id` to the `OrderModel`.
3.  **Create database migration:** Write a script to update the database schema.
4.  **Implement API endpoints:** Create the new API endpoints in a new file `src/api/business_routes.py`.
5.  **Implement authentication:** Use JWT for securing the business admin endpoints.
6.  **Create admin page:** Build the `admin.html` page with HTML, CSS, and JavaScript.
7.  **Connect frontend to backend:** Use JavaScript to fetch data from the new API endpoints and display it on the admin page.

This plan provides a clear path to implementing the business admin panel. Let me know if you have any questions or would like to proceed with the implementation.
