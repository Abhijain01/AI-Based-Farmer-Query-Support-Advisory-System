# app.py
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
from pydub import AudioSegment  # requires ffmpeg installed on system

# Optional ML model libs (some may not be available; code handles missing models)
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

# Sentence Transformer for FAISS query embedding (local embeddings)
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

# -------------------------------
# Config & App init
# -------------------------------
load_dotenv()
app = Flask(__name__)

# Allowed frontend origins - add any dev origins you use
FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    #"http://localhost:3000",
    #"http://127.0.0.1:3000",
]

# Enable CORS and allow credentials (so your frontend can use cookies if needed)


CORS(
    app,
    resources={r"/*": {"origins": FRONTEND_ORIGINS}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"]
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

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY not set in .env - Gemini fallback will fail if used.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# MongoDB (optional, safe if MONGO_URI is missing)
client = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI)
        db = client.get_database("mywebapp_db")
        users = db["users"]
        otps = db["otps"]
        print("✅ Connected to MongoDB.")
    except Exception as e:
        print("⚠️ Could not connect to MongoDB:", e)
        users = otps = None
else:
    users = otps = None
    print("⚠️ MONGO_URI not provided; auth/otp endpoints will still work but DB not persistent.")

# -------------------------------
# Globals: models & search index
# -------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
faiss_index = None
kcc_metadata = None
sentence_model = None

# ML models
fertilizer_model = None
soil_encoder = None
crop_encoder = None
fertilizer_encoder = None
disease_model = None
disease_label_encoder = None
disease_class_map = None


# Tuning
FAISS_TOP_K = 5
FAISS_SCORE_THRESHOLD = 0.6  # tweak: 0.6-0.75 depending on index creation

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)


def safe_path(*parts):
    return os.path.join(*parts)


