import requests
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

print(f"Checking configured key: {os.getenv('GEMINI_API_KEY')[:10]}...")

try:
    resp = requests.get("http://127.0.0.1:5000/gemini-health")
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"Request failed: {e}")
