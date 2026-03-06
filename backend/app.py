# app.py - Integrated Flask backend with ML, OTP, user, marketplace, and utilities
# Optimized for free tiers: lazy model loading, optional deps, dynamic PORT binding.
# Gemini fixes: AI Studio endpoint enforced, model alias + fallbacks, better error handling.

import os
import io
import json
import random
import tempfile
import base64
import logging
import threading
import time
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

# HTTP requests for external APIs
import requests

# ML / utils
import numpy as np
# Make FAISS optional (reduces build failures on free tiers)
try:
    import faiss  # pip install faiss-cpu (optional)
except Exception:
    faiss = None

# Not directly used but kept if you extend feature engineering later
try:
    from sklearn.preprocessing import normalize  # noqa: F401
except Exception:
    normalize = None


try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

from langdetect import detect
import google.generativeai as genai
from gtts import gTTS
from pydub import AudioSegment
from pydub.utils import which

# Optional ML model libs
try:
    # Use mmap_mode to save RAM? Not supported by TF, but we can handle MemoryError
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    from tensorflow.keras.preprocessing import image
    # For newer TF versions
    from tensorflow.keras.utils import img_to_array
except ImportError:
    tf = None
    load_model = None
    image = None
    img_to_array = None
try:
    import joblib
except Exception:
    joblib = None

try:
    import tensorflow as tf  # noqa: F401
    from tensorflow.keras.models import load_model
    from tensorflow.keras.preprocessing import image  # noqa: F401
    from PIL import Image
except Exception:
    tf = None
    load_model = None
    try:
        from PIL import Image
    except Exception:
        Image = None

try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

# Better handling of Google API exceptions (optional)
try:
    from google.api_core.exceptions import NotFound, PermissionDenied, Forbidden, ResourceExhausted, DeadlineExceeded
except Exception:
    NotFound = type("NotFound", (Exception,), {})
    PermissionDenied = type("PermissionDenied", (Exception,), {})
    Forbidden = type("Forbidden", (Exception,), {})
    ResourceExhausted = type("ResourceExhausted", (Exception,), {})
    DeadlineExceeded = type("DeadlineExceeded", (Exception,), {})

# -------------------------------
# Config & App init
# -------------------------------
load_dotenv()
app = Flask(__name__)

# Allow-list frontend origins (configurable via env, comma-separated)
FRONTEND_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    ).split(",")
    if o.strip()
]

CORS(
    app,
    resources={r"/*": {"origins": FRONTEND_ORIGINS}},
    supports_credentials=True,
)

# Env variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
# Accept both GEMINI_API_KEY and GOOGLE_API_KEY
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
# Allow override of the model via env
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
# Force AI Studio endpoint (not Vertex)
GENAI_API_ENDPOINT = os.getenv("GENAI_API_ENDPOINT", "https://generativelanguage.googleapis.com")
MODEL_DIR = os.getenv("MODEL_DIR", os.path.join(os.path.dirname(__file__), "models"))
WEATHER_API = os.getenv("WEATHER_API", "")  # optional

# Configure Google Generative AI client
# Configure Google Generative AI client
if GEMINI_API_KEY:
    try:
        # Simple configuration is often more robust
        genai.configure(api_key=GEMINI_API_KEY)
        app.logger.info("✅ Configured Google Generative AI client.")
    except Exception as e:
        app.logger.warning(f"⚠️ Failed to configure Gemini: {e}")
else:
    app.logger.warning("GEMINI_API_KEY/GOOGLE_API_KEY not set in env - Gemini calls will fail if used.")

# MongoDB or MockDB
client = None
db = None
users = None
otps = None
listings_col = None

