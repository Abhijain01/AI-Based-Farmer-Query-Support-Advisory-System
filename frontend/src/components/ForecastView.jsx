import React, { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import "../styles/forecast.css";

const ForecastView = () => {
  const [weather, setWeather] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [crops, setCrops] = useState([]);

  useEffect(() => {
    const phone = localStorage.getItem("phone");

    // ✅ Fetch crops registered by user
    fetch(`http://127.0.0.1:5000/get-crops?phone=${phone}`)
      .then((res) => res.json())
      .then((data) => setCrops(data.crops || []))
      .catch(() => setCrops([{ id: 1, name: "Wheat" }, { id: 2, name: "Rice" }]));

    // ✅ Fetch today’s weather + 5-day forecast from WeatherAPI
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(async (pos) => {
        const { latitude, longitude } = pos.coords;
        try {
          const res = await fetch(
            `http://api.weatherapi.com/v1/forecast.json?key=6b8f15b41c80499c96c43953252409&q=${latitude},${longitude}&days=5&aqi=no&alerts=yes`
          );
          const data = await res.json();
          setWeather(data);

          if (data.alerts && data.alerts.alert && data.alerts.alert.length > 0) {
            setAlerts(data.alerts.alert[0]);
          }
        } catch (err) {
          console.error("Weather fetch failed:", err);
        }
      });
    }
  }, []);

  const next5Days = weather?.forecast?.forecastday?.map((d) => ({
    day: new Date(d.date).toLocaleDateString("en-US", { weekday: "short" }),
    temp: d.day.avgtemp_c,
  }));

  return (
    <div className="forecast-container">
      {/* ✅ Today’s Weather + Chart in same box */}
      {weather && (
        <div className="today-box">
          <div className="today-left">
            <h2>🌤 Today in {weather.location.name}</h2>
            <div className="today-weather">
              <img
                src={`https:${weather.current.condition.icon}`}
                alt="Weather Icon"
              />
              <div>
                <h3>{weather.current.condition.text}</h3>
                <p>Temperature: {weather.current.temp_c}°C</p>
                <p>Humidity: {weather.current.humidity}%</p>
                <p>Wind: {weather.current.wind_kph} km/h</p>
              </div>
            </div>
          </div>

          {/* ✅ Chart on the right side */}
          <div className="today-chart">
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={next5Days}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="temp" stroke="#ff7300" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ✅ Alerts */}
      {alerts && (
        <div className="alert-card">
          <h2>⚠️ Weather Alert</h2>
          <p><b>{alerts.headline}</b></p>
          <p>{alerts.desc}</p>
        </div>
      )}

      {/* ✅ Crop Forecasts stay below */}
      <h2 className="crop-section">🌱 Crop-wise 5-Day Forecast</h2>
      <div className="crop-grid">
        {crops.map((crop, index) => (
          <div key={index} className="crop-card">
            <h3>{crop.name || `Crop ${index + 1}`}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={next5Days}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="temp" stroke="#82ca9d" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ForecastView;
