# scripts/test_api.py
import httpx
import sys

# This is the API key we retrieved earlier
api_key = "pnFPzrhqstsb-H-nhoqVpQzBjrX5bNXhfGKVU77h8vs"
url = "http://127.0.0.1:8000/api/business/test"

def run_test():
    print("--- Running API Key Validation Test ---")
    
    # 1. Test with an invalid API key
    print("\n[TEST 1] Sending request with an INVALID API key...")
    try:
        with httpx.Client() as client:
            headers = {"X-API-Key": "this-is-an-invalid-key"}
            response = client.get(url, headers=headers)
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Body: {response.json()}")
            if response.status_code == 401:
                print("Result: PASSED - Server correctly rejected the invalid key.")
            else:
                print(f"Result: FAILED - Server responded with {response.status_code} instead of 401.")
                sys.exit(1)
    except httpx.ConnectError as e:
        print(f"\n[ERROR] Connection failed. Is the server running at {url}?")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    # 2. Test with a valid API key
    print("\n[TEST 2] Sending request with a VALID API key...")
    try:
        with httpx.Client() as client:
            headers = {"X-API-Key": api_key}
            response = client.get(url, headers=headers)
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Body: {response.json()}")
            if response.status_code == 200:
                print("Result: PASSED - Server correctly validated the API key.")
            else:
                print(f"Result: FAILED - Server responded with {response.status_code} instead of 200.")
                sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    print("\n--- Test Completed Successfully ---")

if __name__ == "__main__":
    run_test()
