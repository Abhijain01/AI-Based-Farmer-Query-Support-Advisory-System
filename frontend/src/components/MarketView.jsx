import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import "../styles/market.css";

const MarketView = () => {
  const [crops, setCrops] = useState([]);
  const [marketNews, setMarketNews] = useState([]);

  useEffect(() => {
    const phone = localStorage.getItem("phone");

    // ✅ Fetch crops registered by user
    fetch(`http://127.0.0.1:5000/get-crops?phone=${phone}`)
      .then((res) => res.json())
      .then((data) => setCrops(data.crops || []))
      .catch(() =>
        setCrops([
          { id: 1, name: "Wheat" },
          { id: 2, name: "Rice" },
        ])
      );

    // ✅ Fetch market news
    fetch("http://127.0.0.1:5000/market")
      .then((res) => res.json())
      .then((data) => {
        if (data.rates) {
          setMarketNews([
            {
              title: "📈 Wheat prices rise 5%",
              desc: "Increased demand in northern regions boosts wheat market.",
            },
            {
              title: "📉 Rice holds steady",
              desc: "Government procurement ensures stable rice pricing.",
            },
            {
              title: "🌾 Maize export surges",
              desc: "Strong overseas demand pushes maize prices upward.",
            },
            {
              title: "💹 Pulses see mild dip",
              desc: "Higher yield this season slightly lowers pulses prices.",
            },
          ]);
        }
      });
  }, []);

  // ✅ Generate mock price data for 7 days
  const generatePriceData = (basePrice) => {
    return Array.from({ length: 7 }, (_, i) => ({
      day: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][i],
      price: basePrice + Math.floor(Math.random() * 100 - 50),
    }));
  };

  return (
    <div className="market-container">
      <h2 className="page-title">🌾 Market Updates</h2>

      {/* ✅ Market News Section */}
      <div className="news-section">
        <h3 className="section-subtitle">📰 Latest Market News</h3>
        <div className="news-grid">
          {marketNews.map((news, i) => (
            <div key={i} className="news-card">
              <h4>{news.title}</h4>
              <p>{news.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ✅ Crop Price Charts */}
      <h2 className="section-title">📊 Weekly Price Trends</h2>
      <div className="crop-grid">
        {crops.map((crop, index) => {
          const priceData = generatePriceData(2000 + index * 300);
          return (
            <div key={index} className="crop-card">
              <h3>{crop.name}</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={priceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="price" stroke="#3b82f6" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MarketView;