class MockCollection:
    def __init__(self, name):
        self.name = name
        self.data = {}  # {id: document}
        self.lock = threading.Lock()

    def find_one(self, query, projection=None):
        with self.lock:
            for doc in self.data.values():
                if all(doc.get(k) == v for k, v in query.items()):
                    # projection support is minimal here
                    if projection and "_id" in projection and projection["_id"] == 0:
                        doc_copy = doc.copy()
                        doc_copy.pop("_id", None)
                        return doc_copy
                    return doc
            return None

    def insert_one(self, document):
        with self.lock:
            if "_id" not in document:
                document["_id"] = str(random.randint(100000, 999999))
            self.data[document["_id"]] = document
            return document

    def insert_many(self, documents):
        with self.lock:
            for doc in documents:
                if "_id" not in doc:
                    doc["_id"] = str(random.randint(100000, 999999))
                self.data[doc["_id"]] = doc
            return documents

    def update_one(self, query, update, upsert=False):
        with self.lock:
            doc = self.find_one(query)
            if doc:
                # limited support for $set and $addToSet
                if "$set" in update:
                    doc.update(update["$set"])
                if "$addToSet" in update:
                    for k, v in update["$addToSet"].items():
                        if k not in doc:
                            doc[k] = [] if not isinstance(doc.get(k), list) else doc[k]
                        if isinstance(doc[k], list) and v not in doc[k]:
                            doc[k].append(v)
                return doc
            elif upsert:
                # create new
                new_doc = query.copy()
                if "$set" in update:
                    new_doc.update(update["$set"])
                self.insert_one(new_doc)
                return new_doc
            return None

    def delete_one(self, query):
        with self.lock:
            found_id = None
            for doc_id, doc in self.data.items():
                if all(doc.get(k) == v for k, v in query.items()):
                    found_id = doc_id
                    break
            if found_id:
                del self.data[found_id]
                return True
            return False

    def count_documents(self, query):
        with self.lock:
            count = 0
            for doc in self.data.values():
                if all(doc.get(k) == v for k, v in query.items()):
                    count += 1
            return count
    
    def find(self, query, projection=None):
         # returns a list instead of cursor
         with self.lock:
            results = []
            for doc in self.data.values():
                if all(doc.get(k) == v for k, v in query.items()):
                    if projection and "_id" in projection and projection["_id"] == 0:
                        doc_copy = doc.copy()
                        doc_copy.pop("_id", None)
                        results.append(doc_copy)
                    else:
                        results.append(doc)
            return results

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000) # 2s timeout
    client.server_info() # force check
    db = client.get_database("mywebapp_db")
    users = db["users"]
    otps = db["otps"]
    listings_col = db["buyer_requests"]
    app.logger.info("✅ Connected to MongoDB.")
except Exception as e:
    app.logger.warning("⚠️ Could not connect to MongoDB (%s). Using In-Memory MockDB.", e)
    users = MockCollection("users")
    otps = MockCollection("otps")
    listings_col = MockCollection("buyer_requests")

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

# explicitly check common paths
known_ffmpeg = [
    r"C:\Users\abhis\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe",
    "ffmpeg", "ffmpeg.exe"
]
_audio_converter = None
for p in known_ffmpeg:
    v = which(p)
    if v:
        _audio_converter = v
        break

if _audio_converter:
    AudioSegment.converter = _audio_converter
else:
    app.logger.warning("FFmpeg not found in PATH. Audio conversion (/transcribe) will likely fail.")

# -------------------------------
# Gemini helpers (robust alias + fallbacks)
# -------------------------------
def _gemini_model_candidates():
    # Try the requested model, then explicit "models/" form, then fallbacks
    model_env = GEMINI_MODEL.strip()
    names = [
        # Available/Working models (Prioritized)
        "gemini-3-flash-preview", 
        "gemini-2.5-flash",
        "models/gemini-2.5-flash",
        "gemini-2.0-flash",
        "models/gemini-2.0-flash",
        "gemini-flash-latest",
        "models/gemini-flash-latest",
        # User requested model (if any)
        model_env,
        f"models/{model_env}" if not model_env.startswith(("models/", "publishers/")) else model_env,
        # Fallbacks (may fail)
        "gemini-1.5-flash",
        "models/gemini-1.5-flash", 
        "gemini-1.5-pro",
        "models/gemini-1.5-pro",
    ]
    # De-duplicate while preserving order
    seen = set()
    out = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out

def _gemini_generate(prompt, timeout_s=45):
    """Try multiple model names to avoid 404s on retired/region-gated revisions."""
    if not GEMINI_API_KEY:
        return None
    last_exc = None
    
    # Use the robust candidate list
    candidates = _gemini_model_candidates()
    
    for name in candidates:
        try:
            logger.info(f"Gemini trying model: {name}")
            model = genai.GenerativeModel(name)
            # Reduced timeout to fail fast
            resp = model.generate_content(prompt, request_options={"timeout": 20})
            text = getattr(resp, "text", None)
            if text:
                return text
            last_exc = RuntimeError("Empty text in Gemini response")
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "Quota" in err_msg:
                 logger.warning(f"Gemini {name} QUOTA EXCEEDED: {e}")
            else:
                 logger.info(f"Model {name} failed/skipped: {e}")
            last_exc = e
            continue
            
    if last_exc:
        logger.exception("Gemini call failed after trying candidates: %s", last_exc)
    return None

