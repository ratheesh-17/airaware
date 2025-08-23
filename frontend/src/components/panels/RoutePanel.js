import React from "react";
import StationCard from "./StationCard";

export default function RoutePanel({ routesResult }) {
    if (!routesResult) {
    return <p>No route predicted yet. Choose start & end and click “Predict Route”.</p>;
    }

    const routes = routesResult.routes || [];
    const summary = routes.map((r) => ({
    idx: r.route_index,
    avg: Array.isArray(r.avg_forecast_pm2_5) ? r.avg_forecast_pm2_5[0] : null,
    max: Array.isArray(r.max_forecast_pm2_5) ? r.max_forecast_pm2_5[0] : null,
    waypoints: r.waypoints
    }));

    return (
    <div>
        <h3>Routes Summary</h3>
        {summary.length === 0 && <p>No valid predictions returned.</p>}
        {summary.map((r) => (
        <div key={r.idx} style={{ borderBottom: "1px solid #eee", padding: "8px 0" }}>
            <div><b>Route {r.idx}</b></div>
            <div>Avg PM2.5: {r.avg ?? "N/A"}</div>
            <div>Max PM2.5: {r.max ?? "N/A"}</div>
            <div>Waypoints: {r.waypoints}</div>
        </div>
        ))}

        {routesResult.gemini_summary && (
        <>
            <h4 style={{ marginTop: 12 }}>AI Summary</h4>
            <div style={{ whiteSpace: "pre-wrap" }}>
            {routesResult.gemini_summary}
            </div>
        </>
        )}

        <h4 style={{ marginTop: 12 }}>Raw Response (debug)</h4>
        <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>
        {JSON.stringify(routesResult, null, 2)}
        </pre>

        <StationCard />
    </div>
    );
}
