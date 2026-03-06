# app.py (corrected with new model name)
import os
import io
import json
import random
import tempfile
import base64
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

# ML / utils
import numpy as np 
import faiss
from sklearn.preprocessing import normalize
from deep_translator import GoogleTranslator
from langdetect import detect
import google.generativeai as genai
from gtts import gTTS
from pydub import AudioSegment
from pydub.utils import which

# Optional ML model libs
try:
    import joblib
except Exception:
    joblib = None

try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    from tensorflow.keras.preprocessing import image
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

# Allowed frontend origins
FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CORS(
    app,
    resources={r"/*": {"origins": FRONTEND_ORIGINS}},
    supports_credentials=True,
)

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin and origin in FRONTEND_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

# Env variables
MONGO_URI = os.getenv("MONGO_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_DIR = os.getenv("MODEL_DIR", os.path.join(os.path.dirname(__file__), "models"))

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    app.logger.warning("GEMINI_API_KEY not set in .env - Gemini calls will fail if used.")

# MongoDB (optional)
client = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI)
        db = client.get_database("mywebapp_db")
        users = db["users"]
        otps = db["otps"]
        app.logger.info("✅ Connected to MongoDB.")
    except Exception as e:
        app.logger.warning("⚠️ Could not connect to MongoDB: %s", e)
        users = otps = None
else:
    users = otps = None
    app.logger.warning("⚠️ MONGO_URI not provided; auth/otp DB won't be persistent.")

# -------------------------------
# Globals: models & search index
# -------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
faiss_index = None
kcc_metadata = None
sentence_model = None

# ML models & encoders (globals)
fertilizer_model = None
soil_encoder = None
crop_encoder = None
fertilizer_encoder = None

disease_model = None
idx_to_class = {}

# Tuneables
FAISS_TOP_K = 5
FAISS_SCORE_THRESHOLD = 0.6

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)

_audio_converter = which("ffmpeg") or which("ffmpeg.exe")
if _audio_converter:
    AudioSegment.converter = _audio_converter
else:
    app.logger.warning("FFmpeg not found in PATH. Audio conversion (transcription) will likely fail.")

