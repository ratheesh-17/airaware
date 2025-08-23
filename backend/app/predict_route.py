from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
import os
import requests
import math
import numpy as np
import pandas as pd
import logging

from .database import get_db
from .api_quota import guard_api, check_system_enabled
from .utils.simple_cache import get_cache, set_cache
from .predict import predict_from_vector, load_model
from .gemini import call_gemini
from .utils.email import send_alert_email

# --------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

DATASETS_DIR = Path(__file__).resolve().parents[2] / "datasets"
STATIONS_CSV = DATASETS_DIR / "stations.csv"

# --------------------------------------------------------------------
# Station metadata
# --------------------------------------------------------------------
if STATIONS_CSV.exists():
    DATASETS_DIR = Path(__file__).resolve().parents[2] / "datasets"
STATIONS_CSV = DATASETS_DIR / "stations.csv"

if STATIONS_CSV.exists():
    try:
        stations_meta = pd.read_csv(STATIONS_CSV)
        stations_meta.columns = [c.strip().lower() for c in stations_meta.columns]
        stations_meta = stations_meta.rename(columns={"lat": "latitude", "lng": "longitude"})
        stations_meta["latitude"] = stations_meta["latitude"].astype(float)
        stations_meta["longitude"] = stations_meta["longitude"].astype(float)
    except Exception as e:
        logger.exception("Failed to load station CSV: %s", e)
        stations_meta = pd.DataFrame(columns=["station_id", "latitude", "longitude"])
else:
    logger.warning("stations.csv not found at %s", STATIONS_CSV)
    stations_meta = pd.DataFrame(columns=["station_id", "latitude", "longitude"])


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters between two lat/lon points."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def find_nearest_station(lat: float, lon: float):
    """Find the nearest station by Haversine distance."""
    if stations_meta.empty:
        return None
    stations_meta["dist"] = stations_meta.apply(
        lambda r: haversine(lat, lon, r["latitude"], r["longitude"]), axis=1
    )
    nearest = stations_meta.loc[stations_meta["dist"].idxmin()]
    return nearest.get("station_id", None)


