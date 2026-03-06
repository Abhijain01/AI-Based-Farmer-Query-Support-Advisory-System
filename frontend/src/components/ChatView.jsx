import React, { useState, useRef } from "react";
import { FaMicrophone, FaPlus } from "react-icons/fa";
import { MdSend } from "react-icons/md";
import "../styles/chatview.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000";

const ChatView = () => {
  const [messages, setMessages] = useState([
    { from: "bot", text: "Hello! Ask me anything about crops." }
  ]);
  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [attachedFile, setAttachedFile] = useState(null); // New: Staging state
  const fileRef = useRef();

  // Helper to parse JSON safely
  const parseJsonSafe = async (res) => {
    const raw = await res.text();
    try {
      return JSON.parse(raw);
    } catch {
      throw new Error(`HTTP ${res.status} ${res.statusText}: ${raw.slice(0, 200)}`);
    }
  };

  // ---- Send Logic (Decides between Text or Image+Text) ----
  const handleSend = async () => {
    if (attachedFile) {
      await uploadImageWithQuestion(attachedFile, text);
      setAttachedFile(null); // Clear after sending
      setText("");
    } else {
      await sendText();
    }
  };

  // ---- Send Text (connects to /ask) ----
  const sendText = async () => {
    if (!text.trim()) return;

    // show user message instantly
    const msg = text;
    setMessages((m) => [...m, { from: "user", text: msg }]);
    setText("");

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: msg }) // backend expects "question" or "q"
      });

      const data = await parseJsonSafe(res);
      if (!res.ok) {
        setMessages((m) => [...m, { from: "bot", text: `⚠️ ${data.error || "Server error"}` }]);
        return;
      }

      // Show bot answer
      setMessages((m) => [...m, { from: "bot", text: data.answer || "(no answer)" }]);

      // Optional: if server returns audio_base64, add an audio message
      if (data.audio_base64) {
        const audioUrl = `data:audio/mpeg;base64,${data.audio_base64}`;
        setMessages((m) => [...m, { from: "bot", audioUrl }]);
      }
    } catch (err) {
      console.error("Backend error:", err);
      setMessages((m) => [...m, { from: "bot", text: "⚠️ Error connecting to server" }]);
    }
  };

  // ---- Send File + Optional Text (connected to backend /chat-image) ----
  const uploadImageWithQuestion = async (file, questionText) => {
    const url = URL.createObjectURL(file);

    // show user message with image and text
    setMessages((m) => [
      ...m,
      {
        from: "user",
        fileUrl: url,
        fileName: file.name,
        text: questionText // Show text alongside image if provided
      }
    ]);

    try {
      const formData = new FormData();
      formData.append("image", file);
      if (questionText) {
        formData.append("question", questionText);
      }

      const res = await fetch(`${API_BASE}/chat-image`, {
        method: "POST",
        body: formData
      });

      const data = await parseJsonSafe(res);
      if (!res.ok) {
        setMessages((m) => [...m, { from: "bot", text: `⚠️ ${data.error || "Image analyze failed"}` }]);
        return;
      }

      setMessages((m) => [...m, { from: "bot", text: data.answer || "(no result)" }]);
    } catch (err) {
      console.error("Image upload error:", err);
      setMessages((m) => [...m, { from: "bot", text: "⚠️ Error uploading image" }]);
    }
  };

  // ---- Upload audio to backend /transcribe (optional) ----
  const uploadAudio = async (audioBlob) => {
    try {
      const fd = new FormData();
      fd.append("audio", audioBlob, "recording.webm");

      const res = await fetch(`${API_BASE}/transcribe`, {
        method: "POST",
        body: fd
      });

      const data = await parseJsonSafe(res);
      if (!res.ok) {
        setMessages((m) => [...m, { from: "bot", text: `⚠️ ${data.error || "Transcription failed"}` }]);
        return;
      }

      // Show transcript as a user message, then auto-ask
      const transcript = data.text || "(empty transcript)";
      setMessages((m) => [...m, { from: "user", text: transcript }]);

      // Automatically send the transcript to /ask
      const askRes = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: transcript })
      });
      const askData = await parseJsonSafe(askRes);
      if (!askRes.ok) {
        setMessages((m) => [...m, { from: "bot", text: `⚠️ ${askData.error || "Ask failed"}` }]);
        return;
      }
      setMessages((m) => [...m, { from: "bot", text: askData.answer || "(no answer)" }]);

      if (askData.audio_base64) {
        const audioUrl = `data:audio/mpeg;base64,${askData.audio_base64}`;
        setMessages((m) => [...m, { from: "bot", audioUrl }]);
      }
    } catch (err) {
      console.error("Transcribe error:", err);
      setMessages((m) => [...m, { from: "bot", text: "⚠️ Error connecting to server (transcribe)" }]);
    }
  };

  // ---- Voice Recording ----
  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      let chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(chunks, { type: "audio/webm" });
        const audioUrl = URL.createObjectURL(audioBlob);
        setMessages((m) => [...m, { from: "user", audioUrl }]);
        chunks = [];

        // Send to backend for transcription + Q&A
        uploadAudio(audioBlob);
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (err) {
      console.error("Mic access denied:", err);
      setMessages((m) => [...m, { from: "bot", text: "⚠️ Please allow microphone access" }]);
    }
  };

  return (
    <div className="chat-view">
      <div className="chat-messages">
        {messages.map((m, i) => (
          <div className={`msg ${m.from}`} key={i}>
            {m.text && <div className="bubble">{m.text}</div>}

            {m.fileUrl && (
              <div className="bubble file-bubble">
                📎 <a href={m.fileUrl} download={m.fileName}>{m.fileName}</a>
              </div>
            )}

            {m.audioUrl && (
              <audio controls src={m.audioUrl} className="audio-player"></audio>
            )}
          </div>
        ))}
      </div>

      {/* Input Bar */}
      <div className="chat-input-container">
        <div className="chat-input">
          <input
            type="file"
            ref={fileRef}
            style={{ display: "none" }}
            accept="image/*"
            onChange={(e) => {
              if (e.target.files[0]) {
                setAttachedFile(e.target.files[0]); // Stage the file
              }
            }}
          />

          <div className="input-box-wrapper">
            {/* Preview Staged File (Inside Input Box Now) */}
            {attachedFile && (
              <div className="file-preview-container">
                <div className="file-preview">
                    {attachedFile.type.startsWith("image/") ? (
                        <img 
                            src={URL.createObjectURL(attachedFile)} 
                            alt="preview" 
                            className="image-preview" 
                        />
                    ) : (
                        <span className="file-name-preview">📎 {attachedFile.name}</span>
                    )}
                    <button onClick={() => setAttachedFile(null)} className="remove-file-btn" title="Remove attachment">
                        ×
                    </button>
                </div>
              </div>
            )}
            
            <div className="input-box">
              {/* File Upload */}
              <button
                className="icon-btn"
                onClick={() => fileRef.current.click()}
                title="Attach image"
              >
                <FaPlus size={18} />
              </button>

              {/* Text Input */}
              <input
                className="text-input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder={attachedFile ? "Ask a question about this image..." : "Type a message..."}
              />

              {/* Mic Recording */}
              <button
                className={`icon-btn mic-btn ${isRecording ? "recording" : ""}`}
                onClick={toggleRecording}
                title="Record voice"
              >
                <FaMicrophone size={18} />
              </button>

              {/* Send Button */}
              <button className="icon-btn send-btn" onClick={handleSend} title="Send">
                <MdSend size={20} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatView;