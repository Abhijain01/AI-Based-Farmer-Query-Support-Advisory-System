import React, { useState, useEffect } from "react";
import "../styles/OtpVerification.css";   
import backgroundImage from "../assets/farm.png";  
import logo from "../assets/log_nobg.jpg";        
import { FaPhoneVolume } from "react-icons/fa6";
import { useNavigate, useLocation } from "react-router-dom";

const OtpVerification = () => {
  const [otp, setOtp] = useState("");
  const [timer, setTimer] = useState(120); // 2 minutes
  const [resendClicked, setResendClicked] = useState(false); // track style
  const location = useLocation();
  const navigate = useNavigate();

  // ✅ Get phone from state OR localStorage
  const phone = location.state?.phone || localStorage.getItem("phone");

  // ⏳ countdown effect
  useEffect(() => {
    let countdown;
    if (timer > 0) {
      countdown = setInterval(() => {
        setTimer((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(countdown);
  }, [timer]);

  const handleVerifyOtp = async () => {
    if (!otp) {
      alert("⚠️ Enter the OTP");
      return;
    }
    if (!phone) {
      alert("⚠️ Phone number required!");
      return;
    }

    try {
      const res = await fetch("http://127.0.0.1:5000/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, otp }),
      });

      const data = await res.json();

      if (res.ok) {
        if (data.existing_user) {
          alert("✅ Welcome back! Redirecting to Dashboard...");
          navigate("/dashboard");
        } else {
          alert("📝 New user detected! Redirecting to Registration...");
          navigate("/register", { state: { phone } });
        }
      } else {
        alert(data.error || "❌ Invalid OTP");
      }
    } catch (err) {
      console.error("Error:", err);
      alert("⚠️ Something went wrong!");
    }
  };

  const handleResendOtp = async () => {
    if (!phone) {
      alert("⚠️ Phone number required!");
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
        alert("🔄 OTP resent successfully!");
        console.log("Resent OTP:", data.otp); // TEMP for debugging
        setTimer(120); // restart countdown
        setResendClicked(true); // change style
      } else {
        alert(data.error || "❌ Failed to resend OTP");
      }
    } catch (err) {
      console.error("Error:", err);
      alert("⚠️ Something went wrong while resending OTP!");
    }
  };

  // format timer mm:ss
  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60)
      .toString()
      .padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
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
          <h2>OTP Verification</h2>
          <div className="input-group">
            <h4>OTP</h4>
            <input
              type="tel"
              placeholder="Enter the OTP"
              value={otp}
              onChange={(e) => setOtp(e.target.value)} 
            />
            <span className="phone-icon">
              <FaPhoneVolume />
            </span>
          </div>

          {/* Resend OTP */}
          <div className="resent_otp">
            {timer > 0 ? (
              <p>⏳ Resend available in {formatTime(timer)}</p>
            ) : (
              <button 
                onClick={handleResendOtp} 
                className={`resend-btn ${resendClicked ? "clicked" : ""}`}
              >
                Resend OTP
              </button>
            )}
          </div>

          <button className="verify-otp" onClick={handleVerifyOtp}>
            Verify OTP
          </button>
        </div>
      </div>
    </div>
  );
};

export default OtpVerification;
