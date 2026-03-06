import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("backend/.env")

api_key = os.getenv("GEMINI_API_KEY")
model_env = os.getenv("GEMINI_MODEL", "NOT SET")

print(f"API Key present: {bool(api_key)}")
if api_key:
    print(f"Key start: {api_key[:5]}...")
print(f"GEMINI_MODEL env: {model_env}")

genai.configure(api_key=api_key)

models_to_try = [
    "gemini-1.5-pro",
    "models/gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.0-pro"
]

for m in models_to_try:
    print(f"\nTrying model: {m}")
    try:
        model = genai.GenerativeModel(m)
        response = model.generate_content("Say hello in one word.")
        print(f"Success! Response: {response.text}")
        break
    except Exception as e:
        print(f"Failed: {e}")
