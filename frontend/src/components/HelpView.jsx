import React from "react";
import "../styles/HelpDesk.css";
import { Phone, Mail, MapPin, Facebook, Twitter, Instagram } from "lucide-react";

export default function HelpDesk() {
  return (
    <div className="help-container">
      <h1>🌿 Help Desk & Support</h1>
      <p className="subtitle">We're here to help you 24/7. Reach out anytime.</p>

      <div className="contact-section">
        <h2 className="section-title"><Phone /> Call Us</h2>
        <ul>
          <li>📞 +91 98765 43210</li>
          <li>📞 +91 87654 32109</li>
        </ul>
        <p>Available: Mon – Sat (9:00 AM – 6:00 PM)</p>
      </div>

      <div className="contact-section email-section">
        <h2 className="section-title"><Mail /> Email Support</h2>
        <ul>
          <li>📧 <a href="mailto:support@kissanmitra.in">support@kissanmitra.in</a></li>
          <li>📧 <a href="mailto:helpdesk@kissanmitra.in">helpdesk@kissanmitra.in</a></li>
        </ul>
        <p>We reply within 24 hours.</p>
      </div>

      <div className="contact-section">
        <h2 className="section-title"><MapPin /> Visit Our Office</h2>
        <div className="office-address">
          <p><strong>Kissan Mitra HQ</strong></p>
          <p>Plot No. 21, AgriTech Park</p>
          <p>Ludhiana, Punjab, India</p>
          <p>📞 +91 99887 66554</p>
        </div>
      </div>

      <div className="contact-section">
        <h2 className="section-title">🌐 Follow Us</h2>
        <div className="social-links">
          <a href="#"><Facebook /></a>
          <a href="#"><Twitter /></a>
          <a href="#"><Instagram /></a>
        </div>
      </div>
    </div>
  );
}