# -------------------------------
# Model loading
# -------------------------------
def load_models():
    """Centralized function to load all ML models and encoders."""
    global faiss_index, kcc_metadata, sentence_model
    global fertilizer_model, soil_encoder, crop_encoder, fertilizer_encoder
    global disease_model, idx_to_class

    # ... (FAISS and SentenceTransformer loading code remains the same) ...
    # 1) Load KCC FAISS index + metadata (if present)
    try:
        faiss_path = os.path.join(SCRIPT_DIR, "kcc_index_kerala.faiss")
        meta_path = os.path.join(SCRIPT_DIR, "kcc_metadata_kerala.jsonl")
        if os.path.exists(faiss_path) and os.path.exists(meta_path):
            faiss_index = faiss.read_index(faiss_path)
            kcc_metadata = []
            with open(meta_path, "r", encoding="utf-8") as f:
                for line in f:
                    kcc_metadata.append(json.loads(line))
            logger.info(f"✅ Loaded FAISS index ({faiss_path}) with {len(kcc_metadata)} records.")
        else:
            logger.info("KCC FAISS files not found; FAISS search disabled.")
    except Exception as e:
        logger.exception("Failed to load FAISS index: %s", e)

    # 2) Load sentence-transformer for embeddings if available
    try:
        if SentenceTransformer is not None:
            sentence_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            logger.info("✅ Loaded sentence-transformer model.")
        else:
            logger.info("sentence-transformers not installed; skipping local embedding generation.")
    except Exception as e:
        logger.exception("Failed to load sentence-transformer: %s", e)
        sentence_model = None


    # 3) Load disease model (Keras .h5)
    try:
        model_path_candidates = [
            os.path.join(SCRIPT_DIR, "plant_disease_identification_model.h5"),
            os.path.join(MODEL_DIR, "plant_disease_identification_model.h5"),
        ]
        model_path = next((p for p in model_path_candidates if p and os.path.exists(p)), None)

        if model_path and load_model is not None:
            disease_model = load_model(model_path)
            logger.info(f"✅ Loaded disease model from {model_path}")

            json_candidates = [
                os.path.join(os.path.dirname(model_path), "class_indices.json"),
                os.path.join(SCRIPT_DIR, "class_indices.json"),
                os.path.join(MODEL_DIR, "class_indices.json"),
            ]
            json_path = next((p for p in json_candidates if p and os.path.exists(p)), None)

            if json_path:
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        class_indices_map = json.load(f)
                    idx_to_class = {int(v): k for k, v in class_indices_map.items()}
                    logger.info(f"✅ Loaded class_indices.json ({json_path}) with {len(idx_to_class)} classes.")
                except Exception as e:
                    idx_to_class = {}
                    logger.warning(f"⚠️ Failed to load or parse class_indices.json: {e}")
            else:
                idx_to_class = {}
                logger.info("ℹ️ No class_indices.json found; predictions will return indices only.")
        else:
            disease_model = None
            idx_to_class = {}
            logger.info("⚠️ Disease model not found or TensorFlow not installed.")
    except Exception as e:
        disease_model = None
        idx_to_class = {}
        logger.exception(f"❌ Error loading disease model: {e}")

    # 4) Load fertilizer model + encoders (joblib/pickle)
    try:
        # UPDATED to look for 'fertilizer_model.pkl' as requested
        fert_candidates = [
            os.path.join(SCRIPT_DIR, "fertilizer_model.pkl"),
            os.path.join(MODEL_DIR, "fertilizer_model.pkl"),
        ]
        fert_model_path = next((p for p in fert_candidates if p and os.path.exists(p)), None)
        
        if fert_model_path and joblib is not None:
            fertilizer_model = joblib.load(fert_model_path)
            logger.info(f"✅ Loaded fertilizer model from {fert_model_path}")
            
            # Paths for all required encoders
            soil_path = os.path.join(SCRIPT_DIR, "soil_encoder.pkl")
            crop_path = os.path.join(SCRIPT_DIR, "crop_encoder.pkl")
            fert_enc_path = os.path.join(SCRIPT_DIR, "fertilizer_encoder.pkl")

            # Load each encoder and log success or failure
            try:
                if os.path.exists(soil_path):
                    soil_encoder = joblib.load(soil_path)
                    logger.info("✅ Loaded soil_encoder.pkl.")
                else:
                    logger.warning("⚠️ soil_encoder.pkl not found.")
                
                if os.path.exists(crop_path):
                    crop_encoder = joblib.load(crop_path)
                    logger.info("✅ Loaded crop_encoder.pkl.")
                else:
                    logger.warning("⚠️ crop_encoder.pkl not found.")

                if os.path.exists(fert_enc_path):
                    fertilizer_encoder = joblib.load(fert_enc_path)
                    logger.info("✅ Loaded fertilizer_encoder.pkl.")
                else:
                    logger.warning("⚠️ fertilizer_encoder.pkl not found.")

            except Exception as e:
                logger.warning(f"Could not load one or more fertilizer encoders: {e}")
        else:
            fertilizer_model = None
            logger.info("ℹ️ Fertilizer model not found or joblib not available.")
    except Exception as e:
        logger.exception(f"Error loading fertilizer model: {e}")

# Run loading
load_models()


# -------------------------------
# Routes and other functions
# (The rest of the file remains the same)
# -------------------------------

# ... (all other helper functions and routes are unchanged) ...
def detect_lang(text: str):
    try:
        return detect(text)
    except Exception:
        return "en"

def translate_to_en(text: str):
    try:
        return GoogleTranslator(source="auto", target="en").translate(text)
    except Exception:
        return text

def translate_from_en(text: str, target_lang: str):
    if target_lang == "en":
        return text
    try:
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
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
        logger.exception("TTS failed: %s", e)
        return None

def preprocess_image_for_model(img: Image.Image, target_size=(224, 224)):
    img = img.convert("RGB")
    img = img.resize(target_size)
    arr = np.asarray(img).astype("float32") / 255.0
    arr = np.expand_dims(arr, 0)
    return arr

