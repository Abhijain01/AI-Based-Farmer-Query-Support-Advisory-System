from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
import random
from dotenv import load_dotenv
import google.generativeai as genai
import faiss
import numpy as np
from sklearn.preprocessing import normalize
import json
from deep_translator import GoogleTranslator
from langdetect import detect
import base64
from gtts import gTTS
import io
import joblib

# -------------------------------
# 1. App Setup and Configuration
# -------------------------------
load_dotenv()
app = Flask(__name__)
CORS(app)

MONGO_URI = os.getenv("MONGO_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not MONGO_URI or not GEMINI_API_KEY:
    print("CRITICAL ERROR: MONGO_URI or GEMINI_API_KEY not found in .env file.")
else:
    print("✅ Configuration loaded successfully.")

client = MongoClient(MONGO_URI)
db = client["mywebapp_db"]
users = db["users"]
otps = db["otps"]
print("✅ Connected to MongoDB.")

genai.configure(api_key=GEMINI_API_KEY)
print("✅ Gemini API configured.")

# -------------------------------
# 2. AI Model and Data Loading
# -------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
chat_model = genai.GenerativeModel("gemini-1.5-flash-latest")
faiss_index, metadata = None, None
fertilizer_model, soil_encoder, crop_encoder, fertilizer_encoder = None, None, None, None

try:
    FAISS_FILE = os.path.join(SCRIPT_DIR, "kcc_index_kerala.faiss")
    METADATA_FILE = os.path.join(SCRIPT_DIR, "kcc_metadata_kerala.jsonl")
    if os.path.exists(FAISS_FILE) and os.path.exists(METADATA_FILE):
        faiss_index = faiss.read_index(FAISS_FILE)
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = [json.loads(line) for line in f]
        print("✅ KCC search index loaded.")
    else:
        print("⚠️ KCC data files not found.")
except Exception as e:
    print(f"Error loading FAISS index: {e}")

# -------------------------------
# 3. API Endpoints
# -------------------------------
@app.route("/")
def home():
    return jsonify({"message": "Flask backend is running 🚀"})

@app.route("/send-otp", methods=["POST"])
def send_otp():
    phone = request.json.get("phone")
    if not phone:
        return jsonify({"error": "Phone number required"}), 400
    otp = str(random.randint(100000, 999999))
    otps.update_one({"phone": phone}, {"$set": {"otp": otp}}, upsert=True)
    return jsonify({"message": "OTP sent successfully", "otp": otp})

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    phone = request.json.get("phone")
    otp = request.json.get("otp")
    record = otps.find_one({"phone": phone})
    if record and record["otp"] == otp:
        user = users.find_one({"phone": phone}, {"_id": 0})
        return jsonify({"message": "OTP verified ✅", "existing_user": bool(user), "user": user})
    return jsonify({"error": "Invalid OTP ❌"}), 400

@app.route("/register-details", methods=["POST"])
def register_details():
    data = request.json
    phone = data.get("phone")
    if not phone:
        return jsonify({"error": "Phone required"}), 400
    users.update_one({"phone": phone}, {"$set": data}, upsert=True)
    return jsonify({"message": "User details saved successfully"}), 200

@app.route("/get-user", methods=["GET"])
def get_user():
    phone = request.args.get("phone")
    if phone:
        user = users.find_one({"phone": phone}, {"_id": 0})
        if user:
            return jsonify(user)
    return jsonify({"name": "Guest User", "location": "Phagwara"})

@app.route('/ask', methods=['POST'])
def ask_bot():
    prompt = request.json.get('question')
    if not prompt:
        return jsonify({"error": "No question provided"}), 400
    
    translated_query, original_lang = _preprocess_query(prompt)
    retrieved_results = _search_faiss(translated_query)
    top_match = retrieved_results[0] if retrieved_results else None
    
    if top_match:
        answer, source = top_match["answer"], f"KCC Database (Similarity: {top_match['score']:.0%})"
    else:
        gemini_prompt = f"You are a helpful agriculture expert. Answer concisely: {translated_query}"
        answer, source = chat_model.generate_content(gemini_prompt).text, "Gemini 1.5 Flash"
    
    final_answer = _translate_answer(answer, original_lang)
    audio_b64 = _text_to_audio_base64(final_answer, original_lang)

    return jsonify({"answer": final_answer, "source": source, "audio_base64": audio_b64})

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    try:
        audio_file = request.files['audio']
        # Save temporarily (Gemini needs a path to upload properly)
        temp_path = os.path.join(SCRIPT_DIR, "temp_audio.webm")
        audio_file.save(temp_path)

        uploaded_file = genai.upload_file(temp_path)
        speech_model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = speech_model.generate_content([
            "You are a speech-to-text assistant. Transcribe this audio accurately.",
            uploaded_file
        ])

        # Clean up temp file
        os.remove(temp_path)

        return jsonify({"text": response.text.strip() if response.text else ""})
    except Exception as e:
        print(f"Transcription failed: {e}")
        return jsonify({"error": "Failed to transcribe audio"}), 500

# -------------------------------
# 4. Helper Functions
# -------------------------------
def _search_faiss(query):
    if faiss_index is None:
        return []
    try:
        embedding = genai.embed_content(model="models/embedding-001", content=query)["embedding"]
        query_vec = np.array([embedding], dtype='float32')
        query_vec = normalize(query_vec)
        distances, indices = faiss_index.search(query_vec, k=1)
        scores = (1 + distances[0]) / 2
        if scores[0] >= 0.85:
            return [{"score": float(scores[0]), "answer": metadata[indices[0][0]]["answer"]}]
        return []
    except Exception as e:
        print(f"FAISS search failed: {e}")
        return []

def _preprocess_query(query):
    try:
        lang = detect(query)
        if lang != "en":
            return GoogleTranslator(source="auto", target="en").translate(query), lang
        return query, "en"
    except:
        return query, "en"

def _translate_answer(answer, target_lang):
    if target_lang != 'en':
        try:
            return GoogleTranslator(source='en', target=target_lang).translate(answer)
        except:
            return answer
    return answer

def _text_to_audio_base64(text, lang):
    try:
        tld_map = {'en': 'co.in', 'ml': 'co.in'}
        mp3_fp = io.BytesIO()
        tts = gTTS(text=text, lang=lang, tld=tld_map.get(lang, 'com'), slow=False)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return base64.b64encode(mp3_fp.read()).decode()
    except Exception as e:
        print(f"TTS failed: {e}")
        return None

# -------------------------------
# 5. Run the Server
# -------------------------------
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
 