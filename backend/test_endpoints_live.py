import requests
import json
import time

BASE_URL = "http://localhost:5001"

def test_gemini_ask():
    print("\n--- Testing /ask (Gemini) ---")
    payload = {"question": "What is the best fertilizer for wheat?"}
    try:
        start = time.time()
        resp = requests.post(f"{BASE_URL}/ask", json=payload, timeout=60)
        print(f"Status: {resp.status_code}")
        print(f"Time: {time.time() - start:.2f}s")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Source: {data.get('source')}")
            print(f"Answer: {data.get('answer')[:100]}...")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Request failed: {e}")

def test_otp_flow():
    print("\n--- Testing OTP Flow ---")
    phone = "9876543210"
    
    # 1. Send OTP
    print(f"Sending OTP to {phone}...")
    otp_val = None
    try:
        resp = requests.post(f"{BASE_URL}/send-otp", json={"phone": phone})
        print(f"Send Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {data}")
            otp_val = data.get("otp")
        else:
            print(f"Send Error: {resp.text}")
            return
    except Exception as e:
        print(f"Send Request failed: {e}")
        return

    if not otp_val:
        print("No OTP received, skipping verification.")
        return

    # 2. Verify OTP
    print(f"Verifying OTP {otp_val} for {phone}...")
    try:
        resp = requests.post(f"{BASE_URL}/verify-otp", json={"phone": phone, "otp": otp_val})
        print(f"Verify Status: {resp.status_code}")
        print(f"Verify Response: {resp.text}")
    except Exception as e:
        print(f"Verify Request failed: {e}")

if __name__ == "__main__":
    # Check health first
    try:
        h = requests.get(f"{BASE_URL}/health")
        print(f"Health Check: {h.status_code} - {h.text}")
    except Exception as e:
        print(f"Backend seems down: {e}")
        exit(1)

    test_gemini_ask()
    test_otp_flow()