def _gemini_generate_with_file(parts, timeout_s=90):
    """Same as _gemini_generate but for multimodal parts (e.g., file inputs)."""
    if not GEMINI_API_KEY:
        return None
    last_exc = None
    for name in _gemini_model_candidates():
        try:
            logger.info(f"Gemini (file) trying model: {name}")
            model = genai.GenerativeModel(name)
            resp = model.generate_content(parts, request_options={"timeout": timeout_s})
            text = getattr(resp, "text", None)
            if text:
                return text.strip()
            last_exc = RuntimeError("Empty text in Gemini response")
        except (NotFound,) as e:
            last_exc = e
            logger.warning(f"Model not found/inaccessible: {name} ({e}) — trying next candidate.")
            continue
        except (PermissionDenied, Forbidden) as e:
            last_exc = e
            logger.error(f"Permission error with model {name}: {e}")
            break
        except (ResourceExhausted, DeadlineExceeded) as e:
            last_exc = e
            logger.warning(f"Rate limit/timeout with model {name}: {e} — will try next candidate.")
            continue
        except Exception as e:
            last_exc = e
            logger.exception(f"Gemini generate_content (file) error with model {name}: {e}")
            continue
    if last_exc:
        logger.exception("Gemini (file) call failed after trying candidates: %s", last_exc)
    return None

# -------------------------------
# Model loading (lazy)
# -------------------------------
def load_models():
    """Load optional ML models/encoders in background to avoid blocking startup."""
    global faiss_index, kcc_metadata, sentence_model
    global fertilizer_model, soil_encoder, crop_encoder, fertilizer_encoder
    global disease_model, idx_to_class

    # 1) Load KCC FAISS index + metadata (if present and faiss available)
    try:
        if faiss is not None:
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
                logger.info("ℹ️ KCC FAISS files not found; FAISS search disabled.")
        else:
            logger.info("ℹ️ faiss not installed; FAISS search disabled.")
    except Exception as e:
        logger.exception("Failed to load FAISS index: %s", e)

    # 2) Load sentence-transformer for embeddings if available
    try:
        if SentenceTransformer is not None:
            sentence_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            logger.info("✅ Loaded sentence-transformer model.")
        else:
            logger.info("ℹ️ sentence-transformers not installed; skipping local embedding generation.")
    except Exception as e:
        logger.exception("Failed to load sentence-transformer: %s", e)
        sentence_model = None

    # 3) Load disease model (Keras .h5) if TensorFlow available
    try:
        model_path_candidates = [
            os.path.join(SCRIPT_DIR, "plant_disease_identification_model.h5"),
            os.path.join(MODEL_DIR, "plant_disease_identification_model.h5"),
        ]
        model_path = next((p for p in model_path_candidates if p and os.path.exists(p)), None)
        if model_path and load_model is not None and Image is not None:
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
            logger.info("ℹ️ Disease model not loaded (TensorFlow or model file missing).")
    except Exception as e:
        disease_model = None
        idx_to_class = {}
        logger.exception(f"❌ Error loading disease model: {e}")

    # 4) Load fertilizer model + encoders (joblib/pickle)
    try:
        fert_candidates = [
            os.path.join(SCRIPT_DIR, "fertilizer_model.pkl"),
            os.path.join(MODEL_DIR, "fertilizer_model.pkl"),
        ]
        fert_model_path = next((p for p in fert_candidates if p and os.path.exists(p)), None)

        if fert_model_path and joblib is not None:
            # FIX: Use mmap_mode='r' to load large models (1.8GB) from disk without consuming RAM
            fertilizer_model = joblib.load(fert_model_path, mmap_mode='r')
            logger.info(f"✅ Loaded fertilizer model from {fert_model_path} (mmap)")

            # Paths for encoders (in script dir)
            soil_path = os.path.join(SCRIPT_DIR, "soil_encoder.pkl")
            crop_path = os.path.join(SCRIPT_DIR, "crop_encoder.pkl")
            fert_enc_path = os.path.join(SCRIPT_DIR, "fertilizer_encoder.pkl")

            try:
                if os.path.exists(soil_path):
                    soil_encoder = joblib.load(soil_path, mmap_mode='r')
                    logger.info("✅ Loaded soil_encoder.pkl (mmap).")
                else:
                    logger.warning("⚠️ soil_encoder.pkl not found.")

                if os.path.exists(crop_path):
                    crop_encoder = joblib.load(crop_path, mmap_mode='r')
                    logger.info("✅ Loaded crop_encoder.pkl (mmap).")
                else:
                    logger.warning("⚠️ crop_encoder.pkl not found.")

                if os.path.exists(fert_enc_path):
                    fertilizer_encoder = joblib.load(fert_enc_path, mmap_mode='r')
                    logger.info("✅ Loaded fertilizer_encoder.pkl (mmap).")
                else:
                    logger.warning("⚠️ fertilizer_encoder.pkl not found.")

            except Exception as e:
                logger.warning(f"Could not load one or more fertilizer encoders: {e}")
        else:
            fertilizer_model = None
            logger.info("ℹ️ Fertilizer model not found or joblib not available.")
    except Exception as e:
        logger.exception(f"Error loading fertilizer model: {e}")

    # 5) General Memory Check (Optional explicit check)
    # If any models failed due to memory, we log a summary.
    pass

