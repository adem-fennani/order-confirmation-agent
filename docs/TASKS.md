# GitHub Issues - Business Admin Panel + WooCommerce Integration

**Timeline:** 6 Days, 5 Hours Each (30 Total Hours)
**Goal:** Complete order flow from WooCommerce → Extension → Admin Panel

---

## Day 1 Issues (5 hours total)

### Issue #1: Database Schema & Models Setup

**Priority:** High | **Estimated:** 3 hours

**Description:** Set up the foundational database structure for business admin functionality.

**Tasks:**

- [x] Add `business_id`, `site_url`, `site_id` columns to existing `orders` table
- [x] Create new `business_users` table with `api_key` field
- [x] Write and test SQL migration script
- [x] Create BusinessUser model in `models.py` with API key generation
- [x] Test database changes with sample data

**Acceptance Criteria:**

- Database migration runs successfully
- BusinessUser model includes automatic API key generation
- Orders table can store business and site information

---

### Issue #2: API Key Management System

**Priority:** High | **Estimated:** 2 hours

**Description:** Implement secure API key generation and validation system.

**Tasks:**

- [x] Implement API key generation function using `secrets.token_urlsafe(32)`
- [x] Create API key validation middleware for incoming requests
- [x] Add API key to business user creation flow
- [x] Create sample test data (2-3 business users with API keys)
- [x] Test API key validation with mock requests

**Acceptance Criteria:**

- API keys are unique and secure (32+ characters)
- Validation middleware correctly identifies valid/invalid keys
- Test users have working API keys

---

## Day 2 Issues (5 hours total)

### Issue #3: Business Authentication API

**Priority:** High | **Estimated:** 3 hours

**Description:** Create secure authentication system for business admin panel.

**Tasks:**

- [x] Create `/src/api/business.py` FastAPI router
- [x] Implement `POST /api/business/login` endpoint with bcrypt validation
- [x] Create session token generation and validation system
- [x] Add in-memory session storage for MVP
- [x] Test login flow with sample business users

**Acceptance Criteria:**

- Login endpoint accepts username/password and returns session token
- Passwords are properly hashed with bcrypt
- Session tokens are generated and stored securely

---

### Issue #4: Authentication Middleware

**Priority:** High | **Estimated:** 2 hours

**Description:** Build middleware to protect admin endpoints with session validation.

**Tasks:**

- [x] Create Bearer token validation dependency for FastAPI
- [x] Implement session verification middleware
- [x] Add proper HTTP error responses for authentication failures
- [x] Test authentication flow with valid/invalid tokens
- [x] Integrate authentication dependency with business router

**Acceptance Criteria:**

- Protected endpoints require valid Bearer token
- Invalid tokens return 401 Unauthorized
- Valid tokens allow access to protected resources

---

## Day 3 Issues (5 hours total)

### Issue #5: Business Orders API

**Priority:** High | **Estimated:** 3 hours

**Description:** Create API endpoints for businesses to access their order data.

**Tasks:**

- [x] Implement `GET /api/business/orders` with business_id filtering
- [x] Implement `GET /api/business/orders/{order_id}` with ownership validation
- [x] Add pagination support for orders list
- [x] Add proper error handling and HTTP status codes
- [x] Test endpoints with sample order data linked to businesses

**Acceptance Criteria:**

- Orders API returns only orders belonging to authenticated business
- Individual order endpoint validates ownership before returning data
- Proper 404 responses for non-existent or unauthorized orders

---

### Issue #6: API Key Access Endpoint

**Priority:** High | **Estimated:** 2 hours

**Description:** Allow businesses to retrieve their API key for extension configuration.

**Tasks:**

- [x] Implement `GET /api/business/api-key` endpoint
- [x] Add authentication requirement for API key access
- [x] Return API key securely for authenticated users
- [x] Test API key retrieval flow
- [x] Add error handling for missing API keys

**Acceptance Criteria:**

- Authenticated businesses can retrieve their API key
- API key is returned in secure format
- Unauthorized requests are properly rejected

---

## Day 4 Issues (5 hours total)

### Issue #7: Order Submission API

**Priority:** High | **Estimated:** 3 hours

**Description:** Create endpoint for browser extension to submit confirmed orders.

**Tasks:**

- [x] Create `POST /api/orders/submit` endpoint
- [x] Implement `X-API-Key` header validation middleware
- [x] Parse and validate WooCommerce order data format
- [x] Store orders with correct business_id and site information
- [x] Return order confirmation response with generated order ID
- [x] Test with mock WooCommerce order data

