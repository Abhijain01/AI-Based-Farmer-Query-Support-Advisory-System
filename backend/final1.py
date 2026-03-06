# app.py - Full Flask backend with ML, OTP, user, marketplace, and utilities

import os
import io
import json
import random
import tempfile
import base64
import logging
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import requests

import numpy as np
import faiss
from sklearn.preprocessing import normalize

# Optional ML and translation libraries
try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

from langdetect import detect
import google.generativeai as genai
from gtts import gTTS
from pydub import AudioSegment
from pydub.utils import which

try:
    import joblib
except Exception:
    joblib = None

try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    from PIL import Image
except Exception:
    tf = None
    load_model = None
    from PIL import Image

try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

# -------------------------------
# Config & App init
# -------------------------------
load_dotenv()
app = Flask(__name__)

FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
CORS(app, resources={r"/*": {"origins": FRONTEND_ORIGINS}}, supports_credentials=True)

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin and origin in FRONTEND_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

# Environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_DIR = os.getenv("MODEL_DIR", os.path.join(os.path.dirname(__file__), "models"))
WEATHER_API = os.getenv("WEATHER_API", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    app.logger.warning("GEMINI_API_KEY not set. Gemini calls will fail if used.")

# MongoDB
client, db, users, otps, listings_col = None, None, None, None, None
try:
    client = MongoClient(MONGO_URI)
    db = client.get_database("mywebapp_db")
    users = db["users"]
    otps = db["otps"]
    listings_col = db["buyer_requests"]
    app.logger.info("✅ Connected to MongoDB.")
except Exception as e:
    app.logger.warning(f"⚠️ Could not connect to MongoDB: {e}")

# -------------------------------
# Globals: models & search index
# -------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
faiss_index, kcc_metadata, sentence_model = None, None, None
fertilizer_model, soil_encoder, crop_encoder, fertilizer_encoder = None, None, None, None
disease_model, idx_to_class = None, {}

FAISS_TOP_K = 5
FAISS_SCORE_THRESHOLD = 0.6

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)

_audio_converter = which("ffmpeg") or which("ffmpeg.exe")
if _audio_converter:
    AudioSegment.converter = _audio_converter
else:
    app.logger.warning("FFmpeg not found. Audio conversion may fail.")