def safe_load_models():
    """Wrapper to catch critical memory errors during loading."""
    try:
        load_models()
    except MemoryError:
        logger.error("❌ OUT OF MEMORY: The server lacks sufficient RAM to load ML models.")
        logger.error("⚠️ The app will continue running, but ML features (predictions) will be disabled.")
    except Exception as e:
        logger.exception(f"Unexpected error in model loader thread: {e}")

# Start model loading in background as soon as the app module is imported.
if not os.getenv("SKIP_ML"):
    threading.Thread(target=safe_load_models, daemon=True).start()
else:
    logger.info("⚠️ SKIP_ML is set. ML models will not be loaded.")

# -------------------------------
# Helpers
# -------------------------------
def detect_lang(text: str):
    try:
        return detect(text)
    except Exception:
        return "en"

def translate_to_en(text: str):
    if not GoogleTranslator:
        return text
    try:
        return GoogleTranslator(source="auto", target="en").translate(text)
    except Exception as e:
        logger.debug(f"Translation failed: {e}")
        return text

def translate_from_en(text: str, target_lang: str):
    if target_lang == "en" or not GoogleTranslator:
        return text
    try:
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
        return text

import re

def clean_text_for_tts(text: str) -> str:
    # Remove markdown bold/italic (* or _)
    text = re.sub(r"[\*_]+", "", text)
    # Remove headers (#)
    text = re.sub(r"#+", "", text)
    # Remove links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove code blocks (backticks)
    text = re.sub(r"`+", "", text)
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def text_to_audio_base64(text: str, lang: str = "en"):
    try:
        # Clean markdown for professional voice output
        clean_text = clean_text_for_tts(text)
        logger.info(f"Generating TTS for text: {clean_text[:50]}... (lang={lang})")
        
        mp3_fp = io.BytesIO()
        # Use 'com' for better reliability as 'co.in' was timing out
        tld_map = {"en": "com", "ml": "co.in"} 
        tts = gTTS(text=clean_text, lang=lang, tld=tld_map.get(lang, "com"))
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        b64 = base64.b64encode(mp3_fp.read()).decode()
        logger.info(f"TTS generated successfully, length: {len(b64)}")
        return b64
    except Exception as e:
        logger.exception("TTS failed: %s", e)
        return None

def preprocess_image_for_model(img: "Image.Image", target_size=(224, 224)):
    if Image is None:
        raise RuntimeError("Pillow not installed on server.")
    img = img.convert("RGB")
    img = img.resize(target_size)
    arr = np.asarray(img).astype("float32") / 255.0
    arr = np.expand_dims(arr, 0)
    return arr

def _search_faiss_local(query: str, top_k=FAISS_TOP_K):
    if faiss is None:
        return []
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
            results.append({
                "score": score,
                "query": meta.get("query", ""),
                "answer": meta.get("answer", ""),
                "id": meta.get("id", idx)
            })
        return sorted(results, key=lambda x: x["score"], reverse=True)
    except Exception as e:
        logger.exception("FAISS local search failed: %s", e)
        return []

def ask_gemini_once(prompt_en: str) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API key is not configured on the server."
    try:
        text = _gemini_generate(prompt_en, timeout_s=45)
        return text if text else "I’m having trouble connecting to Gemini right now."
    except Exception as e:
        logger.exception("Gemini call failed: %s", e)
        return "I’m having trouble connecting to Gemini right now."

# -------------------------------
# Routes
# -------------------------------

# Health checks
@app.route("/health")
def health():
    return jsonify({"ok": True})

@app.route("/db-health")
def db_health():
    try:
        count = users.count_documents({}) if users else 0
        return jsonify({"ok": True, "count": count})
    except Exception as e:
        logger.exception("DB health failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/gemini-health")
