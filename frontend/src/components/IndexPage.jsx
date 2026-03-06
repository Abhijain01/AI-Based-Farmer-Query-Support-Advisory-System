import React from "react";
import { useNavigate } from "react-router-dom";
import "../styles/IndexPage.css";

const IndexPage = () => {
  const navigate = useNavigate();

  return (
    <div className="index-container">
      {/* Header Section */}
      <header className="index-header">
        {/* ✅ Logo image from public folder */}
        <img 
          src="/favicon.jpg" 
          alt="Kissan Mitra Logo" 
          className="app-logo" 
        />
        <h1 className="logo-text">KISSAN MITRA</h1>
      </header>

      {/* Main Content */}
      <main className="index-main">
        <h2>Welcome to <span>Kissan Mitra</span></h2>
        <p>Your trusted companion for smarter and sustainable farming.</p>

        <button className="login-button" onClick={() => navigate("/login")}>
          Click to Login
        </button>
      </main>

      {/* Footer */}
      <footer className="index-footer">
        <p>© {new Date().getFullYear()} Kissan Mitra. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default IndexPage;
