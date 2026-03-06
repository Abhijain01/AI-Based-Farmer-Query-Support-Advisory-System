
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key present: {bool(api_key)}")

try:
    genai.configure(api_key=api_key)
    
    print("Listing available models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
            
    # Try models that were explicitly listed in the previous output
    candidates = ["gemini-flash-latest", "gemini-pro-latest", "gemini-2.0-flash-lite"]
    
    resp = None
    for model_name in candidates:
        print(f"\nAttempting to generate with {model_name}...")
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content("Say hello", request_options={"timeout": 10})
            print(f"Response from {model_name}: {resp.text}")
            break # Stop if successful
        except Exception as e:
            print(f"Failed with {model_name}: {e}")
            
    if resp:
        print(f"Final Success with: {model_name}")
    else:
        print("All models failed.")

except Exception as e:
    print(f"Error: {e}")
