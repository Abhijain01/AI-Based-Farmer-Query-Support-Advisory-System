import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("backend/.env")
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

models = ["gemini-1.5-flash", "gemini-pro", "gemini-1.5-pro"]

for m in models:
    print(f"Testing {m}...", end=" ")
    try:
        model = genai.GenerativeModel(m)
        resp = model.generate_content("hi")
        print("OK")
    except Exception as e:
        print(f"FAIL: {str(e)[:50]}")
