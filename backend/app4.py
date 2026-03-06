# app.py (corrected)
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
from pydub.utils import which  # used to find ffmpeg

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

# Optional local fallback for audio -> text
try:
    import speech_recognition as sr
except Exception:
    sr = None

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
    # other dev origins if needed
]

# Enable CORS and allow credentials (so your frontend can use cookies if needed)
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

idx_to_class = {}  # from class_indices.json if present

# Tuneables
FAISS_TOP_K = 5
FAISS_SCORE_THRESHOLD = 0.6

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)

# make sure pydub can find ffmpeg
_audio_converter = which("ffmpeg") or which("ffmpeg.exe")
if _audio_converter:
    AudioSegment.converter = _audio_converter
else:
    app.logger.warning("FFmpeg not found in PATH. Audio conversion (transcription) will likely fail. Install ffmpeg and restart.")

# -------------------------------
# Model loading
# -------------------------------

def load_models():
    global faiss_index, kcc_metadata, sentence_model
    global fertilizer_model, soil_encoder, crop_encoder, fertilizer_encoder
    global disease_model, disease_label_encoder, disease_class_map

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
    # 3) Load disease model (Keras .h5)
try:
    candidates = [
        os.path.join(SCRIPT_DIR, "plant_disease_identification_model.h5"),
        os.path.join(SCRIPT_DIR, "models", "plant_disease_identification_model.h5"),
        os.path.join(MODEL_DIR, "plant_disease_identification_model.h5"),
        os.path.join(SCRIPT_DIR, "Model.hdf5"),  # fallback
    ]
    model_path = next((p for p in candidates if p and os.path.exists(p)), None)

    if model_path and load_model is not None:
        disease_model = load_model(model_path)
        logger.info(f"✅ Loaded disease model from {model_path}")

        # optional class_indices.json
        json_candidates = [
            os.path.join(os.path.dirname(model_path), "class_indices.json"),
            os.path.join(SCRIPT_DIR, "class_indices.json"),
            os.path.join(MODEL_DIR, "class_indices.json"),
        ]
        json_path = next((p for p in json_candidates if p and os.path.exists(p)), None)

        if json_path:
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    disease_class_map = json.load(f)

                # Normalize → invert mapping to idx → class_name
                idx_to_class = {}
                for k, v in disease_class_map.items():
                    try:
                        idx_to_class[int(v)] = k
                    except Exception:
                        idx_to_class[k] = v

                logger.info(
                    f"✅ Loaded class_indices.json ({json_path}) with {len(idx_to_class)} classes."
                )
            except Exception as e:
                idx_to_class = {}
                logger.warning("⚠️ Failed to load class_indices.json: %s", e)
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
    logger.exception("❌ Error loading disease model: %s", e)

    # 4) Load fertilizer model + encoders (joblib)
    try:
        fert_candidates = [
            os.path.join(SCRIPT_DIR, "fertilizer_model.pkl"),
            os.path.join(SCRIPT_DIR, "models", "fertilizer_model.pkl"),
            os.path.join(MODEL_DIR, "fertilizer_model.pkl"),
        ]
        fert_model_path = next((p for p in fert_candidates if p and os.path.exists(p)), None)
        if fert_model_path and joblib is not None:
            fertilizer_model = joblib.load(fert_model_path)
            logger.info(f"✅ Loaded fertilizer model from {fert_model_path}")

            # encoders expected names (user-specified)
            soil_path = os.path.join(SCRIPT_DIR, "soil_encoder.pkl")
            crop_path = os.path.join(SCRIPT_DIR, "crop_encoder.pkl")
            fert_enc_path = os.path.join(SCRIPT_DIR, "fertilizer_encoder.pkl")

            # also check MODEL_DIR
            if not os.path.exists(soil_path):
                soil_path = os.path.join(MODEL_DIR, "soil_encoder.pkl")
            if not os.path.exists(crop_path):
                crop_path = os.path.join(MODEL_DIR, "crop_encoder.pkl")
            if not os.path.exists(fert_enc_path):
                fert_enc_path = os.path.join(MODEL_DIR, "fertilizer_encoder.pkl")

            try:
                if os.path.exists(soil_path):
                    soil_encoder = joblib.load(soil_path)
                    logger.info("✅ Loaded soil encoder.")
                if os.path.exists(crop_path):
                    crop_encoder = joblib.load(crop_path)
                    logger.info("✅ Loaded crop encoder.")
                if os.path.exists(fert_enc_path):
                    fertilizer_encoder = joblib.load(fert_enc_path)
                    logger.info("✅ Loaded fertilizer encoder.")
            except Exception as e:
                logger.warning("Could not load some fertilizer encoders: %s", e)
        else:
            logger.info("Fertilizer model not found or joblib not available.")
    except Exception as e:
        logger.exception("Error loading fertilizer model: %s", e)

