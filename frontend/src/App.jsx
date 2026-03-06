import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import IndexPage from "./components/IndexPage";     // ✅ New: Welcome page
import LoginPage from "./components/LoginPage";
import OtpVerification from "./components/OtpVerification";
import RegisterPage from "./components/RegisterPage";
import RegisterDetails from "./components/RegisterDetails";
import Dashboard from "./components/Dashboard";
import Loader from "./components/Loader";           // ✅ Make sure this path is correct

import "./styles/global.css";

function App() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    console.log("⏳ Showing loader...");
    const timer = setTimeout(() => {
      console.log("✅ Hiding loader");
      setLoading(false);
    }, 4000); // loader visible for 4s
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return <Loader />; // ✅ shows your loader before app loads
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* ✅ New welcome landing page */}
        <Route path="/" element={<IndexPage />} />

        {/* 🔐 Auth-related pages */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/otp" element={<OtpVerification />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/register-details" element={<RegisterDetails />} />

        {/* 📊 Dashboard & App pages */}
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/app/*" element={<Dashboard />} />

        {/* 🔁 Catch-all route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;