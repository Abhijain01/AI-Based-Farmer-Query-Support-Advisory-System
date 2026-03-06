# KissanMitra: AI-Powered Agricultural Assistance Platform

KissanMitra is a comprehensive Full-Stack web application designed to empower farmers with real-time, data-backed agricultural insights. The platform bridges the gap between complex agricultural science and accessible farming solutions by offering multi-modal interactions (text, voice, and image). It provides AI-based crop disease diagnosis, intelligent fertilizer recommendations, local market pricing, an interactive marketplace, and an intelligent voice-enabled chatbot.

---

## 🎯 Key Features & Technical Capabilities

### 1. Multi-Modal Crop Disease Diagnosis
*   **Computer Vision:** Users can upload images of diseased crops. The backend processes the image using a custom-trained Convolutional Neural Network (CNN) to mathematically predict the specific disease.
*   **GenAI Enhancement:** The predicted class and image are forwarded to the **Google Gemini Pro Vision API**. Gemini acts as an expert system, confirming the diagnosis and generating a concise, practical remedy in natural language.
*   **Fallback Mechanism:** If the external API fails, the system relies on a locally hosted FAISS index to retrieve pre-embedded remedies for the predicted disease.

### 2. Predictive Analytics for Fertilizer Recommendation
*   **Machine Learning:** Developed a predictive pipeline using Scikit-Learn. The system takes live environmental parameters (Temperature, Moisture, Humidity) and soil composition data (Nitrogen, Phosphorus, Potassium levels, Soil Type, and Crop Type).
*   **Inference:** Using pre-trained label encoders, the normalized data is fed into an ensemble ML model to instantly recommend the optimal fertilizer, reducing soil degradation and improving crop yield.

### 3. Voice-Enabled Intelligent Assistant (RAG Architecture)
*   **Voice/Text Chat:** Built an accessibility-first chat interface using the Web Audio API allowing users to record their voice or type queries. The backend transcribes audio using SpeechRecognition and converts responses back to audio via Google Text-to-Speech (gTTS).
*   **Vector Search & RAG:** To prevent LLM hallucinations on regional farming questions, the backend queries a local **FAISS vector database** populated with dense embeddings from HuggingFace SentenceTransformers. It retrieves accurate, verified local farming context before prompting the Gemini LLM.

### 4. Interactive Marketplace & Real-Time Data Aggregation
*   **Marketplace:** A community feature allowing users to browse and post agricultural trade requests, backed by NoSQL document structures.
*   **Live Aggregation:** The backend actively pings OpenStreetMap Nominatim and Weather APIs to reverse-geocode the user's location and pull in live environmental data to inform the ML models.

### 5. Secure Access & Fault-Tolerant Architecture
*   **Authentication:** Custom phone-based OTP (One Time Password) authentication flow interacting with MongoDB.
*   **Mock DB Fallback:** To ensure high availability, the server is engineered with an in-memory `MockCollection` backup that automatically kicks in if the MongoDB connection drops.
*   **Memory Optimization:** Massive `.pkl` and `.h5` model files are loaded via `joblib`'s memory-mapping (`mmap_mode='r'`) to prevent server Out-of-Memory (OOM) crashes during concurrent API requests.

---

## 🏗️ Project Structure

This project is divided into two main components:
*   `frontend/`: The React Single Page Application (built with Vite).
*   `backend/`: The Python Flask REST API server and AI data pipelines.

**⚠️ Important Note Regarding ML Models:** Large machine learning models (`.h5`, `.pkl`) and massive vector databases (`.jsonl`) are ignored from this repository due to GitHub file size limits. You must provide these core ML models locally in the `backend/` directory for full prediction functionality to work.

---

## 🚀 How to Run the Application Locally (Windows)

To run the full application, you need to open **two separate terminal windows**—one for the backend and one for the frontend.

### 1. Starting the Backend Server (Flask API)

The backend handles the AI models, API routes, and database connections. You must activate the Python virtual environment before running it.

1. Open your first terminal and navigate to the backend folder:
   ```powershell
   cd backend
   ```
2. Activate the Python virtual environment:
   * **For PowerShell:** `.\venv\Scripts\Activate.ps1`
   * **For Command Prompt (CMD):** `.\venv\Scripts\activate.bat`
   *(You should see `(venv)` appear in your terminal prompt)*
3. Install dependencies (if you haven't already):
   ```powershell
   pip install -r requirements.txt
   ```
4. Start the Flask server:
   ```powershell
   python app.py
   ```
   *(The server should start running at `http://127.0.0.1:5000`)*

### 2. Starting the Frontend Server (React + Vite)

The frontend handles the user interface and interacts with the backend APIs.

1. Open a **second, completely separate terminal** and navigate to the frontend folder:
   ```powershell
   cd frontend
   ```
2. Install the Node modules (if this is your first time):
   ```powershell
   npm install
   ```
3. Start the Vite development server:
   ```powershell
   npm run dev
   ```
4. Open your browser and navigate to the URL provided in the terminal (usually `http://localhost:5173` or `http://localhost:5174`).

---

## 🛠️ Technology Stack

*   **Frontend Ecosystem:** React.js, Vite, Vanilla CSS, React-Icons
*   **Backend Framework:** Python, Flask, Flask-CORS, RESTful APIs
*   **Machine Learning / Vision:** TensorFlow, Keras, Scikit-Learn, Google Gemini Pro Vision API
*   **Data Engineering / RAG:** FAISS (Vector Database), HuggingFace SentenceTransformers, Joblib, NumPy
*   **Database Management:** MongoDB, In-Memory Mock Structures
*   **Audio Processing:** Web Audio API, `gTTS` (Text-to-Speech), `SpeechRecognition`
*   **External Data APIs:** OpenStreetMap Geocoding API, WeatherAPI

