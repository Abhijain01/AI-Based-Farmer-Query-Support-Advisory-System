import React, { useState } from "react";
import "../styles/prediction.css";

const Prediction = () => {
  const [chatMessages, setChatMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // ✅ News & Research Items
  const researchItems = [
    {
      title: "📰 Pest Alert",
      desc: "Locusts detected in nearby districts. Farmers advised to take preventive measures.",
      link: "https://www.fao.org/agriculture/locusts/en/" // example link
    },
    {
      title: "🔬 Latest Research",
      desc: "Scientists discovered a new resistant variety of wheat that reduces fungal infections.",
      link: "https://www.sciencedirect.com/journal/crop-protection"
    },
    {
      title: "🌾 Crop Tip",
      desc: "Regular soil testing can help reduce crop diseases by 25%.",
      link: "https://icar.org.in/" // example ICAR research link
    },
  ];

  // ✅ Send text query
  const sendMessage = async () => {
    if (!input.trim()) return;
    const newMsg = { sender: "user", text: input };
    setChatMessages((prev) => [...prev, newMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: input }),
      });
      const data = await res.json();
      setChatMessages((prev) => [...prev, { sender: "bot", text: data.answer }]);
    } catch (err) {
      setChatMessages((prev) => [...prev, { sender: "bot", text: "❌ Error connecting to server" }]);
    }
    setLoading(false);
  };

  // ✅ Image upload query
  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setChatMessages((prev) => [
      ...prev,
      { sender: "user", text: `📷 Uploaded: ${file.name}` },
    ]);
    setLoading(true);

    const formData = new FormData();
    formData.append("image", file);

    try {
      const res = await fetch("http://127.0.0.1:5000/chat-image", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setChatMessages((prev) => [
        ...prev,
        { sender: "bot", text: data.answer || "✅ Image analyzed successfully!" },
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { sender: "bot", text: "❌ Error analyzing image" },
      ]);
    }
    setLoading(false);
  };


  return (
    <div className="prediction-page">
      <h2>🌱 Crop Prediction</h2>

      {/* ✅ Research/News Cards */}
      <div className="research-cards">
        {researchItems.map((item, i) => (
          <div
            key={i}
            className="research-card"
            onClick={() => window.open(item.link, "_blank")}
          >
            <h4>{item.title}</h4>
            <p>{item.desc}</p>
          </div>
        ))}
      </div>

      {/* ✅ Chat Section */}
      <div className="chat-section">
        <h3>🤖 Smart Crop Assistant</h3>
        <div className="chat-box">
          {chatMessages.map((msg, i) => (
            <div
              key={i}
              className={`chat-message ${msg.sender === "user" ? "user" : "bot"}`}
            >
              {msg.text}
            </div>
          ))}
          {loading && <p className="loading">⏳ Bot is thinking...</p>}
        </div>

        <div className="chat-controls">
          
          <label className="upload-btn">
            📷 Upload
            <input type="file" hidden onChange={handleImageUpload} />
          </label>
        </div>
      </div>
    </div>
  );
};

export default Prediction;
