import React, { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
import { GeoSearchControl, OpenStreetMapProvider } from "leaflet-geosearch";
import "leaflet/dist/leaflet.css";
import "leaflet-geosearch/dist/geosearch.css";
import L from "leaflet";
import "../styles/RegisterDetails.css";
import indiaDistricts from "./data/indiaDistricts";

// Fix default marker icon in leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

// 📍 Component to select a point by clicking
const LocationMarker = ({ onSelect }) => {
  const [position, setPosition] = useState(null);

  useMapEvents({
    click(e) {
      setPosition(e.latlng);
      onSelect(e.latlng);
    },
  });

  return position ? <Marker position={position} /> : null;
};

// 📍 Modal for map selection with search + click
const LocationPickerModal = ({ onClose, onSave }) => {
  const mapRef = useRef();

  useEffect(() => {
    if (!mapRef.current) return;

    const provider = new OpenStreetMapProvider();
    const searchControl = new GeoSearchControl({
      provider,
      style: "bar",
      autoComplete: true,
      autoCompleteDelay: 250,
      showMarker: true,
      showPopup: false,
      marker: {
        icon: new L.Icon.Default(),
        draggable: false,
      },
    });

    mapRef.current.addControl(searchControl);

    // When a location is selected via search
    mapRef.current.on("geosearch/showlocation", (result) => {
      const { x, y } = result.location; // lon, lat
      onSave({ lat: y, lng: x });
      onClose();
    });

    return () => {
      mapRef.current.removeControl(searchControl);
    };
  }, [onSave, onClose]);

  return (
    <div className="overlay">
      <div className="map-modal">
        <button className="close-btn" onClick={onClose}>
          ✖
        </button>
        <MapContainer
          center={[20.5937, 78.9629]} // India center
          zoom={5}
          style={{ height: "400px", width: "100%" }}
          whenCreated={(map) => (mapRef.current = map)}
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {/* Allow manual click to select farm location */}
          <LocationMarker
            onSelect={(coords) => {
              onSave(coords);
              onClose();
            }}
          />
        </MapContainer>
      </div>
    </div>
  );
};

const RegisterDetails = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const { phone, name, email, state } = location.state || {};

  const [address, setAddress] = useState({ line1: "", line2: "", line3: "" });
  const [district, setDistrict] = useState("");
  const [pin, setPin] = useState("");
  const [numCrops, setNumCrops] = useState(1);

  // Each crop has name, soil, landArea, farmLocation
  const [crops, setCrops] = useState([
    { name: "", soil: "", landArea: "", farmLocation: null },
  ]);

  // For modal control
  const [openMapIndex, setOpenMapIndex] = useState(null);

  useEffect(() => {
    setDistrict("");
  }, [state]);

  const handleCropCount = (delta) => {
    const newValue = Math.max(1, numCrops + delta);
    setNumCrops(newValue);
    setCrops(
      Array(newValue)
        .fill()
        .map(
          (_, i) =>
            crops[i] || { name: "", soil: "", landArea: "", farmLocation: null }
        )
    );
  };

  const handleCropChange = (index, field, value) => {
    const updatedCrops = [...crops];
    updatedCrops[index][field] = value;
    setCrops(updatedCrops);
  };

  const handleSubmit = async () => {
    if (!address.line1 || !address.line2 || !address.line3) {
      alert("⚠️ Please fill in all Address fields!");
      return;
    }

    if (!district) {
      alert("⚠️ Please select your District!");
      return;
    }

    if (!pin || pin.length !== 6 || !/^\d{6}$/.test(pin)) {
      alert("⚠️ Please enter a valid 6-digit Pincode!");
      return;
    }

    for (let i = 0; i < crops.length; i++) {
      const c = crops[i];
      if (!c.name || !c.soil || !c.landArea || !c.farmLocation) {
        alert(`⚠️ Please fill all details for Crop-${i + 1}!`);
        return;
      }
    }

    const userData = {
      phone,
      name,
      email,
      state,
      address,
      district,
      pin,
      crops,
    };

    try {
      const res = await fetch("http://127.0.0.1:5000/register-details", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(userData),
      });

      const data = await res.json();
      if (res.ok) {
        alert("✅ Registration completed! Redirecting to Dashboard...");
        navigate("/dashboard");
      } else {
        alert(data.error || "❌ Something went wrong");
      }
    } catch (err) {
      console.error("Error:", err);
      alert("❌ Server error");
    }
  };

  return (
    <div className="register-details">
      {/* LEFT PANEL */}
      <div className="left-panel">
        <button className="side-back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <h2>Welcome To</h2>
        <h1>KissanMitra</h1>
      </div>

      {/* RIGHT PANEL */}
      <div className="right-panel">
        <h2 className="form-heading">Create your account</h2>

        {/* Address */}
        <h3 className="section-title">Address</h3>
        <div className="form-group">
          <input
            type="text"
            placeholder="House name/Flat No"
            value={address.line1}
            onChange={(e) => setAddress({ ...address, line1: e.target.value })}
          />
          <input
            type="text"
            placeholder="Place"
            value={address.line2}
            onChange={(e) => setAddress({ ...address, line2: e.target.value })}
          />
          <input
            type="text"
            placeholder="Landmark"
            value={address.line3}
            onChange={(e) => setAddress({ ...address, line3: e.target.value })}
          />
        </div>
        <div className="form-group">
          <select value={district} onChange={(e) => setDistrict(e.target.value)}>
            <option value="">--Select District--</option>
            {indiaDistricts[state]?.map((d, i) => (
              <option key={i} value={d}>
                {d}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Enter the Pincode"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
          />
        </div>

        {/* Crops */}
        <h3 className="section-title">Crops</h3>
        <div className="form-group">
          <label>No. Crops*</label>
          <div className="crop-counter-controls">
            <button type="button" onClick={() => handleCropCount(-1)}>
              –
            </button>
            <span>{numCrops}</span>
            <button type="button" onClick={() => handleCropCount(1)}>
              +
            </button>
          </div>
        </div>

        {crops.map((crop, index) => (
          <div key={index} className="crop-section">
            <h4>Crop-{index + 1}</h4>
            <input
              type="text"
              placeholder="Crop name"
              value={crop.name}
              onChange={(e) => handleCropChange(index, "name", e.target.value)}
            />
            <input
              type="text"
              placeholder="Soil type"
              value={crop.soil}
              onChange={(e) => handleCropChange(index, "soil", e.target.value)}
            />
            <input
              type="text"
              placeholder="Land area (e.g., acres or sqm)"
              value={crop.landArea}
              onChange={(e) =>
                handleCropChange(index, "landArea", e.target.value)
              }
            />

            {/* Farm Location */}
            <button
              type="button"
              className="select-location-btn"
              onClick={() => setOpenMapIndex(index)}
            >
              Select Farm Location
            </button>
            {crop.farmLocation && (
              <p>
                📍 {crop.farmLocation.lat.toFixed(5)},{" "}
                {crop.farmLocation.lng.toFixed(5)}
              </p>
            )}
          </div>
        ))}

        <div className="button-group">
          <button className="submit-btn" onClick={handleSubmit}>
            Submit
          </button>
        </div>
      </div>

      {/* Map Modal */}
      {openMapIndex !== null && (
        <LocationPickerModal
          onClose={() => setOpenMapIndex(null)}
          onSave={(coords) => {
            handleCropChange(openMapIndex, "farmLocation", coords);
          }}
        />
      )}
    </div>
  );
};

export default RegisterDetails;
