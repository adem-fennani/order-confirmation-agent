# scripts/test_api.py
import httpx
import sys

# This is the API key we retrieved earlier
api_key = "pnFPzrhqstsb-H-nhoqVpQzBjrX5bNXhfGKVU77h8vs"
url = "http://127.0.0.1:8000/api/business/test"
login_url = "http://127.0.0.1:8000/api/business/login"
me_url = "http://127.0.0.1:8000/api/business/me"

def run_test():
    print("--- Running API Tests ---")
    
    # 1. Test Business Login to get token
    print("\n[TEST 1] Attempting to log in...")
    try:
        with httpx.Client() as client:
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
        with httpx.Client() as client:
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
        with httpx.Client() as client:
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

    print("\n--- All Tests Completed Successfully ---")

if __name__ == "__main__":
    run_test()
