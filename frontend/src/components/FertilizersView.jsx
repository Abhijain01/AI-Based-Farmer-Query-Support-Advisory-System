import React, { useState } from "react";
import "../styles/FertilizerView.css";

export default function FertilizerPage() {
  const [fertilizer, setFertilizer] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState(null);

  const [formData, setFormData] = useState({
    N: "",
    P: "",
    K: "",
    moisture: "",
    temperature: "",
    humidity: "",
    soil: "",
    crop: "",
  });

  const [recommendation, setRecommendation] = useState("");
  const [loading, setLoading] = useState(false);

  // ✅ Price checker handler
  const handlePriceCheck = (e) => {
    e.preventDefault();
    const basePrice = 25; // ₹ per kg (demo)
    const totalPrice = quantity ? basePrice * parseInt(quantity) : 0;
    setPrice(`Estimated Price: ₹${totalPrice}`);
  };

  // ✅ Handle input change
  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // ✅ Send recommendation data to backend
  const handleRecommendation = async (e) => {
    e.preventDefault();
    setLoading(true);
    setRecommendation("");

    try {
      const res = await fetch("http://127.0.0.1:5000/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const data = await res.json();
      setRecommendation(data.recommendation || data.error || "No recommendation found.");
    } catch (err) {
      setRecommendation("⚠️ Failed to connect to the backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-10 bg-gradient-to-b from-green-50 to-white min-h-screen">
      {/* ✅ Latest Fertilizer News as Cards */}
      <section className="news-section">
        <h2 className="section-title">🌱 Latest Fertilizer News</h2>
        <div className="news-grid">
          {[
            {
              title: "Govt. Subsidy Increased for Urea",
              img: "https://source.unsplash.com/400x250/?fertilizer,urea",
              desc: "The government has announced a 15% subsidy boost to support farmers using urea fertilizers.",
            },
            {
              title: "New Organic Fertilizer Launch",
              img: "https://source.unsplash.com/400x250/?organic,fertilizer",
              desc: "A new eco-friendly organic fertilizer has been launched, improving soil health by 30%.",
            },
            {
              title: "Fertilizer Export Prices Drop",
              img: "https://source.unsplash.com/400x250/?farm,soil",
              desc: "Global fertilizer prices have dropped, reducing costs for local suppliers and farmers.",
            },
          ].map((news, i) => (
            <div key={i} className="news-card">
              <div className="news-image">
                <img src={news.img} alt={news.title} />
              </div>
              <div className="news-content">
                <h3>{news.title}</h3>
                <p>{news.desc}</p>
                <a href="#" className="news-link">Read More →</a>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 🔍 Fertilizer Price Checker */}
      <section className="bg-white p-6 rounded-xl shadow space-y-4">
        <h2 className="text-2xl font-bold">🔍 Fertilizer Price Checker</h2>
        <form onSubmit={handlePriceCheck} className="grid md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Enter Fertilizer Name"
            value={fertilizer}
            onChange={(e) => setFertilizer(e.target.value)}
            className="border p-3 rounded-lg w-full"
          />
          <input
            type="number"
            placeholder="Enter Quantity (kg)"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="border p-3 rounded-lg w-full"
          />
          <button
            type="submit"
            className="col-span-2 bg-green-600 hover:bg-green-700 text-white p-3 rounded-lg transition"
          >
            Check Price
          </button>
        </form>
        {price && (
          <p className="text-lg font-semibold text-green-700 mt-2">{price}</p>
        )}
      </section>

      <hr />

      {/* 🌿 Smart Fertilizer Recommendation (Connected to Backend) */}
      <section className="bg-white p-8 rounded-xl shadow space-y-4">
        <h2 className="text-2xl font-bold">🌿 Fertilizer Recommendation</h2>
        <p className="text-gray-600">
          Enter soil and crop details to get a smart fertilizer suggestion 👨‍🌾
        </p>

        <form onSubmit={handleRecommendation} className="space-y-6">
          {/* NPK Inputs */}
          <div className="grid md:grid-cols-3 gap-4">
            <input
              type="number"
              name="N"
              placeholder="Nitrogen (N)"
              value={formData.N}
              onChange={handleChange}
              className="border p-3 rounded-lg w-full"
              required
            />
            <input
              type="number"
              name="P"
              placeholder="Phosphorus (P)"
              value={formData.P}
              onChange={handleChange}
              className="border p-3 rounded-lg w-full"
              required
            />
            <input
              type="number"
              name="K"
              placeholder="Potassium (K)"
              value={formData.K}
              onChange={handleChange}
              className="border p-3 rounded-lg w-full"
              required
            />
          </div>

          {/* Weather Inputs */}
          <div className="grid md:grid-cols-3 gap-4">
            <input
              type="number"
              name="moisture"
              placeholder="Moisture (%)"
              value={formData.moisture}
              onChange={handleChange}
              className="border p-3 rounded-lg w-full"
            />
            <input
              type="number"
              name="temperature"
              placeholder="Temperature (°C)"
              value={formData.temperature}
              onChange={handleChange}
              className="border p-3 rounded-lg w-full"
            />
            <input
              type="number"
              name="humidity"
              placeholder="Humidity (%)"
              value={formData.humidity}
              onChange={handleChange}
              className="border p-3 rounded-lg w-full"
            />
          </div>

          {/* Soil & Crop */}
          <div className="grid md:grid-cols-2 gap-4">
            <select
              name="soil"
              value={formData.soil}
              onChange={handleChange}
              className="border p-3 rounded-lg w-full"
              required
            >
              <option value="">-- Select Soil Type --</option>
              <option value="Sandy">Sandy</option>
              <option value="Clay">Clay</option>
              <option value="Loamy">Loamy</option>
              <option value="Black">Black</option>
              <option value="Red">Red</option>
            </select>

            <input
              type="text"
              name="crop"
              placeholder="Crop Name"
              value={formData.crop}
              onChange={handleChange}
              className="border p-3 rounded-lg w-full"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg transition text-lg"
          >
            {loading ? "🔄 Getting Recommendation..." : "🌿 Get Recommendation"}
          </button>
        </form>

        {/* 📊 Result Box */}
        {recommendation && (
          <div className="mt-6 bg-blue-50 border border-blue-300 rounded-lg p-4 text-center shadow-sm">
            <h3 className="text-lg font-semibold text-blue-800">✅ Recommendation:</h3>
            <p className="text-blue-700 mt-2">{recommendation}</p>
          </div>
        )}
      </section>
    </div>
  );
}
