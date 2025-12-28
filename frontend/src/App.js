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
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setError(null);
        const data = await fetchStations();
        console.log('Loaded stations:', data);
        setStations(data || []);
      } catch (e) {
        console.error('Failed to load stations:', e);
        setError('Failed to load stations. Make sure the backend is running on port 8000.');
      }
    })();
  }, []);

  const startLabel = picked.start
    ? (picked.start.name || picked.start.StationName || picked.start.station_name || picked.start.StationId || picked.start.station_id || picked.start.id)
    : "Select start location";

  const endLabel = picked.end
    ? (picked.end.name || picked.end.StationName || picked.end.station_name || picked.end.StationId || picked.end.station_id || picked.end.id)
    : "Select destination";

  const canPredict = useMemo(
    () => picked.start && picked.end && picked.start !== picked.end,
    [picked.start, picked.end]
  );

  async function onPredict() {
    if (!canPredict) return;
    setLoading(true);
    setError(null);
    
    try {
      // Handle different coordinate field names
      const sLat = picked.start.latitude ?? picked.start.Latitude ?? picked.start['coordinates.latitude'];
      const sLon = picked.start.longitude ?? picked.start.Longitude ?? picked.start['coordinates.longitude'];
      const dLat = picked.end.latitude ?? picked.end.Latitude ?? picked.end['coordinates.latitude'];
      const dLon = picked.end.longitude ?? picked.end.Longitude ?? picked.end['coordinates.longitude'];

      if (!sLat || !sLon || !dLat || !dLon) {
        throw new Error('Invalid coordinates for selected locations');
      }

      const source = `${sLat},${sLon}`;
      const destination = `${dLat},${dLon}`;
      
      console.log('Predicting route from', source, 'to', destination);
      const res = await predictRoute({ source, destination });
      console.log('Route prediction result:', res);
      setRoutesResult(res);
    } catch (e) {
      console.error('Route prediction failed:', e);
      setError('Route prediction failed: ' + e.message);
    }
    setLoading(false);
  }

  const getStationId = (station) => {
    return station?.id || station?.station_id || station?.StationId;
  };

  const getStationName = (station) => {
    return station?.name || station?.StationName || station?.station_name || getStationId(station);
  };

  return (
    <div className="app">
      <Header>
        <div className="controls">
          {error && (
            <div style={{ color: 'red', marginBottom: '10px', fontSize: '14px' }}>
              {error}
            </div>
          )}
          
          {/* Start dropdown */}
          <select
            value={picked.start ? getStationId(picked.start) : ""}
            onChange={(e) => {
              const id = e.target.value;
              const st = stations.find(s => getStationId(s) === id);
              setPicked(p => ({ ...p, start: st || null }));
            }}
            disabled={stations.length === 0}
          >
            <option value="">{stations.length === 0 ? 'Loading stations...' : startLabel}</option>
            {stations.map((s) => {
              const id = getStationId(s);
              const name = getStationName(s);
              return <option key={id} value={id}>{name}</option>;
            })}
          </select>

          {/* End dropdown */}
          <select
            value={picked.end ? getStationId(picked.end) : ""}
            onChange={(e) => {
              const id = e.target.value;
              const st = stations.find(s => getStationId(s) === id);
              setPicked(p => ({ ...p, end: st || null }));
            }}
            disabled={stations.length === 0}
          >
            <option value="">{stations.length === 0 ? 'Loading stations...' : endLabel}</option>
            {stations.map((s) => {
              const id = getStationId(s);
              const name = getStationName(s);
              return <option key={id} value={id}>{name}</option>;
            })}
          </select>

          <button onClick={onPredict} disabled={!canPredict || loading || stations.length === 0}>
            {loading ? "Predicting..." : "Predict Route"}
          </button>
          
          {stations.length > 0 && (
            <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
              {stations.length} stations loaded
            </div>
          )}
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
