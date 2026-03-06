import requests
import os

url = "http://127.0.0.1:5000/chat-image"
image_path = "frontend/src/assets/farm.png"

if not os.path.exists(image_path):
    print(f"Image not found at {image_path}")
    exit(1)

print(f"Testing fallback with {image_path}...")
files = {"image": open(image_path, "rb")}
try:
    resp = requests.post(url, files=files)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Request failed: {e}")
