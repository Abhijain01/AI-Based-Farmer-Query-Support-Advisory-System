import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "../styles/RegisterPage.css";

const RegisterPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const phone = location.state?.phone; // phone passed from OTP page

  // user basic info
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [state, setState] = useState("");

  const handleNext = () => {
  if (!name || !email || !state) {
    alert("⚠️ Please fill all fields!");
    return;
  }

  // Email validation regex
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    alert("⚠️ Please enter a valid email address!");
    return;
  }

  // Pass collected info to RegisterDetails
  navigate("/register-details", {
    state: { phone, name, email, state },
  });
};


  return (
    <div className="register-container">
      {/* LEFT PANEL */}
      <div className="left-panel">
        <button className="back-btn" onClick={() => navigate(-1)}>← Back</button>
        <img src="/farmer.png" alt="Farmer" className="farmer-img" />
        <h2>Welcome To</h2>
        <h1>KissanMitra</h1>
      </div>

      {/* RIGHT PANEL */}
      <div className="right-panel">
        <h2>Create your account</h2>

        <div className="form-group">
          <label>Name</label>
          <input
            type="text"
            placeholder="Enter your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>E-mail address</label>
          <input
            type="email"
            placeholder="Enter your mail"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>State</label>
          <select value={state} onChange={(e) => setState(e.target.value)}>
            <option value="">-- Select your state --</option>
            <option value="Andhra Pradesh">Andhra Pradesh</option>
            <option value="Arunachal Pradesh">Arunachal Pradesh</option>
            <option value="Assam">Assam</option>
            <option value="Bihar">Bihar</option>
            <option value="Chhattisgarh">Chhattisgarh</option>
            <option value="Goa">Goa</option>
            <option value="Gujarat">Gujarat</option>
            <option value="Haryana">Haryana</option>
            <option value="Himachal Pradesh">Himachal Pradesh</option>
            <option value="Jharkhand">Jharkhand</option>
            <option value="Karnataka">Karnataka</option>
            <option value="Kerala">Kerala</option>
            <option value="Madhya Pradesh">Madhya Pradesh</option>
            <option value="Maharashtra">Maharashtra</option>
            <option value="Manipur">Manipur</option>
            <option value="Meghalaya">Meghalaya</option>
            <option value="Mizoram">Mizoram</option>
            <option value="Nagaland">Nagaland</option>
            <option value="Odisha">Odisha</option>
            <option value="Punjab">Punjab</option>
            <option value="Rajasthan">Rajasthan</option>
            <option value="Sikkim">Sikkim</option>
            <option value="Tamil Nadu">Tamil Nadu</option>
            <option value="Telangana">Telangana</option>
            <option value="Tripura">Tripura</option>
            <option value="Uttar Pradesh">Uttar Pradesh</option>
            <option value="Uttarakhand">Uttarakhand</option>
            <option value="West Bengal">West Bengal</option>
            <option value="Andaman and Nicobar Islands">Andaman and Nicobar Islands</option>
            <option value="Chandigarh">Chandigarh</option>
            <option value="Dadra and Nagar Haveli and Daman and Diu">
              Dadra and Nagar Haveli and Daman and Diu
            </option>
            <option value="Delhi">Delhi</option>
            <option value="Jammu and Kashmir">Jammu and Kashmir</option>
            <option value="Ladakh">Ladakh</option>
            <option value="Lakshadweep">Lakshadweep</option>
            <option value="Puducherry">Puducherry</option>
          </select>
        </div>

        <button className="next-btn" onClick={handleNext}>
          Next
        </button>
      </div>
    </div>
  );
};

export default RegisterPage;
