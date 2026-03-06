// src/components/CropMap.jsx
import React, { useState } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix default icon paths
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
const DefaultIcon = L.icon({
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

function LocationMarker({ onSelect }) {
  const [pos, setPos] = useState(null);
  useMapEvents({
    click(e) {
      setPos(e.latlng);
      onSelect(e.latlng); // notify parent
    },
  });
  return pos ? <Marker position={pos} /> : null;
}

export default function CropMap({ onSelect, center = [20.5937, 78.9629], zoom = 5 }) {
  return (
    <div style={{ height: "360px", width: "100%" }}>
      <MapContainer center={center} zoom={zoom} style={{ height: "100%", width: "100%" }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <LocationMarker onSelect={onSelect} />
      </MapContainer>
    </div>
  );
}
