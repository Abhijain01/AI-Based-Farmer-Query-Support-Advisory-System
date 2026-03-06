import React, { useEffect, useState } from "react";
import "../styles/homeview.css";

const HomeView = () => {
  const [user, setUser] = useState(null);
  const [weather, setWeather] = useState(null);
  const [news, setNews] = useState({});

  useEffect(() => {
    const phone = localStorage.getItem("phone");

    // ✅ Fetch user
    fetch(`http://127.0.0.1:5000/get-user?phone=${phone}`)
      .then((r) => r.json())
      .then(setUser)
      .catch(() => setUser({ name: "Farmer" }));

    // ✅ Fetch news
    fetch("http://127.0.0.1:5000/news")
      .then((r) => r.json())
      .then(setNews)
      .catch(() => setNews({ headline: "Latest updates for farmers" }));

    // ✅ Get location + weather
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          const { latitude, longitude } = pos.coords;
          try {
            await fetch("http://127.0.0.1:5000/update-location", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ phone, lat: latitude, lon: longitude }),
            });

            const res = await fetch(`http://127.0.0.1:5000/weather?phone=${phone}`);
            const data = await res.json();
            setWeather({
              temp: data.temp,
              humidity: data.humidity,
              wind: data.wind,
              desc: data.desc,
              city: data.city,
            });
          } catch {
            setWeather({
              temp: "28°C",
              humidity: "65%",
              wind: "10 km/h",
              desc: "Partly Cloudy",
              city: "Unknown",
            });
          }
        },
        () => {
          setWeather({
            temp: "28°C",
            humidity: "65%",
            wind: "10 km/h",
            desc: "Partly Cloudy",
            city: "Unknown",
          });
        }
      );
    }
  }, []);

  return (
    <div className="home-grid">
      {/* ✅ Welcome & Weather */}
      <div className="welcome-card">
        <div className="welcome-left">
          <h3>Welcome, {user?.name || "Farmer"}</h3>
          <p className="date">
            {new Date().toLocaleDateString("en-US", {
              weekday: "long",
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
          {weather && (
            <p className="date">
              {weather.desc}, {weather.temp} ({weather.city})
            </p>
          )}
        </div>

        {weather && (
          <div className="welcome-weather">
            <div className="details">
              <b>
                {weather.desc}, {weather.temp}
              </b>
              <p>📍 Location: {weather.city}</p>
              <p>💧 Humidity: {weather.humidity}</p>
              <p>🌬 Wind: {weather.wind}</p>
            </div>
          </div>
        )}
      </div>

      {/* ✅ Bigger cards with more info */}
      <div className="cards">
        <button className="card">
          📰 <h4>News & Updates</h4>
          <p>{news.headline || "Top crop news & trends"}</p>
          <ul>
            <li>🌦 Weather-related farming tips</li>
            <li>📈 Crop price changes and alerts</li>
            <li>🌿 New government policy updates</li>
          </ul>
        </button>

        <button className="card">
          📉 <h4>Market Rate</h4>
          <p>Check live mandi prices for key crops:</p>
          <ul>
            <li>🌾 Wheat: ₹2,150/quintal</li>
            <li>🌽 Maize: ₹1,800/quintal</li>
            <li>🥔 Potatoes: ₹1,200/quintal</li>
          </ul>
        </button>

        <button className="card">
          ☁️ <h4>7-Day Forecast</h4>
          <p>Plan your irrigation & pesticide use wisely:</p>
          <ul>
            <li>🌦 Partly Cloudy (Mon–Tue)</li>
            <li>🌧 Light Rain (Wed–Thu)</li>
            <li>☀️ Sunny (Fri–Sun)</li>
          </ul>
        </button>

        <button className="card">
          🦠 <h4>Crop Disease Alerts</h4>
          <p>Latest alerts from your region:</p>
          <ul>
            <li>🌱 Rice blast in nearby districts</li>
            <li>🪲 Aphid attack on mustard crops</li>
            <li>🍅 Fungal rust on tomato plants</li>
          </ul>
        </button>

        <button className="card">
          🏛 <h4>Govt Schemes</h4>
          <p>Available financial support & programs:</p>
          <ul>
            <li>💸 PM-Kisan Direct Benefit Scheme</li>
            <li>🚜 Subsidy on agri-equipment</li>
            <li>💧 Water conservation projects</li>
          </ul>
        </button>

        <button className="card">
          🛒 <h4>Buyers & Trade Leads</h4>
          <p>Connect directly with verified buyers:</p>
          <ul>
            <li>🏢 AgriExport Pvt. Ltd.</li>
            <li>🌾 Punjab Farmers Co-op</li>
            <li>🍀 Local food processing units</li>
          </ul>
        </button>
      </div>
    </div>
  );
};

export default HomeView;