import React, { useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix Leaflet's default icon paths under bundlers like CRA
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
    iconUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
    shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const INDIA_CENTER = [20.5937, 78.9629];

function toLat(s) {
    return parseFloat(s.latitude ?? s.Latitude);
}
function toLon(s) {
    return parseFloat(s.longitude ?? s.Longitude);
}

export default function MapView({ stations, picked, setPicked, routesResult }) {
    const polylines = useMemo(() => {
    // Expecting backend to include ors_geometry: [ [ [lon,lat], ... ], ... ]
    const g = routesResult?.ors_geometry;
    if (!Array.isArray(g)) return [];
    return g
        .filter(r => Array.isArray(r))
        .map(r => r.map(([lon, lat]) => [lat, lon]));
    }, [routesResult]);

    return (
    <MapContainer
        center={INDIA_CENTER}
        zoom={5}
        scrollWheelZoom
        style={{ height: "100%", width: "100%" }}
    >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

        {stations.map((s, idx) => {
        const lat = toLat(s);
        const lon = toLon(s);
        if (isNaN(lat) || isNaN(lon)) return null;

        const id = s.station_id || s.StationId;
        const name = s.StationName || s.station_name || id;

        const isStart = picked.start && (id === (picked.start.station_id || picked.start.StationId));
        const isEnd = picked.end && (id === (picked.end.station_id || picked.end.StationId));

        return (
            <Marker key={id || idx} position={[lat, lon]}>
            <Popup>
                <div style={{ minWidth: 180 }}>
                <b>{name}</b>
                <div>ID: {id}</div>
                <div>{s.City || s.city}</div>

                <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                    <button onClick={() => setPicked(p => ({ ...p, start: s }))}>
                    {isStart ? "✓ Start" : "Set Start"}
                    </button>
                    <button onClick={() => setPicked(p => ({ ...p, end: s }))}>
                    {isEnd ? "✓ End" : "Set End"}
                    </button>
                </div>
                </div>
            </Popup>
            </Marker>
        );
        })}

        {polylines.map((line, i) => (
        <Polyline key={i} positions={line} />
        ))}
    </MapContainer>
    );
}
