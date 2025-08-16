# backend/app/predict_route.py
from fastapi import APIRouter, Depends, HTTPException
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# config
DATASETS_DIR = Path(__file__).resolve().parents[1] / "datasets"
STATIONS_CSV = DATASETS_DIR / "station.csv"

# Load station metadata safely and ensure lat/lon are floats
if STATIONS_CSV.exists():
    try:
        stations_meta = pd.read_csv(STATIONS_CSV)
        stations_meta.columns = [c.strip() for c in stations_meta.columns]
        # ensure latitude/longitude exist and are floats
        if "latitude" in stations_meta.columns and "longitude" in stations_meta.columns:
            stations_meta["latitude"] = stations_meta["latitude"].astype(float)
            stations_meta["longitude"] = stations_meta["longitude"].astype(float)
        else:
            # fallback to empty df with expected columns
            stations_meta = pd.DataFrame(columns=["station_id", "latitude", "longitude"])
    except Exception as e:
        logger.exception("Failed to load station CSV: %s", e)
        stations_meta = pd.DataFrame(columns=["station_id", "latitude", "longitude"])
else:
    stations_meta = pd.DataFrame(columns=["station_id", "latitude", "longitude"])


def haversine(lat1, lon1, lat2, lon2):
    """Return distance in meters between two lat/lon points."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def find_nearest_station(lat, lon):
    """Return (station_id, distance_m) or (None, None) if no stations."""
    if stations_meta.empty:
        return None, None
    # compute distances vectorized is faster, but keep readability
    dists = stations_meta.apply(lambda r: haversine(lat, lon, r["latitude"], r["longitude"]), axis=1)
    idx = dists.idxmin()
    return stations_meta.loc[idx, "station_id"], float(dists.loc[idx])


def sample_polyline(coords, step_m=300):
    """
    coords: list of [lon, lat] pairs (GeoJSON order)
    returns list of (lat, lon) sampled approximately every step_m meters along the polyline
    """
    sampled = []

    def segdist(a, b):
        # a and b are [lon, lat]
        return haversine(a[1], a[0], b[1], b[0])

    for i in range(len(coords) - 1):
        a = coords[i]
        b = coords[i + 1]
        seglen = segdist(a, b)
        if seglen == 0:
            continue
        # number of samples excluding the endpoint; ensure at least one step if segment long
        n = max(1, int(seglen // step_m))
        for s in range(n):
            t = s / n
            lon = a[0] + (b[0] - a[0]) * t
            lat = a[1] + (b[1] - a[1]) * t
            sampled.append((lat, lon))
    # include final endpoint
    if coords:
        sampled.append((coords[-1][1], coords[-1][0]))
    return sampled


# ---------------------------
# Cached model loader (load once)
# ---------------------------
_model_cache = None
_feature_cols_cache = None


def get_model():
    global _model_cache, _feature_cols_cache
    if _model_cache is None or _feature_cols_cache is None:
        _model_cache, _feature_cols_cache = load_model()
    return _model_cache, _feature_cols_cache


# ---------------------------
# External API wrappers (guarded by quota)
# ---------------------------

@guard_api("openrouteservice")
def call_ors(db: Session, s_lat, s_lon, d_lat, d_lon):
    ORS_KEY = os.getenv("OPENROUTESERVICE_API_KEY")
    if not ORS_KEY:
        raise HTTPException(status_code=500, detail="ORS key not configured")
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    body = {
        "coordinates": [[s_lon, s_lat], [d_lon, d_lat]],
        "instructions": False,
        "alternative_routes": {"share_factor": 0.6, "target_count": 3},
    }
    headers = {"Authorization": ORS_KEY, "Content-Type": "application/json"}
    resp = requests.post(url, json=body, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


@guard_api("openweathermap")
def call_owm(db: Session, lat, lon):
    OWM_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
    if not OWM_KEY:
        raise HTTPException(status_code=500, detail="OWM key not configured")
    url = "http://api.openweathermap.org/data/2.5/air_pollution"
    r = requests.get(url, params={"lat": lat, "lon": lon, "appid": OWM_KEY}, timeout=10)
    r.raise_for_status()
    return r.json()


# helper: get latest reading from DB table latest_readings
def get_latest_from_db(db: Session, station_id: str):
    if station_id is None:
        return None
    try:
        row = db.execute(
            text("SELECT station_id, pm2_5, pm10, no2, co, o3 FROM latest_readings WHERE station_id = :sid"),
            {"sid": station_id},
        ).first()
        if row:
            # SQLAlchemy Row -> mapping
            return dict(row._mapping)
    except Exception:
        logger.exception("DB query failed for station %s", station_id)
    return None


@router.post("/predict-route")
def predict_route(payload: dict, db: Session = Depends(get_db)):
    """
    payload example:
    {
      "source": "12.34,56.78",
      "destination": "12.35,56.79"
    }
    """
    # Ensure system not disabled due to critical quota exhaustion
    check_system_enabled(db)

    # parse payload
    try:
        s_lat, s_lon = map(float, payload["source"].split(","))
        d_lat, d_lon = map(float, payload["destination"].split(","))
    except Exception:
        raise HTTPException(status_code=400, detail="source/destination must be 'lat,lon'")

    # load model once
    model, feature_cols = get_model()

    # ORS with caching
    ors_key = f"ors:{s_lat:.6f}:{s_lon:.6f}:{d_lat:.6f}:{d_lon:.6f}"
    ors_json = get_cache(ors_key)
    if ors_json is None:
        try:
            ors_json = call_ors(db=db, s_lat=s_lat, s_lon=s_lon, d_lat=d_lat, d_lon=d_lon)
            set_cache(ors_key, ors_json, ttl=600)
        except HTTPException as e:
            raise e
        except Exception:
            logger.exception("ORS call failed")
            raise HTTPException(status_code=502, detail="Route provider failed")

    # ORS may return either 'features' (GeoJSON) or 'routes' (some variants).
    if "features" in ors_json:
        features = ors_json.get("features", [])
    elif "routes" in ors_json:
        # convert routes into a list of pseudo-features with geometry coordinates if possible
        features = []
        for r in ors_json.get("routes", []):
            geom = r.get("geometry")
            if isinstance(geom, dict) and "coordinates" in geom:
                features.append({"geometry": geom})
            elif isinstance(geom, str):
                # some responses are encoded polylines — leave handling to caller; skip
                continue
    else:
        features = []

    route_summaries = []
    for i, feat in enumerate(features, start=1):
        coords = feat.get("geometry", {}).get("coordinates", [])
        if not coords:
            continue

        sampled = sample_polyline(coords, step_m=300)
        waypoint_preds = []

        for lat, lon in sampled:
            station_id, dist = find_nearest_station(lat, lon)
            latest = get_latest_from_db(db, station_id)
            if latest is None:
                # try cached OWM
                owm_key = f"owm:{round(lat,4)}:{round(lon,4)}"
                cached = get_cache(owm_key)
                if cached is None:
                    try:
                        j = call_owm(db=db, lat=lat, lon=lon)
                        # extract components safely
                        comp = j.get("list", [{}])[0].get("components", {})
                        latest = {
                            "pm2_5": comp.get("pm2_5"),
                            "pm10": comp.get("pm10"),
                            "no2": comp.get("no2"),
                            "co": comp.get("co"),
                            "o3": comp.get("o3"),
                        }
                        set_cache(owm_key, latest, ttl=600)
                    except HTTPException:
                        latest = None
                    except Exception:
                        logger.exception("OWM call failed for %s,%s", lat, lon)
                        latest = None
                else:
                    latest = cached

            if latest is None:
                # unable to obtain environmental reading for this waypoint
                continue

            # build feature vector in same order as feature_columns
            vec = []
            for col in feature_cols:
                val = None
                # tolerant mapping
                if col in latest:
                    val = latest[col]
                elif col.replace(".", "_") in latest:
                    val = latest[col.replace(".", "_")]
                elif col.lower() in latest:
                    val = latest[col.lower()]
                else:
                    val = 0.0
                try:
                    vec.append(float(val) if val is not None else 0.0)
                except Exception:
                    vec.append(0.0)

            # predict
            try:
                preds = predict_from_vector(vec)  # expected list/array
            except Exception:
                logger.exception("Prediction failed for waypoint %s,%s", lat, lon)
                preds = [None]

            waypoint_preds.append({"lat": lat, "lon": lon, "station": station_id, "pred": preds})

        if not waypoint_preds:
            # no waypoints with predictions for this route
            continue

        # build numpy array safely: filter out None entries
        valid_preds = [w["pred"] for w in waypoint_preds if w["pred"] and w["pred"][0] is not None]
        if not valid_preds:
            continue
        arr = np.array(valid_preds)
        if arr.size == 0:
            continue

        # mean and max along axis 0
        mean_forecast = arr.mean(axis=0).tolist()
        max_forecast = arr.max(axis=0).tolist()
        route_summaries.append(
            {
                "route_index": i,
                "avg_forecast_pm2_5": mean_forecast,
                "max_forecast_pm2_5": max_forecast,
                "waypoints": len(waypoint_preds),
            }
        )

    # Compose compact Gemini prompt & call (placeholder)
    prompt_lines = []
    for r in route_summaries:
        v = r.get("avg_forecast_pm2_5", [])
        first = f"{v[0]:.1f}" if v and len(v) > 0 else "N/A"
        prompt_lines.append(f"Route {r['route_index']}: avg1={first}")

    prompt = "Compare routes and recommend best and whether to delay.\n" + "\n".join(prompt_lines)
    gemini_summary = call_gemini(prompt)

    return {"routes": route_summaries, "gemini_summary": gemini_summary}
