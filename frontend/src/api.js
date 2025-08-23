// Centralized API calls for backend
import axios from "axios";

// If backend is a different origin/port, set baseURL here:
// const API = axios.create({ baseURL: "http://localhost:8000" });
const API = axios.create({ baseURL: "" }); // same-origin (CRA proxy can also be used)

export async function fetchStations() {
    const r = await API.get("/api/stations");
    return r.data || [];
}

export async function predictRoute({ source, destination }) {
  // source, destination: "lat,lon"
    const r = await API.post("/api/predict-route", { source, destination });
    return r.data;
}