**Acceptance Criteria:**

- Extension can submit orders using valid API key
- Order data is properly parsed and stored
- Orders are linked to correct business via API key
- Confirmation response includes order ID

---

### Issue #8: WooCommerce Extension Integration

**Priority:** High | **Estimated:** 2 hours

**Description:** Update browser extension to detect and submit WooCommerce orders.

**Tasks:**

- [ ] Update extension to detect WooCommerce order success page patterns
- [ ] Extract order details from DOM (items, prices, totals, order ID)
- [ ] Add API key and site ID configuration to extension settings
- [ ] Implement order submission to `/api/orders/submit` endpoint
- [ ] Test with actual WooCommerce order confirmation pages

**Acceptance Criteria:**

- Extension recognizes WooCommerce order success pages
- Order data is accurately extracted from page DOM
- Orders are successfully submitted to API
- Extension handles API response and errors

---

## Day 5 Issues (5 hours total)

### Issue #9: Admin Panel Core UI

**Priority:** High | **Estimated:** 3 hours

**Description:** Build the main user interface for the business admin panel.

**Tasks:**

- [ ] Create `admin.html` with login section and dashboard layout
- [ ] Implement `AdminApp` JavaScript class structure
- [ ] Add login form with proper form validation
- [ ] Create orders table with sortable columns
- [ ] Add basic CSS styling for usability
- [ ] Implement show/hide logic for login vs dashboard sections

**Acceptance Criteria:**

- Clean, functional login interface
- Orders are displayed in organized table format
- UI switches between login and dashboard states
- Basic responsive design works on desktop and mobile

---

### Issue #10: Frontend API Integration

**Priority:** High | **Estimated:** 2 hours

**Description:** Connect the admin panel frontend to backend APIs.

**Tasks:**

- [ ] Connect login form to `POST /api/business/login` endpoint
- [ ] Implement secure token storage in localStorage
- [ ] Load and display orders from `GET /api/business/orders`
- [ ] Add logout functionality with proper session cleanup
- [ ] Handle API errors and display user-friendly messages

**Acceptance Criteria:**

- Login form successfully authenticates with backend
- Orders load and display after successful login
- Logout clears session and returns to login screen
- Basic error handling for network/API failures

---

## Day 6 Issues (5 hours total)

### Issue #11: Order Details & API Settings

**Priority:** High | **Estimated:** 3 hours

**Description:** Complete the admin panel with order details and API configuration.

**Tasks:**

- [ ] Create order detail modal with complete order information
- [ ] Implement `GET /api/business/orders/{id}` integration
- [ ] Add API settings section displaying business API key
- [ ] Add copy-to-clipboard functionality for API key
- [ ] Show site information and basic site management
- [ ] Add order status and conversation data display

**Acceptance Criteria:**

- Order details modal shows complete order information
- API key is displayed and easily copyable
- Site information is clearly presented
- All order data including conversations is accessible

---

### Issue #12: End-to-End Testing & Polish

**Priority:** High | **Estimated:** 2 hours

**Description:** Complete testing and final polish for MVP release.

**Tasks:**

- [ ] Test complete flow: WooCommerce order → Extension → Admin Panel
- [ ] Add responsive CSS styling for mobile devices
- [ ] Implement loading states for API calls
- [ ] Add basic error messages and success notifications
- [ ] Verify all API endpoints function correctly
- [ ] Create minimal setup instructions for businesses

**Acceptance Criteria:**

- Full order flow works end-to-end without errors
- Admin panel is usable on mobile and desktop
- Users receive appropriate feedback for all actions
- Basic documentation exists for business setup

---

## Optional Future Issues (Post-Deadline)

### Issue #13: Enhanced UX

**Priority:** Low | **Future Enhancement**

- Advanced styling and animations
- Comprehensive error handling
- Real-time order notifications
- Advanced filtering and search capabilities

### Issue #14: Documentation & Support

**Priority:** Low | **Future Enhancement**

- Complete API documentation
- Detailed business setup guide
- Extension configuration walkthrough
- Troubleshooting and FAQ documentation

---

## Summary

**Total Estimated Time:** 30 hours
**Daily Commitment:** 5 hours focused coding
**Deliverable:** Complete business admin panel with WooCommerce integration
**Success Criteria:** Orders flow seamlessly from WooCommerce through extension to admin panel
