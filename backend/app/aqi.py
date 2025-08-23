# backend/app/aqi.py
import os, requests
from typing import Optional, Dict
from dotenv import load_dotenv
from pathlib import Path

# ensure env loaded
project_root = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=project_root / ".env")

OWM_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

def fetch_owm_point(lat: float, lon: float, timeout=8) -> Optional[Dict]:
    """
    Returns dict with components or None
    """
    if not OWM_KEY:
        return None
    url = "http://api.openweathermap.org/data/2.5/air_pollution"
    resp = requests.get(url, params={"lat": lat, "lon": lon, "appid": OWM_KEY}, timeout=timeout)
    resp.raise_for_status()
    j = resp.json()
    if "list" in j and len(j["list"])>0:
        comp = j["list"][0]["components"]
        return comp
    return None
