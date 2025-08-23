import React from "react";

export default function Header({ children }) {
    return (
    <div className="header-bar">
        <h1>AirAware — Route AQI Visualizer</h1>
        {children}
    </div>
    );
}