# -------------------------------
# Model loading
# -------------------------------
def load_models():
    global faiss_index, kcc_metadata, sentence_model
    global fertilizer_model, soil_encoder, crop_encoder, fertilizer_encoder
    global disease_model, idx_to_class

    # FAISS + metadata
    try:
        faiss_path = os.path.join(SCRIPT_DIR, "kcc_index_kerala.faiss")
        meta_path = os.path.join(SCRIPT_DIR, "kcc_metadata_kerala.jsonl")
        if os.path.exists(faiss_path) and os.path.exists(meta_path):
            faiss_index = faiss.read_index(faiss_path)
            kcc_metadata = [json.loads(line) for line in open(meta_path, "r", encoding="utf-8")]
            logger.info(f"✅ Loaded FAISS index ({faiss_path}) with {len(kcc_metadata)} records.")
        else:
            logger.info("FAISS files not found; local search disabled.")
    except Exception as e:
        logger.exception(f"Failed to load FAISS index: {e}")

    # Sentence Transformer
    try:
        if SentenceTransformer:
            sentence_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            logger.info("✅ Loaded sentence-transformer model.")
        else:
            logger.info("sentence-transformers not installed; skipping embedding generation.")
    except Exception as e:
        logger.exception(f"Failed to load sentence-transformer: {e}")
        sentence_model = None

    # Disease model
    try:
        model_path_candidates = [
            os.path.join(SCRIPT_DIR, "plant_disease_identification_model.h5"),
            os.path.join(MODEL_DIR, "plant_disease_identification_model.h5")
        ]
        model_path = next((p for p in model_path_candidates if os.path.exists(p)), None)
        if model_path and load_model:
            disease_model = load_model(model_path)
            logger.info(f"✅ Loaded disease model from {model_path}")
            json_candidates = [
                os.path.join(os.path.dirname(model_path), "class_indices.json"),
                os.path.join(SCRIPT_DIR, "class_indices.json"),
                os.path.join(MODEL_DIR, "class_indices.json")
            ]
            json_path = next((p for p in json_candidates if os.path.exists(p)), None)
            if json_path:
                with open(json_path, "r", encoding="utf-8") as f:
                    class_indices_map = json.load(f)
                idx_to_class.update({int(v): k for k, v in class_indices_map.items()})
                logger.info(f"✅ Loaded class_indices.json ({json_path}) with {len(idx_to_class)} classes.")
        else:
            logger.info("ℹ️ Disease model not found or TensorFlow not installed.")
    except Exception as e:
        logger.exception(f"Error loading disease model: {e}")
        disease_model = None

    # Fertilizer model
    try:
        fert_candidates = [
            os.path.join(SCRIPT_DIR, "fertilizer_model.pkl"),
            os.path.join(MODEL_DIR, "fertilizer_model.pkl")
        ]
        fert_model_path = next((p for p in fert_candidates if os.path.exists(p)), None)
        if fert_model_path and joblib:
            fertilizer_model = joblib.load(fert_model_path)
            logger.info(f"✅ Loaded fertilizer model from {fert_model_path}")
            # encoders
            for name, path in [("soil_encoder", "soil_encoder.pkl"), ("crop_encoder", "crop_encoder.pkl"), ("fertilizer_encoder", "fertilizer_encoder.pkl")]:
                full_path = os.path.join(SCRIPT_DIR, path)
                if os.path.exists(full_path):
                    globals()[name] = joblib.load(full_path)
                    logger.info(f"✅ Loaded {path}")
        else:
            logger.info("ℹ️ Fertilizer model not found or joblib not available.")
    except Exception as e:
        logger.exception(f"Error loading fertilizer model: {e}")

load_models()

# -------------------------------
# Helpers
# -------------------------------
def detect_lang(text: str):
    try:
        return detect(text)
    except:
        return "en"

def translate_to_en(text: str):
    try:
        return GoogleTranslator(source="auto", target="en").translate(text)
    except:
        return text

def translate_from_en(text: str, target_lang: str):
    if target_lang == "en": return text
    try:
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except:
        return text

def text_to_audio_base64(text: str, lang: str = "en"):
    try:
        mp3_fp = io.BytesIO()
        tld_map = {"en": "co.in", "ml": "co.in"}
        tts = gTTS(text=text, lang=lang, tld=tld_map.get(lang, "com"))
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return base64.b64encode(mp3_fp.read()).decode()
    except Exception as e:
        logger.exception(f"TTS failed: {e}")
        return None

def preprocess_image_for_model(img: Image.Image, target_size=(224, 224)):
    img = img.convert("RGB").resize(target_size)
    arr = np.expand_dims(np.asarray(img).astype("float32") / 255.0, 0)
    return arr

def _search_faiss_local(query: str, top_k=FAISS_TOP_K):
    if not faiss_index or not sentence_model or not kcc_metadata:
        return []
    try:
        q_emb = sentence_model.encode([query], convert_to_numpy=True).astype("float32")
        D, I = faiss_index.search(q_emb, top_k)
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(kcc_metadata): continue
            score = 1.0 / (1.0 + float(dist))
            meta = kcc_metadata[idx]
            results.append({"score": score, "query": meta.get("query", ""), "answer": meta.get("answer", ""), "id": meta.get("id", idx)})
        return sorted(results, key=lambda x: x["score"], reverse=True)
    except Exception as e:
        logger.exception(f"FAISS search failed: {e}")
        return []

def ask_gemini_once(prompt_en: str) -> str:
    if not GEMINI_API_KEY: raise RuntimeError("Gemini API key not configured.")
    try:
        gen_model = genai.GenerativeModel("gemini-1.5-flash-latest")
        resp = gen_model.generate_content(prompt_en)
        return getattr(resp, "text", "")
    except Exception as e:
        logger.exception(f"Gemini call failed: {e}")
        return "Gemini failed to generate a response."