def sample_polyline(coords, step_m: int = 300):
    """Resample polyline geometry into evenly spaced waypoints."""
    sampled = []

    def segdist(a, b):
        return haversine(a[1], a[0], b[1], b[0])

    for i in range(len(coords) - 1):
        a, b = coords[i], coords[i + 1]
        seglen = segdist(a, b)
        if seglen == 0:
            continue
        n = max(1, int(seglen // step_m))
        for s in range(n):
            t = s / n
            lon = a[0] + (b[0] - a[0]) * t
            lat = a[1] + (b[1] - a[1]) * t
            sampled.append((lat, lon))
    if coords:
        sampled.append((coords[-1][1], coords[-1][0]))
    return sampled


# --------------------------------------------------------------------
# ML Model
# --------------------------------------------------------------------
_model_cache = None
_feature_cols_cache = None

def get_model():
    global _model_cache, _feature_cols_cache
    if _model_cache is None or _feature_cols_cache is None:
        _model_cache, _feature_cols_cache = load_model()
    return _model_cache, _feature_cols_cache


# --------------------------------------------------------------------
# External APIs
# --------------------------------------------------------------------
@guard_api("openrouteservice")
def call_ors(db: Session, s_lat: float, s_lon: float, d_lat: float, d_lon: float):
    """Call OpenRouteService for driving routes."""
    ORS_KEY = os.getenv("OPENROUTESERVICE_API_KEY")
    if not ORS_KEY:
        raise HTTPException(status_code=500, detail="ORS key not configured")

    url = "https://api.openrouteservice.org/v2/directions/driving-car/json"

    headers = {"Authorization": ORS_KEY, "Content-Type": "application/json"}
    body = {
        "coordinates": [[s_lon, s_lat], [d_lon, d_lat]],
        "options": {"instructions": False},
        "alternative_routes": {"share_factor": 0.6, "target_count": 3},
    }

    resp = requests.post(url, json=body, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


@guard_api("openweathermap")
def call_owm(db: Session, lat: float, lon: float):
    """Call OpenWeatherMap Air Pollution API."""
    OWM_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
    if not OWM_KEY:
        raise HTTPException(status_code=500, detail="OWM key not configured")

    url = "http://api.openweathermap.org/data/2.5/air_pollution"
    resp = requests.get(url, params={"lat": lat, "lon": lon, "appid": OWM_KEY}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_latest_from_db(db: Session, station_id: str):
    """Fetch latest air quality readings from DB."""
    if not station_id:
        return None
    try:
        row = db.execute(
            text("SELECT station_id, pm2_5, pm10, no2, co, o3 FROM latest_readings WHERE station_id = :sid"),
            {"sid": station_id},
        ).first()
        return dict(row._mapping) if row else None
    except Exception:
        logger.exception("DB query failed for station %s", station_id)
        return None


# --------------------------------------------------------------------
# Route Prediction Endpoint
# --------------------------------------------------------------------
@router.post("/predict-route")
def predict_route(payload: dict, db: Session = Depends(get_db), bg: BackgroundTasks = None):
    """Predict air quality along alternative driving routes."""
    check_system_enabled(db)

    # Parse input
    try:
        s_lat, s_lon = map(float, payload["source"].split(","))
        d_lat, d_lon = map(float, payload["destination"].split(","))
    except Exception:
        raise HTTPException(status_code=400, detail="source/destination must be 'lat,lon'")

    model, feature_cols = get_model()

    # Fetch ORS routes (cached)
    ors_key = f"ors:{s_lat:.6f}:{s_lon:.6f}:{d_lat:.6f}:{d_lon:.6f}"
    ors_json = get_cache(ors_key)
    if ors_json is None:
        try:
            ors_json = call_ors(db, s_lat, s_lon, d_lat, d_lon)
            set_cache(ors_key, ors_json, ttl=600)
        except Exception:
            logger.exception("ORS call failed")
            raise HTTPException(status_code=502, detail="Route provider failed")

    # Normalize features (FIXED)
    features = []
    if "routes" in ors_json:  # Standard ORS response
        for r in ors_json["routes"]:
            geom = r.get("geometry")
            if geom:
                if isinstance(geom, str):  # Encoded polyline
                    try:
                        from openrouteservice import convert
                        coords = convert.decode_polyline(geom)["coordinates"]
                    except Exception:
                        logger.exception("Failed to decode ORS polyline")
                        coords = []
                elif isinstance(geom, dict) and "coordinates" in geom:
                    coords = geom["coordinates"]
                else:
                    coords = []
                features.append({"geometry": {"coordinates": coords}})
    elif "features" in ors_json:  # GeoJSON-like
        features = ors_json.get("features", [])

    route_summaries = []
    for i, feat in enumerate(features, start=1):
        coords = feat.get("geometry", {}).get("coordinates", [])
        if not coords:
            continue

        sampled = sample_polyline(coords, step_m=300)
        waypoint_preds = []

        for lat, lon in sampled:
            # Prefer DB data, fallback to OWM
            station_id = find_nearest_station(lat, lon)
            latest = get_latest_from_db(db, station_id)

            if latest is None:
                owm_key = f"owm:{round(lat,4)}:{round(lon,4)}"
                latest = get_cache(owm_key)
                if latest is None:
                    try:
                        j = call_owm(db, lat, lon)
                        comp = j.get("list", [{}])[0].get("components", {})
                        latest = {
                            "pm2_5": comp.get("pm2_5"),
                            "pm10": comp.get("pm10"),
                            "no2": comp.get("no2"),
                            "co": comp.get("co"),
                            "o3": comp.get("o3"),
                        }
                        set_cache(owm_key, latest, ttl=600)
                    except Exception:
                        logger.exception("OWM call failed for %s,%s", lat, lon)
                        latest = None

            if latest is None:
                continue

            # Build feature vector
            vec = []
            for col in feature_cols:
                val = latest.get(col) or latest.get(col.replace(".", "_")) or latest.get(col.lower()) or 0.0
                try:
                    vec.append(float(val))
                except Exception:
                    vec.append(0.0)

            try:
                preds = predict_from_vector(vec)
            except Exception:
                logger.exception("Prediction failed for waypoint %s,%s", lat, lon)
                preds = [None]

            waypoint_preds.append({"lat": lat, "lon": lon, "station": station_id, "pred": preds})

        # Aggregate forecasts
        valid_preds = [w["pred"] for w in waypoint_preds if w["pred"] and w["pred"][0] is not None]
        if not valid_preds:
            continue

        arr = np.array(valid_preds)
        mean_forecast = arr.mean(axis=0).tolist()
        max_forecast = arr.max(axis=0).tolist()

        route_summaries.append({
            "route_index": i,
            "avg_forecast_pm2_5": mean_forecast,
            "max_forecast_pm2_5": max_forecast,
            "waypoints": len(waypoint_preds),
        })

    # ----------------------------------------------------------------
    # Alerting
    # ----------------------------------------------------------------
    threshold = float(os.getenv("POLLUTION_ALERT_THRESHOLD", "150"))
    for r in route_summaries:
        maxv = r.get("max_forecast_pm2_5", [])
        if maxv and maxv[0] and maxv[0] > threshold:
            officer = os.getenv("ALERT_OFFICER_EMAIL")
            if officer:
                subject = f"High pollution alert: route {r['route_index']}"
                content = f"Predicted PM2.5 peak: {maxv[0]:.1f}\nRoute waypoints: {r['waypoints']}"
                if bg:
                    bg.add_task(send_alert_email, officer, subject, content)
                else:
                    send_alert_email(officer, subject, content)

    # ----------------------------------------------------------------
    # Gemini summary
    # ----------------------------------------------------------------
    prompt_lines = []
    for r in route_summaries:
        v = r.get("avg_forecast_pm2_5", [])
        prompt_lines.append(f"Route {r['route_index']}: avg1={v[0]:.1f}" if v else f"Route {r['route_index']}: avg1=N/A")

    prompt = "Compare routes and recommend best and whether to delay.\n" + "\n".join(prompt_lines)
    gemini_summary = call_gemini(prompt)

    return {"routes": route_summaries, "gemini_summary": gemini_summary}
