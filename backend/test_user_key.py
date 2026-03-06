
import google.generativeai as genai
import os

key = "AIzaSyDxXsFeyUGlpVhbU7oTWhkNDMirOMt7izg"
print(f"Testing Key: {key}")

try:
    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    print("Generating content with flash...")
    resp = model.generate_content("Hello from test script", request_options={"timeout": 10})
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
