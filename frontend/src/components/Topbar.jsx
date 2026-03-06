import React, { useState, useEffect } from "react";
import { FaUserCircle } from "react-icons/fa";
import "../styles/topbar.css";

const Topbar = () => {
  const [open, setOpen] = useState(false);
  const [location, setLocation] = useState("Fetching...");
  const [user, setUser] = useState(null);

  // ✅ Fetch user from backend
  useEffect(() => {
    const phone = localStorage.getItem("phone");
    if (phone) {
      fetch(`http://127.0.0.1:5000/get-user?phone=${phone}`)
        .then((r) => r.json())
        .then(setUser)
        .catch(() => setUser({ name: "Guest" }));
    } else {
      setUser({ name: "Guest" });
    }
  }, []);

  // ✅ Get current location & update DB
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          const { latitude, longitude } = pos.coords;
          try {
            // Reverse geocode → get city name
            const response = await fetch(
              `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`
            );
            const data = await response.json();

            const city =
              data.address.city ||
              data.address.town ||
              data.address.village ||
              data.address.state_district ||
              data.address.state ||
              "Unknown";

            setLocation(city);

            // ✅ Save/update location in backend
            const phone = localStorage.getItem("phone");
            if (phone) {
              await fetch("http://127.0.0.1:5000/update-location", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  phone,
                  lat: latitude,
                  lon: longitude,
                  city,
                }),
              });
            }
          } catch (err) {
            console.error("Error fetching location:", err);
            setLocation("Unavailable");
          }
        },
        (error) => {
          console.error("Geolocation error:", error);
          setLocation("Permission denied");
        }
      );
    } else {
      setLocation("Not supported");
    }
  }, []);

  // ✅ Logout function
  const handleLogout = () => {
    localStorage.removeItem("phone");
    window.location.reload();
  };

  return (
    <header className="topbar">
      <div className="topbar-left">
        {/* Logo/Name removed as it is already in Sidebar */}
      </div>

      <div className="topbar-right">
        {/* ✅ Location moved to right */}
        <div className="location">{location}</div>

        <div className="lang">EN ▾</div>
        <div className="profile" onClick={() => setOpen(!open)}>
          <FaUserCircle size={28} className="profile-icon" />
          <span>{user?.name || "Guest"}</span>
          {open && (
            <div className="profile-menu">
              <button>View profile</button>
              <button>Edit profile</button>
              <button onClick={handleLogout}>Logout</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Topbar;
