import React from "react";
import "../styles/loader.css";

export default function Loader() {
  return (
    <div className="loader-container">
      <video
        className="loader-video"
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
      >
        <source src="/loader/loading.mp4" type="video/mp4" />
        Your browser does not support the video tag.
      </video>
    </div>
  );
}
