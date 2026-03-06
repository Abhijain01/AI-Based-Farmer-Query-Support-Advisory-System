import React from "react";
import { NavLink } from "react-router-dom";
import "../styles/sidebar.css";
import logo from "../assets/log_nobg.jpg";
import { FaHome } from "react-icons/fa";
import { IoLogoWechat } from "react-icons/io5";
import { MdOnlinePrediction } from "react-icons/md";
import { TiWeatherPartlySunny } from "react-icons/ti";
import { TbBusinessplan } from "react-icons/tb";
import { RiGovernmentLine } from "react-icons/ri";
import { GiTrade } from "react-icons/gi";
import { GiChemicalTank } from "react-icons/gi";


const Sidebar = () => {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="logo-container">
          <img src={logo} alt="KissanMitra Logo" className="brand-logo" />
        </div>
        <div className="brand-name">KissanMitra</div>
      </div>

      <nav className="nav">
        <NavLink to="/app/home" className="nav-item"><FaHome /> Home</NavLink>
        <NavLink to="/app/queries" className="nav-item"><IoLogoWechat /> Queries</NavLink>
        <NavLink to="/app/prediction" className="nav-item"><MdOnlinePrediction /> Prediction</NavLink>
        <NavLink to="/app/forecast" className="nav-item"><TiWeatherPartlySunny /> Forecast</NavLink>
        <NavLink to="/app/market" className="nav-item"><TbBusinessplan /> Market</NavLink>
        <NavLink to="/app/schemes" className="nav-item"><RiGovernmentLine /> Schemes</NavLink>
        <NavLink to="/app/trade" className="nav-item"><GiTrade /> Trade</NavLink>
        <NavLink to="/app/fertilizers" className="nav-item"><GiChemicalTank /> Fertilizers</NavLink>
        <NavLink to="/app/help" className="nav-item">❓ Help Desk</NavLink>
      </nav>

      <div className="sidebar-footer">
        <small>v1.0</small>
      </div>
    </aside>
  );
};

export default Sidebar;