def gemini_health():
    if not GEMINI_API_KEY:
        return jsonify({"ok": False, "error": "Missing GEMINI_API_KEY/GOOGLE_API_KEY"}), 500
    try:
        txt = ask_gemini_once("Say 'pong' in one word.")
        ok = isinstance(txt, str) and "pong" in txt.lower()
        return jsonify({"ok": ok, "reply": txt}), (200 if ok else 500)
    except Exception as e:
        logger.exception("Gemini health check failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500

# Home route
@app.route("/")
def home():
    return jsonify({"message": "Flask backend is running 🚀"})

# Image disease prediction
@app.route("/chat-image", methods=["POST"])
def chat_image():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    # 1. Try Local Model
    local_prediction = None
    if disease_model is not None and Image is not None:
        try:
            f = request.files["image"]
            img = Image.open(f.stream)
            try:
                ishape = getattr(disease_model, "input_shape", None)
                h, w = (ishape[1], ishape[2]) if isinstance(ishape, (list, tuple)) and len(ishape) >= 3 else (224, 224)
                target_size = (w or 224, h or 224)
            except Exception:
                target_size = (224, 224)
            arr = preprocess_image_for_model(img, target_size=target_size)
            preds = disease_model.predict(arr, verbose=0)
            class_idx = int(np.argmax(preds, axis=1)[0])
            conf = float(np.max(preds))
            local_prediction = idx_to_class.get(class_idx, f"Class_{class_idx}").replace("_", " ")
            logger.info(f"Local model predicted: {local_prediction} ({conf:.2f})")
        except Exception as e:
            logger.exception("Local disease prediction failed: %s", e)
    
    # 1.5 FAISS Search (New)
    faiss_context = ""
    if local_prediction:
        try:
            # Search for the predicted disease in the knowledge base
            results = _search_faiss_local(local_prediction, top_k=2)
            if results and results[0]["score"] > 0.5:
                faiss_context = "\n\nRelevant Knowledge Base Info:\n"
                for res in results:
                     faiss_context += f"- Q: {res['query']}\n  A: {res['answer']}\n"
        except Exception as e:
            logger.warning(f"FAISS search failed during image chat: {e}")

    # 2. Use Gemini (Hybrid or Fallback)
    if GEMINI_API_KEY:
        try:
            f = request.files["image"]
            f.seek(0) # Reset pointer
            img_data = f.read()
            import io
            pil_img = Image.open(io.BytesIO(img_data))
            
            # Helper to try generation
            def try_generate(m_name):
                logger.info(f"Gemini (Vision) trying model: {m_name}")
                model = genai.GenerativeModel(m_name)
                
                # Check for user question
                user_q = request.form.get("question") or request.form.get("q")
                
                if local_prediction:
                     base_prompt = (f"I have a plant image. My local analysis tool identified the issue as '{local_prediction}'. "
                                    f"{faiss_context if faiss_context else ''}")
                     
                     if user_q:
                         # User asked something specific
                         prompt = f"{base_prompt}\nThe user asks: '{user_q}'. Please answer their question utilizing the image and context provided."
                     else:
                         # Default analysis
                         prompt = (f"{base_prompt}\nPlease confirm if this looks correct based on the image, and then provide a 3-sentence practical remedy "
                                   f"specifically for '{local_prediction}'. "
                                   f"If the image clearly shows something else, please correct me.")
                else:
                     if user_q:
                         prompt = f"Analyze this plant/crop image. User question: '{user_q}'"
                     else:
                         prompt = "Analyze this plant/crop image. Identify any disease, pest, or deficiency. If it looks healthy, say so. Provide a short, practical 2-sentence recommendation."
                
                return model.generate_content([prompt, pil_img], request_options={"timeout": 30})

            # Try configured model first (flash), then fallback to pro
            resp = None
            last_err = None
            
            # List of models to try in order (Prioritize working models)
            candidates = [
                "gemini-3-flash-preview",
                "gemini-2.5-flash", 
                "gemini-2.0-flash", 
                "gemini-flash-latest",
                GEMINI_MODEL,
            ]
            # Remove duplicates/None while preserving order
            candidates = list(dict.fromkeys([c for c in candidates if c]))
            logger.info(f"DEBUG: Using candidates: {candidates}")

            for model_name in candidates:
                try:
                    resp = try_generate(model_name)
                    if resp:
                        break
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "Quota" in err_msg:
                        logger.warning(f"Gemini {model_name} QUOTA EXCEEDED: {e}")
                    elif "404" in err_msg:
                        logger.info(f"Gemini {model_name} not found/supported.")
                    else:
                        logger.info(f"Gemini {model_name} error: {e}")
                    last_err = e
            
            if not resp:
                raise last_err or Exception("All Gemini models failed")

            text = getattr(resp, "text", "I could not analyze the image (empty response).")
            
            final_disease = local_prediction if local_prediction else "Analyzed by AI"
            # Show which model actually worked in the source
            used_model = model_name 
            source = f"Hybrid (Local + {used_model})" if local_prediction else f"Gemini ({used_model})"
            
            return jsonify({"answer": text, "disease": final_disease, "confidence": 1.0, "source": source})
            
        except Exception as e:
            logger.exception("Gemini image analysis failed: %s", e)
            # If Gemini fails but we had a local prediction, return that!
            # If Gemini fails but we had a local prediction, return that!
            if local_prediction:
                 fallback_ans = f"Gemini is unreachable (Error: {str(e)}), but our local model detected: {local_prediction}."
                 if faiss_context:
                     fallback_ans += f"\n\n{faiss_context}"
                 else:
                     fallback_ans += f" Please check standard remedies for {local_prediction}."

                 return jsonify({
                     "answer": fallback_ans, 
                     "disease": local_prediction, 
                     "confidence": 0.9, 
                     "source": "Local Model + FAISS (Gemini Failed)"
                 })
            return jsonify({"error": f"Image analysis failed: {str(e)}", "details": str(e)}), 500

    if local_prediction:
         return jsonify({
             "answer": f"AI advice unavailable (no key), but predicted: {local_prediction}", 
             "disease": local_prediction, 
             "confidence": 0.9, 
             "source": "Local Model Only"
         })

    return jsonify({"error": "Disease model not loaded and Gemini API key missing."}), 500


# Fertilizer recommendation
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
        # Return a generic error to avoid leaking implementation details.
        return jsonify({"error": "Failed to get fertilizer recommendation due to an internal error."}), 500

# Knowledge Q&A with FAISS + Gemini + TTS
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
        
        # Clean markdown symbols for both display and TTS (since frontend doesn't render MD)
        final_answer = clean_text_for_tts(final_answer)
        
        audio_b64 = text_to_audio_base64(final_answer, lang=user_lang)
        return jsonify({"answer": final_answer, "source": source, "audio_base64": audio_b64})
    except Exception as e:
        logger.exception("Error in ask endpoint: %s", e)
        return jsonify({"error": f"Internal error answering the question: {str(e)}", "details": str(e)}), 500

# Transcription (Gemini + local fallback)
@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API key not configured on server."}), 500
    if not _audio_converter:
        return jsonify({"error": "Server cannot convert audio: ffmpeg not found."}), 500

    tmp_in_path, tmp_wav_path = None, None
    uploaded = None
    try:
        audio_file = request.files["audio"]

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1] or ".webm") as tmp_in:
            audio_file.save(tmp_in.name)
            tmp_in_path = tmp_in.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
            AudioSegment.from_file(tmp_in_path).export(tmp_wav.name, format="wav")
            tmp_wav_path = tmp_wav.name

        text = ""
        try:
            uploaded = genai.upload_file(path=tmp_wav_path, mime_type="audio/wav")

            # Wait for the file to be ACTIVE
            def get_state_name(file_obj):
                try:
                    return file_obj.state.name if hasattr(file_obj.state, "name") else str(file_obj.state)
                except Exception:
                    return str(getattr(file_obj, "state", "UNKNOWN"))

            state_name = get_state_name(uploaded)
            start_wait = time.time()
            while state_name == "PROCESSING" and (time.time() - start_wait) < 30:
                time.sleep(1)
                uploaded = genai.get_file(uploaded.name)
                state_name = get_state_name(uploaded)

            if state_name != "ACTIVE":
                raise RuntimeError(f"File not ACTIVE (state={state_name})")

            # Try multiple models for transcription to avoid version 404s
            text = _gemini_generate_with_file(["Transcribe this audio.", uploaded], timeout_s=90) or ""
        except Exception as gen_exc:
            logger.exception("Gemini transcription error: %s", gen_exc)
        finally:
            # Best-effort cleanup of uploaded file on Gemini
            try:
                if uploaded and getattr(uploaded, "name", None):
                    genai.delete_file(uploaded.name)
            except Exception:
                pass

        if not text and sr is not None:
            try:
                r = sr.Recognizer()
                with sr.AudioFile(tmp_wav_path) as source:
                    audio_data = r.record(source)
                text = r.recognize_google(audio_data)
                logger.info("Local fallback transcription succeeded.")
            except Exception as local_exc:
                logger.warning("Local fallback transcription failed: %s", local_exc)

        if text:
            return jsonify({"text": text})
        else:
            return jsonify({"error": "Transcription failed or returned empty text."}), 500

    except Exception as e:
        logger.exception("Transcription failed: %s", e)
        return jsonify({"error": "Failed to transcribe audio"}), 500

    finally:
        # Cleanup local temp files
        if tmp_in_path and os.path.exists(tmp_in_path):
            os.unlink(tmp_in_path)
        if tmp_wav_path and os.path.exists(tmp_wav_path):
            os.unlink(tmp_wav_path)