def _search_faiss_local(query: str, top_k=FAISS_TOP_K):
    if faiss_index is None or sentence_model is None or not kcc_metadata:
        return []
    try:
        q_emb = sentence_model.encode([query], convert_to_numpy=True).astype("float32")
        D, I = faiss_index.search(q_emb, top_k)
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(kcc_metadata):
                continue
            try:
                dval = float(dist[0]) if isinstance(dist, (list, np.ndarray)) else float(dist)
            except Exception:
                dval = float(dist)
            score = 1.0 / (1.0 + dval)
            meta = kcc_metadata[idx]
            results.append({"score": score, "query": meta.get("query", ""), "answer": meta.get("answer", ""), "id": meta.get("id", idx)})
        return sorted(results, key=lambda x: x["score"], reverse=True)
    except Exception as e:
        logger.exception("FAISS local search failed: %s", e)
        return []

def ask_gemini_once(prompt_en: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API key not configured.")
    try:
        gen_model = genai.GenerativeModel("gemini-1.5-flash")
        resp = gen_model.generate_content(prompt_en)
        return resp.text if getattr(resp, "text", None) else ""
    except Exception as e:
        logger.exception("Gemini call failed: %s", e)
        raise

@app.route("/chat-image", methods=["POST"])
def chat_image():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400
    if disease_model is None:
        return jsonify({"error": "Disease model not loaded on server."}), 500
    try:
        f = request.files["image"]
        img = Image.open(f.stream)
        try:
            ishape = disease_model.input_shape
            h, w = (ishape[1], ishape[2]) if isinstance(ishape, (list, tuple)) and len(ishape) >= 3 else (224, 224)
            target_size = (w or 224, h or 224)
        except Exception:
            target_size = (224, 224)
        arr = preprocess_image_for_model(img, target_size=target_size)
        preds = disease_model.predict(arr, verbose=0)
        class_idx = int(np.argmax(preds, axis=1)[0])
        conf = float(np.max(preds))
        label = idx_to_class.get(class_idx, f"Class_{class_idx}").replace("_", " ")
        reply = f"Predicted disease: {label} (confidence {conf:.2f})"
        return jsonify({"answer": reply, "disease": label, "confidence": conf, "source": "disease_model"})
    except Exception as e:
        logger.exception("Disease prediction failed: %s", e)
        return jsonify({"error": "Disease prediction failed."}), 500

@app.route("/recommend", methods=["POST"])
def recommend_fertilizer():
    if fertilizer_model is None:
        return jsonify({"error": "Fertilizer model not loaded on server."}), 500
    if soil_encoder is None or crop_encoder is None or fertilizer_encoder is None:
        return jsonify({"error": "One or more fertilizer encoders not loaded. Ensure soil_encoder.pkl, crop_encoder.pkl and fertilizer_encoder.pkl are present."}), 500
    try:
        data = request.json or {}
        required = ["N", "P", "K", "moisture", "temperature", "humidity", "soil", "crop"]
        if not all(r in data for r in required):
            missing = [r for r in required if r not in data]
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
        
        features_data = [
            float(data["temperature"]), float(data["humidity"]), float(data["moisture"]),
            float(data["N"]), float(data["P"]), float(data["K"]),
            soil_encoder.transform([data["soil"]])[0],
            crop_encoder.transform([data["crop"]])[0]
        ]
        features = np.array([features_data])
        pred_encoded = fertilizer_model.predict(features)[0]
        fertilizer_name = fertilizer_encoder.inverse_transform([pred_encoded])[0]
        return jsonify({"recommendation": fertilizer_name})
    except Exception as e:
        logger.exception("Fertilizer recommendation failed: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route("/ask", methods=["POST"])
def ask_bot():
    body = request.json or {}
    prompt = body.get("question") or body.get("q", "")
    if not prompt:
        return jsonify({"error": "No question provided"}), 400
    user_lang = detect_lang(prompt)
    try:
        results = _search_faiss_local(prompt, top_k=FAISS_TOP_K)
        top = results[0] if results and results[0]["score"] >= FAISS_SCORE_THRESHOLD else None
        if top:
            answer_en = top["answer"]
            source = f"KCC (local) score={top['score']:.2f}"
        else:
            prompt_en = prompt if user_lang == "en" else translate_to_en(prompt)
            gemini_prompt = f"You are an agriculture expert. Answer succinctly and practically: {prompt_en}"
            answer_en = ask_gemini_once(gemini_prompt)
            source = "Gemini (fallback)"
        final_answer = answer_en if user_lang == "en" else translate_from_en(answer_en, user_lang)
        audio_b64 = text_to_audio_base64(final_answer, lang=user_lang)
        return jsonify({"answer": final_answer, "source": source, "audio_base64": audio_b64})
    except Exception as e:
        logger.exception("Error in ask endpoint: %s", e)
        return jsonify({"error": "Internal error answering the question."}), 500

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API key not configured on server."}), 500
    if not _audio_converter:
        return jsonify({"error": "Server cannot convert audio: ffmpeg not found."}), 500
    try:
        audio_file = request.files["audio"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1] or ".webm") as tmp_in:
            audio_file.save(tmp_in.name)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
            AudioSegment.from_file(tmp_in.name).export(tmp_wav.name, format="wav")
        text = ""
        try:
            uploaded = genai.upload_file(path=tmp_wav.name)
            speech_model = genai.GenerativeModel("gemini-1.5-flash-latest")
            resp = speech_model.generate_content(["Transcribe this audio.", uploaded])
            text = resp.text.strip() if getattr(resp, "text", None) else ""
        except Exception as gen_exc:
            logger.exception("Gemini transcription error: %s", gen_exc)
        if not text and sr is not None:
            try:
                r = sr.Recognizer()
                with sr.AudioFile(tmp_wav.name) as source:
                    audio_data = r.record(source)
                text = r.recognize_google(audio_data)
                logger.info("Local fallback transcription succeeded.")
            except Exception as local_exc:
                logger.warning("Local fallback transcription failed: %s", local_exc)
        os.unlink(tmp_in.name)
        os.unlink(tmp_wav.name)
        if text:
            return jsonify({"text": text})
        else:
            return jsonify({"error": "Transcription failed or returned empty text."}), 500
    except Exception as e:
        logger.exception("Transcription failed: %s", e)
        return jsonify({"error": "Failed to transcribe audio"}), 500

@app.route("/send-otp", methods=["POST"])
def send_otp():
    if otps is None: return jsonify({"success": False, "error": "Database not configured"}), 500
    data = request.json or {}
    phone = data.get("phone")
    if not phone: return jsonify({"success": False, "error": "Phone number required"}), 400
    otp = str(random.randint(100000, 999999))
    otps.update_one({"phone": phone}, {"$set": {"otp": otp}}, upsert=True)
    app.logger.info(f"OTP for {phone}: {otp}")
    return jsonify({"success": True, "message": "OTP sent", "otp": otp})

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    if otps is None or users is None: return jsonify({"success": False, "error": "Database not configured"}), 500
    data = request.json or {}
    phone, otp = data.get("phone"), data.get("otp")
    if not phone or not otp: return jsonify({"success": False, "error": "Phone and OTP required"}), 400
    otp_doc = otps.find_one({"phone": phone})
    if not otp_doc or otp_doc.get("otp") != otp:
        return jsonify({"success": False, "error": "Invalid OTP"}), 400
    user = users.find_one({"phone": phone})
    otps.delete_one({"phone": phone})
    return jsonify({"success": True, "message": "OTP verified successfully", "existing_user": bool(user)})

@app.route("/register-details", methods=["POST"])
def register_details():
    data = request.json or {}
    if not data.get("phone"): return jsonify({"error": "phone required"}), 400
    if users is not None:
        users.update_one({"phone": data["phone"]}, {"$set": data}, upsert=True)
    return jsonify({"message": "saved"}), 200

@app.route("/get-user", methods=["GET"])
def get_user():
    phone = request.args.get("phone")
    if phone and users is not None:
        user = users.find_one({"phone": phone}, {"_id": 0})
        if user: return jsonify(user)
    return jsonify({"name": "Guest User", "location": "Unknown"})

if __name__ == "__main__":
    logger.info("Starting Flask app...")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)