# run loading
load_models()

# -------------------------------
# small helper utilities
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

def decode_disease_label(class_idx: int) -> str:
    """Return readable label for predicted numeric class index."""
    try:
        # If we have map class_name -> index, invert it to index->class_name
        if disease_class_map:
            inv = {}
            for k, v in disease_class_map.items():
                try:
                    inv[int(v)] = k
                except Exception:
                    # if value is already int
                    inv[v] = k
            if int(class_idx) in inv:
                return inv[int(class_idx)].replace("_", " ")
        if disease_label_encoder and hasattr(disease_label_encoder, "inverse_transform"):
            return disease_label_encoder.inverse_transform([class_idx])[0]
        if isinstance(disease_label_encoder, (list, tuple, dict, np.ndarray)):
            return disease_label_encoder[class_idx]
    except Exception:
        pass
    return str(class_idx)

# -------------------------------
# FAISS search (local embeddings)
# -------------------------------
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
            # map distance to score
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

# -------------------------------
# Gemini call (fallback)
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
# chat-image endpoint (disease)
# -------------------------------
def preprocess_image_for_model(img: Image.Image, target_size=(224, 224)):
    img = img.convert("RGB")
    img = img.resize(target_size)
    arr = np.asarray(img).astype("float32") / 255.0
    arr = np.expand_dims(arr, 0)
    return arr

@app.route("/chat-image", methods=["POST"])
def chat_image():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400
    if disease_model is None:
        return jsonify({"error": "Disease model not loaded on server."}), 500

    try:
        f = request.files["image"]
        img = Image.open(f.stream)

        # determine model input size safely
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

        label = decode_disease_label(class_idx)
        reply = f"Predicted disease: {label} (confidence {conf:.2f})"

        return jsonify({"answer": reply, "disease": label, "confidence": conf, "source": "disease_model"})
    except Exception as e:
        logger.exception("Disease prediction failed: %s", e)
        return jsonify({"error": "Disease prediction failed."}), 500

# -------------------------------
# Fertilizer recommendation endpoint
# -------------------------------
@app.route("/recommend", methods=["POST"])
def recommend():
    if fertilizer_model is None:
        return jsonify({"error": "Fertilizer model not loaded on server."}), 500
    if soil_encoder is None or crop_encoder is None or fertilizer_encoder is None:
        return jsonify({"error": "One or more fertilizer encoders not loaded (soil/crop/fertilizer). Ensure soil_encoder.pkl, crop_encoder.pkl and fertilizer_encoder.pkl are present."}), 500

    try:
        data = request.json or {}
        required = ["N", "P", "K", "moisture", "temperature", "humidity", "soil", "crop"]
        for r in required:
            if r not in data:
                return jsonify({"error": f"Missing field: {r}"}), 400

        soil_encoded = soil_encoder.transform([data["soil"]])[0]
        crop_encoded = crop_encoder.transform([data["crop"]])[0]

        features = np.array([[float(data["temperature"]), float(data["humidity"]), float(data["moisture"]),
                              float(data["N"]), float(data["K"]), float(data["P"]),
                              soil_encoded, crop_encoded]])
        pred_encoded = fertilizer_model.predict(features)[0]
        fertilizer_name = fertilizer_encoder.inverse_transform([pred_encoded])[0]

        return jsonify({"recommendation": fertilizer_name})
    except Exception as e:
        logger.exception("Fertilizer recommendation failed: %s", e)
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Chat endpoint
# -------------------------------
@app.route("/ask", methods=["POST"])
def ask_bot():
    body = request.json or {}
    prompt = body.get("question") or body.get("q") or ""
    if not prompt:
        return jsonify({"error": "No question provided"}), 400

    user_lang = detect_lang(prompt)
    try:
        results = _search_faiss_local(prompt, top_k=FAISS_TOP_K)
        top = results[0] if results else None
        if top and top["score"] >= FAISS_SCORE_THRESHOLD:
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

