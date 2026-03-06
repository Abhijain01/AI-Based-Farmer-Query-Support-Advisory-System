# KissanMitra: AI-Powered Agricultural Assistance Platform

KissanMitra is a comprehensive Full-Stack web application designed to empower farmers with real-time agricultural insights. It features AI-based crop disease diagnosis, local market pricing, an intelligent marketplace, and a multi-modal voice/text chatbot that processes complex agricultural queries.

## Project Structure

This project is divided into two main components:
*   `frontend/`: The React application (built with Vite).
*   `backend/`: The Python Flask REST API server and AI models.

**Note:** Large machine learning models (`.h5`, `.pkl`) and massive vector databases (`.jsonl`) are ignored from this repository due to GitHub file size limits. You must provide these locally in the `backend/` directory for full prediction functionality.

---

## 🚀 How to Run the Application Locally (Windows)

To run the full application, you need to open **two separate terminal windows**—one for the backend and one for the frontend.

### 1. Starting the Backend Server (Flask)

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

## 🛠️ Tech Stack
*   **Frontend:** React, Vite, Vanilla CSS, React-Icons
*   **Backend:** Python, Flask, Flask-CORS
*   **AI/ML Integration:** Google Gemini Pro Vision, TensorFlow/Keras, FAISS, SentenceTransformers
*   **Audio Processing:** Web Audio API, gTTS, SpeechRecognition
*   **Database:** MongoDB

