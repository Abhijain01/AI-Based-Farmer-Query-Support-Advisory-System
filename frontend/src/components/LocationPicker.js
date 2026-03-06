// LocationPickerModal.js
import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import {
  GeoSearchControl,
  OpenStreetMapProvider,
} from "leaflet-geosearch";
import "leaflet-geosearch/dist/geosearch.css";

// ✅ Fix default marker issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

// ✅ Component to add search control inside react-leaflet
function SearchControl({ onSelect }) {
  const map = useMap();
  const controlRef = useRef(null);

  useEffect(() => {
    const provider = new OpenStreetMapProvider();

    const searchControl = new GeoSearchControl({
      provider,
      style: "bar", // shows search bar at the top
      autoComplete: true,
      autoCompleteDelay: 250,
      showMarker: true,
      showPopup: false,
      retainZoomLevel: false,
      animateZoom: true,
      marker: {
        icon: new L.Icon.Default(),
        draggable: false,
      },
    });

    controlRef.current = searchControl;
    map.addControl(searchControl);

    map.on("geosearch/showlocation", (result) => {
      const { x, y } = result.location;
      onSelect({ lat: y, lng: x });
    });

    return () => {
      if (controlRef.current) {
        map.removeControl(controlRef.current);
      }
    };
  }, [map, onSelect]);

  return null;
}

export default function LocationPickerModal({ onSave, onClose }) {
  return (
    <div
      style={{
        position: "fixed",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        width: "80%",
        height: "70%",
        background: "white",
        zIndex: 2000,
        borderRadius: "10px",
        overflow: "hidden",
        boxShadow: "0 4px 8px rgba(0,0,0,0.2)",
      }}
    >
      {/* Close button */}
      <button
        onClick={onClose}
        style={{
          position: "absolute",
          top: "10px",
          right: "10px",
          zIndex: 3000,
          background: "red",
          color: "white",
          border: "none",
          borderRadius: "50%",
          width: "30px",
          height: "30px",
          cursor: "pointer",
        }}
      >
        ✕
      </button>

      {/* Map */}
      <MapContainer
        center={[20.5937, 78.9629]}
        zoom={5}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />
        {/* ✅ Inject search bar */}
        <SearchControl
          onSelect={(coords) => {
            onSave(coords);
            onClose();
          }}
        />
      </MapContainer>
    </div>
  );
}