# -------------------------------
# Model loading (attempt)
# -------------------------------
def load_models():
    global fertilizer_model, soil_encoder, crop_encoder, fertilizer_encoder
    global disease_model, disease_label_encoder, disease_class_map
    # Load class_indices.json for disease model
    json_path = os.path.join(os.path.dirname(model_path), "class_indices.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                disease_class_map = json.load(f)
            logger.info(f"✅ Loaded class_indices.json with {len(disease_class_map)} classes")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load class_indices.json: {e}")


    # 1) Load KCC FAISS index + metadata
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
            logger.warning("KCC FAISS index or metadata file not found.")
    except Exception as e:
        logger.exception("Failed to load FAISS index: %s", e)

    # 2) Load sentence-transformer for embeddings (used for query encoding)
    try:
        if SentenceTransformer is not None:
            sentence_model_name = "paraphrase-multilingual-MiniLM-L12-v2"
            sentence_model = SentenceTransformer(sentence_model_name)
            logger.info(f"✅ Loaded sentence-transformer: {sentence_model_name}")
        else:
            logger.warning("sentence-transformers not available; FAISS search disabled.")
    except Exception as e:
        logger.exception("Failed to load sentence-transformer: %s", e)
        sentence_model = None

# 3) Load disease model if available (Keras .h5)
try:
    candidates = [
        os.path.join(SCRIPT_DIR, "plant_disease_identification_model.h5"),
        os.path.join(SCRIPT_DIR, "models", "plant_disease_identification_model.h5"),
        os.path.join(MODEL_DIR, "plant_disease_identification_model.h5"),
    ]
    model_path = next((p for p in candidates if os.path.exists(p)), None)
    if model_path and load_model is not None:
        disease_model = load_model(model_path)

        # try load label encoder (optional)
        le_path = os.path.join(os.path.dirname(model_path), "label_encoders.pkl")
        if os.path.exists(le_path):
            try:
                import pickle
                with open(le_path, "rb") as f:
                    disease_label_encoder = pickle.load(f)
            except Exception:
                disease_label_encoder = None

        # load class_indices.json
        json_path = os.path.join(os.path.dirname(model_path), "class_indices.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    disease_class_map = json.load(f)
                logger.info(f"✅ Loaded class_indices.json with {len(disease_class_map)} classes")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load class_indices.json: {e}")

        logger.info(f"✅ Loaded disease model from {model_path}")
    else:
        logger.warning("Disease model not found or TensorFlow not available.")
except Exception as e:
    logger.exception("Error loading disease model: %s", e)


# 4) Load fertilizer model (pickle/joblib)
try:
    fert_model_path = os.path.join(SCRIPT_DIR, "fertilizer_model.pkl")
    if os.path.exists(fert_model_path) and joblib is not None:
        fertilizer_model = joblib.load(fert_model_path)

        # load encoders
        fert_encoders = {}
        for enc_name in ["soil_encoder.pkl", "crop_encoder.pkl", "fertilizer_encoder.pkl"]:
            enc_path = os.path.join(SCRIPT_DIR, enc_name)
            if os.path.exists(enc_path):
                with open(enc_path, "rb") as f:
                    fert_encoders[enc_name.split("_")[0]] = joblib.load(f)
        logger.info(f"✅ Loaded fertilizer model and encoders")
    else:
        logger.warning("Fertilizer model not found or joblib not available.")
except Exception as e:
    logger.exception("Error loading fertilizer model: %s", e)



# Load at startup
load_models()

# -------------------------------
# Helper utils
# -------------------------------
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


# -------------------------------
# FAISS search (local embeddings)
# -------------------------------
def _search_faiss_local(query: str, top_k=FAISS_TOP_K):
    """
    Encode query using sentence transformer and search faiss index.
    Returns list of {'score', 'query', 'answer', 'id'} ordered by best first.
    Score is converted to a 0..1 range (higher is better) via 1/(1+dist).
    """
    if faiss_index is None or sentence_model is None or not kcc_metadata:
        return []

    try:
        q_emb = sentence_model.encode([query], convert_to_numpy=True).astype("float32")
        # do search
        D, I = faiss_index.search(q_emb, top_k)
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(kcc_metadata):
                continue
            # convert distance -> similarity-like score
            # (works both for L2 distances and IP results: if index used IP,
            # distances are actually similarity, but 1/(1+dist) still gives positive mapping)
            try:
                # dist may be scalar or array (if k>1)
                if isinstance(dist, (list, np.ndarray)):
                    dval = float(dist[0])
                else:
                    dval = float(dist)
            except Exception:
                dval = float(dist)
            score = 1.0 / (1.0 + dval)  # heuristic mapping to 0..1 (higher better)
            meta = kcc_metadata[idx]
            results.append({"score": score, "query": meta.get("query", ""), "answer": meta.get("answer", ""), "id": meta.get("id", idx)})
        # sort by score descending
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        return results
    except Exception as e:
        logger.exception("FAISS local search failed: %s", e)
        return []


# -------------------------------
# Gemini call (single fallback)
# -------------------------------
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


# -------------------------------
# Image disease endpoint (used by ChatView /chat-image)
# -------------------------------
def preprocess_image_for_model(img: Image.Image, target_size=(224, 224)):
    img = img.convert("RGB")
    img = img.resize(target_size)
    arr = np.asarray(img).astype("float32") / 255.0
    arr = np.expand_dims(arr, 0)
    return arr

@app.route("/chat-image", methods=["POST"])
def chat_image():
    """
    Receives image upload, runs disease model if available,
    and returns { answer: "...", disease: "...", confidence: 0.9 }.
    """
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400
    if disease_model is None:
        return jsonify({"error": "Disease model not loaded on server."}), 500

    try:
        f = request.files["image"]
        img = Image.open(f.stream)

        # determine target size from model if possible
        try:
            ishape = disease_model.input_shape
            if isinstance(ishape, (list, tuple)) and len(ishape) >= 3:
                h, w = ishape[1], ishape[2]
                target_size = (w or 224, h or 224)
            else:
                target_size = (224, 224)
        except Exception:
            target_size = (224, 224)

        arr = preprocess_image_for_model(img, target_size=target_size)
        preds = disease_model.predict(arr)
        class_idx = int(np.argmax(preds, axis=1)[0])
        conf = float(np.max(preds))

        # decode label safely
        label = None
        try:
            if disease_class_map:
                # invert the dict {class_name: index} -> {index: class_name}
                inv_map = {v: k for k, v in disease_class_map.items()}
                label = inv_map.get(class_idx, str(class_idx))
                label = label.replace("_", " ")
            elif hasattr(disease_label_encoder, "inverse_transform"):
                label = disease_label_encoder.inverse_transform([class_idx])[0]
            elif isinstance(disease_label_encoder, (list, tuple, dict, np.ndarray)):
                label = disease_label_encoder[class_idx]
        except Exception:
            label = str(class_idx)

        return jsonify({
            "disease": label,
            "confidence": conf,
            "answer": f"The plant is likely affected by {label} with {conf:.2%} confidence."
        })

    except Exception as e:
        logger.exception("Error in chat-image endpoint: %s", e)
        return jsonify({"error": "Failed to process image"}), 500



# -------------------------------
# Fertilizer recommendation endpoint
# -------------------------------
@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        data = request.json
        # Required fields (without pH)
        required = ["N", "P", "K", "moisture", "temperature", "humidity", "soil", "crop"]
        for r in required:
            if r not in data:
                return jsonify({"error": f"Missing field: {r}"}), 400

        # Encode soil and crop
        soil_encoded = soil_encoder.transform([data["soil"]])[0]
        crop_encoded = crop_encoder.transform([data["crop"]])[0]

        # Match training feature order: [Temp, Humidity, Moisture, N, K, P, Soil, Crop]
        features = np.array([[
            float(data["temperature"]),
            float(data["humidity"]),
            float(data["moisture"]),
            float(data["N"]),
            float(data["K"]),
            float(data["P"]),
            soil_encoded,
            crop_encoded
        ]])

        # Prediction
        pred_encoded = fertilizer_model.predict(features)[0]
        fertilizer_name = fertilizer_encoder.inverse_transform([pred_encoded])[0]

        return jsonify({"recommendation": fertilizer_name})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------
# Chat endpoint (KCC + Gemini fallback)
# -------------------------------
@app.route("/ask", methods=["POST"])
def ask_bot():
    body = request.json or {}
    prompt = body.get("question") or body.get("q") or ""
    if not prompt:
        return jsonify({"error": "No question provided"}), 400

    user_lang = detect_lang(prompt)
    # For retrieval, use query as-is (sentence-transformer handles multilingual)
    # But for Gemini fallback, we prefer to send English prompt
    try:
        results = _search_faiss_local(prompt, top_k=FAISS_TOP_K)
        top = results[0] if results else None
        if top and top["score"] >= FAISS_SCORE_THRESHOLD:
            answer_en = top["answer"]
            source = f"KCC (local) score={top['score']:.2f}"
        else:
            # fallback: call Gemini once
            prompt_en = prompt if user_lang == "en" else translate_to_en(prompt)
            gemini_prompt = f"You are an agriculture expert. Answer succinctly and practically: {prompt_en}"
            answer_en = ask_gemini_once(gemini_prompt)
            source = "Gemini (fallback)"

        # translate back if needed
        final_answer = answer_en
        if user_lang != "en":
            final_answer = translate_from_en(answer_en, user_lang)

        # produce audio
        audio_b64 = text_to_audio_base64(final_answer, lang=user_lang)

        return jsonify({"answer": final_answer, "source": source, "audio_base64": audio_b64})
    except Exception as e:
        logger.exception("Error in ask endpoint: %s", e)
        return jsonify({"error": "Internal error answering the question."}), 500


# -------------------------------
# Robust /transcribe endpoint (save -> convert -> upload)
# -------------------------------
@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API key not configured on server."}), 500

    try:
        audio_file = request.files["audio"]
        # save to temp file
        tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1] or ".webm", dir=SCRIPT_DIR)
        audio_file.save(tmp_in.name)
        tmp_in.close()

        # convert to wav (pydub uses ffmpeg)
        tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=SCRIPT_DIR)
        audio_seg = AudioSegment.from_file(tmp_in.name)
        audio_seg.export(tmp_wav.name, format="wav")

        # upload converted file to Gemini
        try:
            # genai.upload_file accepts path in many versions
            uploaded = genai.upload_file(path=tmp_wav.name)
        except TypeError:
            uploaded = genai.upload_file(tmp_wav.name)

        speech_model = genai.GenerativeModel("gemini-1.5-flash-latest")
        resp = speech_model.generate_content(["Transcribe this audio.", uploaded])
        text = resp.text.strip() if getattr(resp, "text", None) else ""

        # cleanup
        try:
            os.unlink(tmp_in.name)
            os.unlink(tmp_wav.name)
        except Exception:
            pass

        return jsonify({"text": text})
    except Exception as e:
        logger.exception("Transcription failed: %s", e)
        return jsonify({"error": "Failed to transcribe audio"}), 500