# Send OTP
@app.route("/send-otp", methods=["POST"])
def send_otp():
    if otps is None:
        return jsonify({"success": False, "error": "Database not configured"}), 500
    data = request.json or {}
    phone = data.get("phone")
    if not phone:
        return jsonify({"success": False, "error": "Phone number required"}), 400
    otp = str(random.randint(100000, 999999))
    otps.update_one({"phone": phone}, {"$set": {"otp": otp}}, upsert=True)
    app.logger.info(f"OTP for {phone}: {otp}")
    return jsonify({"success": True, "message": "OTP sent", "otp": otp})

# Verify OTP
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    if otps is None or users is None:
        return jsonify({"success": False, "error": "Database not configured"}), 500
    data = request.json or {}
    phone, otp = data.get("phone"), data.get("otp")
    if not phone or not otp:
        return jsonify({"success": False, "error": "Phone and OTP required"}), 400
    otp_doc = otps.find_one({"phone": phone})
    if not otp_doc or otp_doc.get("otp") != otp:
        return jsonify({"success": False, "error": "Invalid OTP"}), 400
    user = users.find_one({"phone": phone}, {"_id": 0})
    otps.delete_one({"phone": phone})
    return jsonify({
        "success": True,
        "message": "OTP verified ✅",
        "existing_user": bool(user),
        "user": user
    })