# -------------------------------
# Routes
# -------------------------------
@app.route("/")
def home():
    return jsonify({"message": "Flask backend is running 🚀"})

@app.route("/chat-image", methods=["POST"])
def chat_image():
    if "image" not in request.files: return jsonify({"error": "No image provided"}), 400
    if not disease_model: return jsonify({"error": "Disease model not loaded on server."}), 500
    try:
        img = Image.open(request.files["image"].stream)
        arr = preprocess_image_for_model(img)
        preds = disease_model.predict(arr, verbose=0)
        class_idx = int(np.argmax(preds))
        conf = float(np.max(preds))
        label = idx_to_class.get(class_idx, f"Class_{class_idx}").replace("_", " ")
        return jsonify({"answer": f"Predicted disease: {label} (confidence {conf:.2f})", "disease": label, "confidence": conf, "source": "disease_model"})
    except Exception as e:
        logger.exception(f"Disease prediction failed: {e}")
        return jsonify({"error": "Disease prediction failed."}), 500

@app.route("/recommend", methods=["POST"])
def recommend_fertilizer():
    if not fertilizer_model: return jsonify({"error": "Fertilizer model not loaded"}), 500
    if not all([soil_encoder, crop_encoder, fertilizer_encoder]): return jsonify({"error": "One or more encoders missing"}), 500
    try:
        data = request.json or {}
        required = ["N","P","K","moisture","temperature","humidity","soil","crop"]
        missing = [r for r in required if r not in data]
        if missing: return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
        features = np.array([[float(data["temperature"]), float(data["humidity"]), float(data["moisture"]),
                              float(data["N"]), float(data["P"]), float(data["K"]),
                              soil_encoder.transform([data["soil"]])[0],
                              crop_encoder.transform([data["crop"]])[0]]])
        pred_encoded = fertilizer_model.predict(features)[0]
        fertilizer_name = fertilizer_encoder.inverse_transform([pred_encoded])[0]
        return jsonify({"recommendation": fertilizer_name})
    except Exception as e:
        logger.exception(f"Fertilizer recommendation failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/ask", methods=["POST"])
def ask_bot():
    body = request.json or {}
    prompt = body.get("question") or body.get("q","")
    if not prompt: return jsonify({"error":"No question provided"}), 400
    user_lang = detect_lang(prompt)
    try:
        results = _search_faiss_local(prompt)
        top = results[0] if results and results[0]["score"] >= FAISS_SCORE_THRESHOLD else None
        if top:
            answer_en = top["answer"]
            source = f"KCC local (score={top['score']:.2f})"
        else:
            prompt_en = prompt if user_lang=="en" else translate_to_en(prompt)
            gemini_prompt = f"You are an agriculture expert. Answer succinctly and practically: {prompt_en}"
            answer_en = ask_gemini_once(gemini_prompt)
            source = "Gemini (fallback)"
        final_answer = answer_en if user_lang=="en" else translate_from_en(answer_en, user_lang)
        audio_b64 = text_to_audio_base64(final_answer, user_lang)
        return jsonify({"answer": final_answer, "source": source, "audio_base64": audio_b64})
    except Exception as e:
        logger.exception(f"Ask endpoint error: {e}")
        return jsonify({"error": "Internal error answering the question."}), 500

# -------------------------------
# OTP endpoints
# -------------------------------
@app.route("/send-otp", methods=["POST"])
def send_otp():
    if not otps: return jsonify({"success": False, "error":"DB not configured"}), 500
    phone = (request.json or {}).get("phone")
    if not phone: return jsonify({"success": False, "error":"Phone number required"}), 400
    otp = str(random.randint(100000,999999))
    otps.update_one({"phone":phone},{"$set":{"otp":otp}}, upsert=True)
    logger.info(f"OTP for {phone}: {otp}")
    return jsonify({"success":True,"message":"OTP sent","otp":otp})

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    if not otps or not users: return jsonify({"success": False, "error":"DB not configured"}),500
    data = request.json or {}
    phone, otp = data.get("phone"), data.get("otp")
    if not phone or not otp: return jsonify({"success":False,"error":"Phone and OTP required"}),400
    otp_doc = otps.find_one({"phone":phone})
    if not otp_doc or otp_doc.get("otp") != otp: return jsonify({"success":False,"error":"Invalid OTP"}),400
    user = users.find_one({"phone":phone},{"_id":0})
    otps.delete_one({"phone":phone})
    return jsonify({"success":True,"message":"OTP verified ✅","existing_user":bool(user),"user":user})

