import React from "react";
export default function PredictionView({ isForecast }) {
  return (
    <div>
      <h2>{isForecast ? "Weather Forecast" : "Crop Prediction"}</h2>
      <div style={{display:"flex",gap:12}}>
        <button>New</button>
        <button>Find disease in plant</button>
      </div>
      <div style={{marginTop:20}}>
        {/* If uploading an image is required use same file upload flow as ChatView */}
      </div>
    </div>
  );
}