# Register user
@app.route("/register-details", methods=["POST"])
def register_details():
    data = request.json or {}
    phone = data.get("phone")
    if not phone:
        return jsonify({"error": "phone required"}), 400

    crops = []
    for c in data.get("crops", []):
        crop = {
            "name": c.get("name"),
            "soil": c.get("soil"),
            "landArea": c.get("landArea"),
            "farmLocation": c.get("farmLocation"),
        }
        crops.append(crop)

    if users is not None:
        users.update_one(
            {"phone": phone},
            {
                "$set": {
                    "name": data.get("name"),
                    "email": data.get("email"),
                    "state": data.get("state"),
                    "address": data.get("address"),
                    "district": data.get("district"),
                    "pin": data.get("pin"),
                    "crops": crops,
                }
            },
            upsert=True,
        )
    return jsonify({"message": "User details saved successfully"}), 200

# Get user by phone
@app.route("/get-user", methods=["GET"])
def get_user():
    phone = request.args.get("phone")
    if not phone or users is None:
        return jsonify({"name": "Guest"})
    user = users.find_one({"phone": phone}, {"_id": 0})
    if user:
        return jsonify(user)
    return jsonify({"name": "Guest"})

# Save/update location for user
@app.route("/update-location", methods=["POST"])
def update_location():
    if users is None:
        return jsonify({"error": "Database not configured"}), 500
    data = request.json or {}
    phone = data.get("phone")
    lat = data.get("lat")
    lon = data.get("lon")
    city = data.get("city")

    if not phone or lat is None or lon is None or not city:
        return jsonify({"error": "phone, lat, lon, city required"}), 400

    users.update_one(
        {"phone": phone},
        {"$set": {"current_location": {"lat": lat, "lon": lon, "city": city}}},
        upsert=True,
    )
    return jsonify({"message": "Location updated ✅", "city": city})

# Weather using WeatherAPI.com
@app.route("/weather", methods=["GET"])
def weather():
    phone = request.args.get("phone")
    try:
        user = users.find_one({"phone": phone}, {"_id": 0}) if users is not None and phone else None
        if user and "current_location" in user and WEATHER_API:
            lat = user["current_location"]["lat"]
            lon = user["current_location"]["lon"]
            url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API}&q={lat},{lon}"
            res = requests.get(url, timeout=10)
            data = res.json()
            return jsonify({
                "temp": f"{data['current']['temp_c']}°C",
                "humidity": f"{data['current']['humidity']}%",
                "wind": f"{data['current']['wind_kph']} km/h",
                "desc": data['current']['condition']['text'],
                "city": data['location']['name']
            })
    except Exception as e:
        logger.warning("Weather API error: %s", e)

    # Default fallback if user or API fails
    return jsonify({
        "temp": "31°C",
        "humidity": "75%",
        "wind": "12 km/h",
        "desc": "Partly Cloudy",
        "city": "Ludhiana"
    })

