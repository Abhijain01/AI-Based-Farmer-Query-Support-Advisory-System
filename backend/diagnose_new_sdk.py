from google import genai
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
api_key = os.getenv("GEMINI_API_KEY")

print(f"Testing with google-genai SDK. Key present: {bool(api_key)}")

try:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-1.5-flash", 
        contents="Say hello"
    )
    print(f"Success! Response: {response.text}")
except Exception as e:
    print(f"Failed: {e}")
