import React, { useState } from "react";
import "../styles/LoginPage.css";  
import backgroundImage from "../assets/farm.png";  
import logo from "../assets/log_nobg.jpg";        
import { FaPhoneVolume } from "react-icons/fa6";
import { useNavigate } from "react-router-dom";

const LoginPage = () => {
  const [phone, setPhone] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false); // ✅ track checkbox
  const navigate = useNavigate();

  const handleSendOtp = async () => {
    // Empty check
    if (!phone) {
      alert("⚠️ Please enter your phone number!");
      return;
    }

    // Mobile number validation (Indian format: 10 digits, starts with 6–9)
    const phoneRegex = /^[6-9]\d{9}$/;
    if (!phoneRegex.test(phone)) {
      alert("⚠️ Please enter a valid 10-digit mobile number!");
      return;
    }

    // Checkbox validation
    if (!acceptedTerms) {
      alert("⚠️ Please accept the terms & conditions to proceed!");
      return;
    }

    try {
      const res = await fetch("http://127.0.0.1:5000/send-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
      });

      const data = await res.json();
      if (res.ok) {
        console.log("✅ OTP sent:", data.otp); // TEMP: shows OTP in console
        // Save phone to localStorage for OTP page
        localStorage.setItem("phone", phone);
        navigate("/otp", { state: { phone } });
      } else {
        alert(data.error || "❌ Failed to send OTP");
      }
    } catch (err) {
      console.error("Error:", err);
      alert("❌ Something went wrong while sending OTP!");
    }
  };

  return (
    <div className="login-page">
      <div
        className="image-box"
        style={{ backgroundImage: `url(${backgroundImage})` }}
      >
        <div className="logo">
          <img src={logo} alt="App Logo" />
        </div>
        <div className="login-card">
          <h2>Login</h2>
          <div className="input-group">
            <h4>Phone Number</h4>
            <input
              type="tel"
              placeholder="Enter your phone number"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <span className="phone-icon">
              <FaPhoneVolume />
            </span>
          </div>

          <div className="checkbox">
            <input
              type="checkbox"
              id="terms"
              checked={acceptedTerms}
              onChange={(e) => setAcceptedTerms(e.target.checked)}
            />
            <label htmlFor="terms">
              I accept <a href="#">terms & conditions</a>
            </label>
          </div>

          <button className="send-otp" onClick={handleSendOtp}>
            SEND OTP
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