# -------------------------------
# Other small endpoints (auth) - existing logic preserved
# -------------------------------
# -------------------------------
# -------------------------------
# OTP Endpoints
# -------------------------------
# app.py

# ... (keep all your other code the same) ...


# -------------------------------
# OTP Endpoints (Corrected)
# -------------------------------

@app.route("/send-otp", methods=["POST"])
def send_otp():
    """Send a new OTP to the given phone number."""
    if otps is None:
        return jsonify({"success": False, "error": "Database not configured on server"}), 500

    data = request.json or {}
    phone = data.get("phone")
    if not phone:
        return jsonify({"success": False, "error": "Phone number required"}), 400

    otp = str(random.randint(100000, 999999))
    
    otps.update_one({"phone": phone}, {"$set": {"otp": otp}}, upsert=True)
    app.logger.info(f"OTP sent to {phone}: {otp}")

    # In a real app, you would integrate an SMS service here instead of returning the OTP.
    return jsonify({"success": True, "message": "OTP sent", "otp": otp})


@app.route("/resend-otp", methods=["POST"])
def resend_otp_endpoint():
    """Resend OTP to an existing phone number."""
    if otps is None:
        return jsonify({"success": False, "error": "Database not configured on server"}), 500
        
    data = request.json or {}
    phone = data.get("phone")
    if not phone:
        return jsonify({"success": False, "error": "Phone number required"}), 400

    otp = str(random.randint(100000, 999999))
    otps.update_one({"phone": phone}, {"$set": {"otp": otp}}, upsert=True)
    app.logger.info(f"OTP resent to {phone}: {otp}")

    return jsonify({"success": True, "message": "OTP resent", "otp": otp})


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    """Verify OTP for a phone number."""
    if otps is None or users is None:
        return jsonify({"success": False, "error": "Database not configured on server"}), 500

    data = request.json or {}
    phone = data.get("phone")
    otp = data.get("otp")

    if not phone or not otp:
        return jsonify({"success": False, "error": "Phone and OTP required"}), 400

    otp_doc = otps.find_one({"phone": phone})
    if not otp_doc or otp_doc.get("otp") != otp:
        return jsonify({"success": False, "error": "Invalid OTP"}), 400

    # check if user exists
    user = users.find_one({"phone": phone})
    existing_user = bool(user)

    # delete OTP after verification
    otps.delete_one({"phone": phone})

    return jsonify({
        "success": True,
        "message": "OTP verified successfully",
        "existing_user": existing_user
    })

# ... 


@app.route("/register-details", methods=["POST"])
def register_details():
    data = request.json or {}
    if not data.get("phone"):
        return jsonify({"error": "phone required"}), 400
    if users is not None:
        users.update_one({"phone": data["phone"]}, {"$set": data}, upsert=True)
    return jsonify({"message": "saved"}), 200


@app.route("/get-user", methods=["GET"])
def get_user():
    phone = request.args.get("phone")
    if phone and users is not None:
        user = users.find_one({"phone": phone}, {"_id": 0}) if users is not None else None

        if user:
            return jsonify(user)
    return jsonify({"name": "Guest User", "location": "Unknown"})


# -------------------------------
# Run server
# -------------------------------
if __name__ == "__main__":
    logger.info("Starting Flask app...")
    app.run(host="0.0.0.0", port=5000, debug=True)