# DUMMY total revenue API
@app.route("/market-revenue", methods=["GET"])
def market_revenue():
    return jsonify({"total": "₹1,24,500"})

# Buyer Requests API — fetch listings
@app.route("/buyer-requests", methods=["GET"])
def buyer_requests():
    if listings_col is None:
        # If DB not available, return in-memory dummy data
        dummy_data = [
            {
                "id": "req1",
                "crop": "Maize",
                "buyer": "Asha Agri Traders",
                "qty": 500,
                "unit": "kg",
                "price": 2200,
                "image": "https://source.unsplash.com/480x320/?maize,corn",
                "location": "Ludhiana, PB",
                "postedAt": datetime.now().isoformat()
            },
            {
                "id": "req2",
                "crop": "Wheat",
                "buyer": "Punjab Buyers Co.",
                "qty": 1000,
                "unit": "kg",
                "price": 2100,
                "image": "https://source.unsplash.com/480x320/?wheat,field",
                "location": "Amritsar, PB",
                "postedAt": datetime.now().isoformat()
            },
            {
                "id": "req3",
                "crop": "Rice (Basmati)",
                "buyer": "Rao Traders",
                "qty": 200,
                "unit": "kg",
                "price": 3000,
                "image": "https://source.unsplash.com/480x320/?rice,field",
                "location": "Fazilka, PB",
                "postedAt": datetime.now().isoformat()
            },
        ]
        return jsonify({"requests": dummy_data})

    # Seed dummy data if collection is empty
    if listings_col.count_documents({}) == 0:
        dummy_data = [
            {
                "id": "req1",
                "crop": "Maize",
                "buyer": "Asha Agri Traders",
                "qty": 500,
                "unit": "kg",
                "price": 2200,
                "image": "https://source.unsplash.com/480x320/?maize,corn",
                "location": "Ludhiana, PB",
                "postedAt": datetime.now().isoformat()
            },
            {
                "id": "req2",
                "crop": "Wheat",
                "buyer": "Punjab Buyers Co.",
                "qty": 1000,
                "unit": "kg",
                "price": 2100,
                "image": "https://source.unsplash.com/480x320/?wheat,field",
                "location": "Amritsar, PB",
                "postedAt": datetime.now().isoformat()
            },
            {
                "id": "req3",
                "crop": "Rice (Basmati)",
                "buyer": "Rao Traders",
                "qty": 200,
                "unit": "kg",
                "price": 3000,
                "image": "https://source.unsplash.com/480x320/?rice,field",
                "location": "Fazilka, PB",
                "postedAt": datetime.now().isoformat()
            },
        ]
        listings_col.insert_many(dummy_data)

    listings = list(listings_col.find({}, {"_id": 0}))
    return jsonify({"requests": listings})

# Post a new buyer listing
@app.route("/post-listing", methods=["POST"])
def post_listing():
    if listings_col is None:
        return jsonify({"error": "Database not configured"}), 500
    data = request.json or {}
    data["id"] = f"req{random.randint(1000,9999)}"
    data["postedAt"] = datetime.now().isoformat()
    listings_col.insert_one(data)
    return jsonify({"message": "Listing created successfully", "listing": data})

# Mark interest in listing
@app.route("/interest", methods=["POST"])
def mark_interest():
    if listings_col is None:
        return jsonify({"error": "Database not configured"}), 500
    listing_id = (request.json or {}).get("listingId")
    phone = (request.json or {}).get("phone")
    if not listing_id or not phone:
        return jsonify({"error": "listingId and phone required"}), 400
    listings_col.update_one({"id": listing_id}, {"$addToSet": {"interested": phone}})
    return jsonify({"message": "Interest recorded ✅"})

# Other small routes
@app.route("/news", methods=["GET"])
def news():
    return jsonify({"headline": "Monsoon expected to arrive on schedule across Punjab this year."})

@app.route("/schemes", methods=["GET"])
def schemes():
    return jsonify({"schemes": [
        {"title": "PM-KISAN", "desc": "Income support for farmers"},
        {"title": "Soil Health Card", "desc": "Check soil quality"}
    ]})

@app.route("/fertilizers", methods=["GET"])
def fertilizers():
    return jsonify({"items": [
        {"name": "Urea", "price": "₹300/bag"},
        {"name": "DAP", "price": "₹1200/bag"}
    ]})

# -------------------------------
# Entrypoint (Render will set PORT)
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    logger.info(f"Starting Flask app on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)