# -------------------------------
# Transcribe endpoint (robust with helpful messages)
# -------------------------------
@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API key not configured on server."}), 500

    if not _audio_converter:
        # Give a clear error for developer: FFmpeg not installed
        return jsonify({"error": "Server cannot convert audio: ffmpeg not found on server. Install ffmpeg and restart."}), 500

    try:
        audio_file = request.files["audio"]
        tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1] or ".webm", dir=SCRIPT_DIR)
        audio_file.save(tmp_in.name)
        tmp_in.close()

        tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=SCRIPT_DIR)
        audio_seg = AudioSegment.from_file(tmp_in.name)
        audio_seg.export(tmp_wav.name, format="wav")

        # Try Gemini upload & transcription
        try:
            try:
                uploaded = genai.upload_file(path=tmp_wav.name)
            except TypeError:
                uploaded = genai.upload_file(tmp_wav.name)

            speech_model = genai.GenerativeModel("gemini-1.5-flash-latest")
            resp = speech_model.generate_content(["Transcribe this audio.", uploaded])
            text = resp.text.strip() if getattr(resp, "text", None) else ""
        except Exception as gen_exc:
            logger.exception("Gemini transcription error: %s", gen_exc)
            text = ""

            # Optional local fallback with SpeechRecognition -> Google Web Speech (requires internet)
            if sr is not None:
                try:
                    r = sr.Recognizer()
                    with sr.AudioFile(tmp_wav.name) as source:
                        audio_data = r.record(source)
                    text = r.recognize_google(audio_data)
                    logger.info("Local fallback transcription succeeded.")
                except Exception as local_exc:
                    logger.warning("Local fallback transcription failed: %s", local_exc)
                    text = ""

        # cleanup
        try:
            os.unlink(tmp_in.name)
            os.unlink(tmp_wav.name)
        except Exception:
            pass

        if text:
            return jsonify({"text": text})
        else:
            return jsonify({"error": "Transcription failed or returned empty text."}), 500

    except Exception as e:
        logger.exception("Transcription failed: %s", e)
        return jsonify({"error": "Failed to transcribe audio"}), 500

# -------------------------------
# OTP and user endpoints (kept simple)
# -------------------------------
@app.route("/send-otp", methods=["POST"])
def send_otp():
    if otps is None:
        return jsonify({"success": False, "error": "Database not configured on server"}), 500
    data = request.json or {}
    phone = data.get("phone")
    if not phone:
        return jsonify({"success": False, "error": "Phone number required"}), 400
    otp = str(random.randint(100000, 999999))
    otps.update_one({"phone": phone}, {"$set": {"otp": otp}}, upsert=True)
    app.logger.info(f"OTP sent to {phone}: {otp}")
    return jsonify({"success": True, "message": "OTP sent", "otp": otp})

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
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
    user = users.find_one({"phone": phone})
    existing_user = bool(user)
    otps.delete_one({"phone": phone})
    return jsonify({"success": True, "message": "OTP verified successfully", "existing_user": existing_user})

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
        user = users.find_one({"phone": phone}, {"_id": 0})
        if user:
            return jsonify(user)
    return jsonify({"name": "Guest User", "location": "Unknown"})

# -------------------------------
# Run server
# -------------------------------
if __name__ == "__main__":
    logger.info("Starting Flask app...")
    app.run(host="0.0.0.0", port=5000, debug=True)
