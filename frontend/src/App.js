import React, { useEffect, useMemo, useState } from "react";
import "./App.css";
import Header from "./components/layout/Header";
import MapView from "./components/map/MapView";
import RoutePanel from "./components/panels/RoutePanel";
import { fetchStations, predictRoute } from "./api";

export default function App() {
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [routesResult, setRoutesResult] = useState(null);
  const [picked, setPicked] = useState({ start: null, end: null });

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchStations();
        setStations(data || []);
      } catch (e) {
        console.error(e);
        alert("Failed to load stations. Check backend /api/stations.");
      }
    })();
  }, []);

  const startLabel = picked.start
    ? (picked.start.StationName || picked.start.station_name || picked.start.StationId || picked.start.station_id)
    : "Select start";

  const endLabel = picked.end
    ? (picked.end.StationName || picked.end.station_name || picked.end.StationId || picked.end.station_id)
    : "Select end";

  const canPredict = useMemo(
    () => picked.start && picked.end,
    [picked.start, picked.end]
  );

  async function onPredict() {
    if (!canPredict) return;
    setLoading(true);
    const sLat = picked.start.latitude ?? picked.start.Latitude;
    const sLon = picked.start.longitude ?? picked.start.Longitude;
    const dLat = picked.end.latitude ?? picked.end.Latitude;
    const dLon = picked.end.longitude ?? picked.end.Longitude;

    const source = `${sLat},${sLon}`;
    const destination = `${dLat},${dLon}`;
    try {
      const res = await predictRoute({ source, destination });
      setRoutesResult(res);
    } catch (e) {
      console.error(e);
      alert("Route prediction failed. Check backend /api/predict-route logs.");
    }
    setLoading(false);
  }

  return (
    <div className="app">
      <Header>
        <div className="controls">
          {/* Start dropdown */}
          <select
            value={picked.start ? (picked.start.station_id || picked.start.StationId) : ""}
            onChange={(e) => {
              const id = e.target.value;
              const st = stations.find(s => (s.station_id || s.StationId) === id);
              setPicked(p => ({ ...p, start: st || null }));
            }}
          >
            <option value="">{startLabel}</option>
            {stations.map((s) => {
              const id = s.station_id || s.StationId;
              const nm = s.StationName || s.station_name || id;
              return <option key={id} value={id}>{nm}</option>;
            })}
          </select>

          {/* End dropdown */}
          <select
            value={picked.end ? (picked.end.station_id || picked.end.StationId) : ""}
            onChange={(e) => {
              const id = e.target.value;
              const st = stations.find(s => (s.station_id || s.StationId) === id);
              setPicked(p => ({ ...p, end: st || null }));
            }}
          >
            <option value="">{endLabel}</option>
            {stations.map((s) => {
              const id = s.station_id || s.StationId;
              const nm = s.StationName || s.station_name || id;
              return <option key={id} value={id}>{nm}</option>;
            })}
          </select>

          <button onClick={onPredict} disabled={!canPredict || loading}>
            {loading ? "Predicting..." : "Predict Route"}
          </button>
        </div>
      </Header>

      <div className="main">
        <MapView
          stations={stations}
          picked={picked}
          setPicked={setPicked}
          routesResult={routesResult}
        />
        <div className="panel">
          <RoutePanel routesResult={routesResult} />
        </div>
      </div>
    </div>
  );
}
