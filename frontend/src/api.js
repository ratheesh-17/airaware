// Centralized API calls for backend
import axios from "axios";

// Backend API base URL - adjust if backend runs on different port
const API = axios.create({ 
    baseURL: process.env.REACT_APP_API_URL || "http://localhost:8000",
    timeout: 30000 // 30 second timeout for route predictions
});

export async function fetchStations() {
    try {
        const r = await API.get("/api/stations");
        return r.data || [];
    } catch (error) {
        console.error("Failed to fetch stations:", error);
        throw error;
    }
}

export async function predictRoute({ source, destination }) {
    // source, destination: "lat,lon"
    try {
        const r = await API.post("/api/predict-route", { source, destination });
        return r.data;
    } catch (error) {
        console.error("Failed to predict route:", error);
        throw error;
    }
}
