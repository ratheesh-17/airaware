import React from "react";

// Placeholder card for future station details (prediction, latest readings, etc.)
export default function StationCard() {
    return (
    <div style={{
        marginTop: 12,
        border: "1px solid #e6e6e6",
        borderRadius: 10,
        padding: 10
    }}>
        <b>Station Details</b>
        <div style={{ color: "#666" }}>
        Click a station marker to set Start/End. After prediction, details can be shown here.
        </div>
    </div>
    );
}