# -------------------------------
# User endpoints
# -------------------------------
@app.route("/register-details", methods=["POST"])
def register_details():
    data = request.json or {}
    phone = data.get("phone")
    if not phone: return jsonify({"error":"phone required"}),400
    crops = [{"name":c.get("name"),"soil":c.get("soil"),"landArea":c.get("landArea"),"farmLocation":c.get("farmLocation")} for c in data.get("crops",[])]
    if users:
        users.update_one({"phone":phone},{"$set":{"name":data.get("name"),"email":data.get("email"),"state":data.get("state"),"address":data.get("address"),"district":data.get("district"),"pin":data.get("pin"),"crops":crops}},upsert=True)
    return jsonify({"message":"User details saved successfully"}),200

@app.route("/get-user", methods=["GET"])
def get_user():
    phone = request.args.get("phone")
    if not phone or not users: return jsonify({"name":"Guest"})
    user = users.find_one({"phone":phone},{"_id":0})
    return jsonify(user or {"name":"Guest"})

@app.route("/update-location", methods=["POST"])
def update_location():
    if not users: return jsonify({"error":"DB not configured"}),500
    data = request.json or {}
    phone, lat, lon, city = data.get("phone"), data.get("lat"), data.get("lon"), data.get("city")
    if not phone or lat is None or lon is None or not city: return jsonify({"error":"phone, lat, lon, city required"}),400
    users.update_one({"phone":phone},{"$set":{"current_location":{"lat":lat,"lon":lon,"city":city}}},upsert=True)
    return jsonify({"message":"Location updated ✅","city":city})

@app.route("/weather", methods=["GET"])
def weather():
    phone = request.args.get("phone")
    try:
        if users and phone:
            user = users.find_one({"phone":phone},{"_id":0})
            if user and "current_location" in user:
                lat, lon = user["current_location"]["lat"], user["current_location"]["lon"]
                url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API}&q={lat},{lon}"
                res = requests.get(url).json()
                return jsonify({"temp":f"{res['current']['temp_c']}°C","humidity":f"{res['current']['humidity']}%","wind":f"{res['current']['wind_kph']} km/h","desc":res['current']['condition']['text'],"city":res['location']['name']})
    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")
    return jsonify({"temp":"N/A","humidity":"N/A","wind":"N/A","desc":"N/A","city":"Unknown"})

# -------------------------------
# Marketplace endpoints
# -------------------------------
@app.route("/buyer-requests", methods=["POST"])
def buyer_requests():
    if not listings_col: return jsonify({"error":"DB not configured"}),500
    data = request.json or {}
    listings_col.insert_one(data)
    return jsonify({"message":"Buyer request saved ✅"})

@app.route("/get-buyer-requests", methods=["GET"])
def get_buyer_requests():
    if not listings_col: return jsonify([]),500
    requests_list = list(listings_col.find({},{"_id":0}))
    return jsonify(requests_list)

# -------------------------------
# Transcription
# -------------------------------
@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    if sr is None: return jsonify({"error":"SpeechRecognition not installed"}),500
    if "audio" not in request.files: return jsonify({"error":"No audio uploaded"}),400
    try:
        file = request.files["audio"]
        recognizer = sr.Recognizer()
        with sr.AudioFile(file) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return jsonify({"transcription": text})
    except Exception as e:
        logger.exception(f"Transcription failed: {e}")
        return jsonify({"error":"Transcription failed"}),500

# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)), debug=True)
