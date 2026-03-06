import requests
import sys

URL = "http://127.0.0.1:5000/ask"
PAYLOAD = {"question": "Describe a healthy tomato plant in one sentence."}

try:
    print(f"Testing /ask with {PAYLOAD}...")
    resp = requests.post(URL, json=PAYLOAD, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {data}")
        # Verify if answer is valid
        if "answer" in data and len(data["answer"]) > 5:
             sys.exit(0)
        else:
             print("Invalid answer content.")
             sys.exit(1)
    else:
        print(f"Error: {resp.text}")
        sys.exit(1)
except Exception as e:
    print(f"Request failed: {e}")
    sys.exit(1)
