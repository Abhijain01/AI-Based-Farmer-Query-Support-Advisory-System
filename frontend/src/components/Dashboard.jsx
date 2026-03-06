import React, { useEffect, useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";

// Shared layout components
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";

// Pages / Views
import HomeView from "../components/HomeView";
import ChatView from "../components/ChatView";
import PredictionView from "../components/PredictionView";
import ForecastView from "../components/ForecastView";
import MarketView from "../components/MarketView";
import SchemesView from "../components/SchemesView";
import TradeView from "../components/TradeView";
import FertilizersView from "../components/FertilizersView";
import HelpView from "../components/HelpView";

// Styles
import "../styles/dashboard.css";


const Dashboard = () => {
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    // fetch logged-in user data from backend
    fetch("http://127.0.0.1:5000/get-user", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => setUser(data))
      .catch(() => {
        // fallback mock user if backend isn't ready
        setUser({ name: "Rajesh Kumar", location: "Phagwara" });
      });
  }, []);

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-area">
        <Topbar user={user} />
        <div className="content-area">
          <Routes>
            <Route path="home" element={<HomeView user={user} />} />
            <Route path="queries" element={<ChatView />} />
            <Route path="prediction" element={<PredictionView />} />
            <Route path="forecast" element={<ForecastView/>} />
            <Route path="market" element={<MarketView />} />
            <Route path="schemes" element={<SchemesView />} />
            <Route path="trade" element={<TradeView />} />
            <Route path="fertilizers" element={<FertilizersView />} />
            <Route path="help" element={<HelpView />} />
            <Route path="*" element={<HomeView user={user} />} />
          </Routes>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
