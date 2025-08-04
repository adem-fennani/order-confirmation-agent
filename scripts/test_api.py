# scripts/test_api.py
import httpx
import sys

# This is the API key we retrieved earlier
api_key = "5jJFLzzWMc5C1vO59JIcS_rDB7N_Xw3gNLp0cQKb1Nw"
url = "http://127.0.0.1:8000/api/business/test"
login_url = "http://127.0.0.1:8000/api/business/login"
me_url = "http://127.0.0.1:8000/api/business/me"
business_orders_url = "http://127.0.0.1:8000/api/business/orders"
business_api_key_url = "http://127.0.0.1:8000/api/business/api-key"
submit_order_url = "http://127.0.0.1:8000/orders/submit"

def run_test():
    print("--- Running API Tests ---")
    
    # 1. Test Business Login to get token
    print("\n[TEST 1] Attempting to log in...")
    try:
        with httpx.Client(timeout=30.0) as client:
            data = {"username": "testuser", "password": "password"}
            response = client.post(login_url, data=data)
            if response.status_code == 200 and "access_token" in response.json():
                token = response.json()["access_token"]
                print("Result: PASSED - Successfully logged in.")
            else:
                print(f"Result: FAILED - Login failed with status {response.status_code}.")
                sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during login: {e}")
        sys.exit(1)

    # 2. Test protected route with the token
    print("\n[TEST 2] Accessing protected route with valid token...")
    try:
        with httpx.Client(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get(me_url, headers=headers)
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Body: {response.json()}")
            if response.status_code == 200:
                print("Result: PASSED - Successfully accessed protected route.")
            else:
                print(f"Result: FAILED - Server responded with {response.status_code}.")
                sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    # 3. Test protected route with an invalid token
    print("\n[TEST 3] Accessing protected route with invalid token...")
    try:
        with httpx.Client(timeout=30.0) as client:
            headers = {"Authorization": "Bearer invalid-token"}
            response = client.get(me_url, headers=headers)
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Body: {response.json()}")
            if response.status_code == 401:
                print("Result: PASSED - Server correctly rejected invalid token.")
            else:
                print(f"Result: FAILED - Server responded with {response.status_code}.")
                sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    # 4. Test get_business_orders
    print("\n[TEST 4] Getting business orders...")
    try:
        with httpx.Client(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get(business_orders_url, headers=headers)
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Body: {response.json()}")
            if response.status_code == 200 and len(response.json()) == 3: # Assuming 3 test orders were created
                print("Result: PASSED - Retrieved correct number of orders.")
            else:
                print(f"Result: FAILED - Expected 3 orders, got {len(response.json()) if response.status_code == 200 else 'N/A'}.")
                sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    # 5. Test get_business_orders with pagination
    print("\n[TEST 5] Getting business orders with pagination (skip=1, limit=1)...")
    try:
        with httpx.Client(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get(f"{business_orders_url}?skip=1&limit=1", headers=headers)
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Body: {response.json()}")
            if response.status_code == 200 and len(response.json()) == 1:
                print("Result: PASSED - Pagination works correctly.")
            else:
                print(f"Result: FAILED - Expected 1 order, got {len(response.json()) if response.status_code == 200 else 'N/A'}.")
                sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    # 6. Test get_business_order with a valid ID
    print("\n[TEST 6] Getting a specific business order with a valid ID...")
    try:
        with httpx.Client(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {token}"}
            # Get an order ID from the previous test
            response = client.get(business_orders_url, headers=headers)
            first_order_id = response.json()[0]["id"]
            
            response = client.get(f"{business_orders_url}/{first_order_id}", headers=headers)
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Body: {response.json()}")
            if response.status_code == 200 and response.json()["id"] == first_order_id:
                print("Result: PASSED - Retrieved specific order correctly.")
            else:
                print(f"Result: FAILED - Could not retrieve specific order.")
                sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    # 7. Test get_business_order with an invalid ID
    print("\n[TEST 7] Getting a specific business order with an invalid ID...")
    try:
        with httpx.Client(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get(f"{business_orders_url}/invalid_order_id", headers=headers)
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Body: {response.json()}")
            if response.status_code == 404:
                print("Result: PASSED - Correctly returned 404 for invalid ID.")
            else:
                print(f"Result: FAILED - Expected 404, got {response.status_code}.")
                sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    # 8. Test get_business_api_key
    print("\n[TEST 8] Getting business API key...")
    try:
        with httpx.Client(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get(business_api_key_url, headers=headers)
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Body: {response.json()}")
            if response.status_code == 200 and response.json()["api_key"] == api_key:
                print("Result: PASSED - Retrieved API key correctly.")
            else:
                print(f"Result: FAILED - Could not retrieve API key.")
                sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    # 9. Test POST /orders/submit
    print("\n[TEST 9] Submitting a new order...")
    try:
        with httpx.Client(timeout=30.0) as client:
            submit_data = {
                "site_id": "test_site_1",
                "site_url": "https://www.example.com/shop",
                "order_data": {
                    "items": [
                        {"name": "Product A", "price": 10.0, "quantity": 1},
                        {"name": "Product B", "price": 20.0, "quantity": 2}
                    ],
                    "total_amount": 30.0,
                    "notes": "Test order from extension"
                },
                "customer_info": {
                    "customer_name": "John Doe",
                    "customer_phone": "+15551234567"
                }
            }
            headers = {"X-API-Key": api_key}
            response = client.post(submit_order_url, json=submit_data, headers=headers)
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Body: {response.json()}")
            if response.status_code == 200 and "id" in response.json():
                print("Result: PASSED - Order submitted successfully.")
            else:
                print(f"Result: FAILED - Order submission failed.")
                sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during order submission: {e}")
        sys.exit(1)

    print("\n--- All Tests Completed Successfully ---")

if __name__ == "__main__":
    run_test()