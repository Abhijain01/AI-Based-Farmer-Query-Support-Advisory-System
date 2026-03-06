import React from "react";
import "../styles/schemes.css";

const schemesData = [
  {
    title: "PM-Kisan Samman Nidhi",
    desc: "Direct income support of ₹6000 per year to farmers in three installments.",
    link: "https://pmkisan.gov.in/",
  },
  {
    title: "Pradhan Mantri Fasal Bima Yojana",
    desc: "Crop insurance scheme to protect farmers against crop failure due to natural calamities.",
    link: "https://pmfby.gov.in/",
  },
  {
    title: "Soil Health Card Scheme",
    desc: "Provides farmers with soil nutrient status and crop-wise recommendations.",
    link: "https://soilhealth.dac.gov.in/",
  },
  {
    title: "Kisan Credit Card (KCC)",
    desc: "Credit facility for farmers at low interest rates for agricultural expenses.",
    link: "https://www.myscheme.gov.in/schemes/kcc",
  },
  {
    title: "National Mission on Sustainable Agriculture",
    desc: "Promotes sustainable agriculture practices and climate-resilient farming.",
    link: "https://nmsa.dac.gov.in/",
  },
  {
    title: "Paramparagat Krishi Vikas Yojana",
    desc: "Encourages organic farming through cluster-based approach.",
    link: "https://pgsindia-ncof.gov.in/",
  },
];

const SchemesView = () => {
  return (
    <div className="schemes-container">
      <h2 className="page-title">🌱 Government Schemes for Farmers</h2>

      <div className="schemes-grid">
        {schemesData.map((scheme, index) => (
          <div key={index} className="scheme-card">
            <h3>{scheme.title}</h3>
            <p>{scheme.desc}</p>
            <a href={scheme.link} target="_blank" rel="noopener noreferrer">
              <button className="learn-more-btn">Learn More</button>
            </a>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SchemesView;
