# backend/app/scripts/populate_latest_readings.py
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import math
from sqlalchemy import text  # <-- important for raw SQL

# Relative imports
from ..database import SessionLocal, engine
from ..models import LatestReading  # or correct class name

# Load .env from project root
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# For testing — limit stations
LIMIT_STATIONS = 50  # None to load all stations

# Path to CSV (adjust if needed)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = PROJECT_ROOT / "datasets" / "station_hour.csv"

if not CSV_PATH.exists():
    raise FileNotFoundError(f"station_hour.csv not found at {CSV_PATH}")

def safe_float(val):
    """Convert NaN or None to None, otherwise float."""
    if val is None:
        return None
    try:
        if math.isnan(val):
            return None
    except TypeError:
        pass
    return float(val)

def populate_latest_from_station_hour(limit=LIMIT_STATIONS):
    print("Reading CSV:", CSV_PATH)
    usecols = ["StationId", "Datetime", "PM2.5", "PM10", "NO2", "CO", "O3"]
    df_iter = pd.read_csv(CSV_PATH, usecols=usecols, parse_dates=["Datetime"], chunksize=200000)

    latest = {}

    for chunk in df_iter:
        if limit:
            unique_ids = set(latest.keys())
            for _, row in chunk.iterrows():
                sid = row["StationId"]
                if limit and len(unique_ids) >= limit and sid not in unique_ids:
                    continue
                dt = row["Datetime"]
                if (sid not in latest) or (pd.to_datetime(latest[sid]["Datetime"]) < pd.to_datetime(dt)):
                    latest[sid] = {
                        "Datetime": dt,
                        "PM2.5": row.get("PM2.5", None),
                        "PM10": row.get("PM10", None),
                        "NO2": row.get("NO2", None),
                        "CO": row.get("CO", None),
                        "O3": row.get("O3", None)
                    }
                unique_ids = set(latest.keys())
        else:
            for _, row in chunk.iterrows():
                sid = row["StationId"]
                dt = row["Datetime"]
                if (sid not in latest) or (pd.to_datetime(latest[sid]["Datetime"]) < pd.to_datetime(dt)):
                    latest[sid] = {
                        "Datetime": dt,
                        "PM2.5": row.get("PM2.5", None),
                        "PM10": row.get("PM10", None),
                        "NO2": row.get("NO2", None),
                        "CO": row.get("CO", None),
                        "O3": row.get("O3", None)
                    }

    print("Stations to insert:", len(latest))

    db = SessionLocal()
    inserted = 0
    try:
        for sid, row in latest.items():
            dt = pd.to_datetime(row["Datetime"]).to_pydatetime()
            record = db.execute(
                text("SELECT station_id FROM latest_readings WHERE station_id = :sid"),
                {"sid": str(sid)}
            ).first()

            if record:
                db.execute(
                    text("""
                        UPDATE latest_readings
                        SET pm2_5 = :pm2_5, pm10 = :pm10, no2 = :no2, co = :co, o3 = :o3, updated_at = :updated_at
                        WHERE station_id = :sid
                    """),
                    {
                        "pm2_5": safe_float(row["PM2.5"]),
                        "pm10": safe_float(row["PM10"]),
                        "no2": safe_float(row["NO2"]),
                        "co": safe_float(row["CO"]),
                        "o3": safe_float(row["O3"]),
                        "updated_at": dt,
                        "sid": str(sid)
                    }
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO latest_readings (station_id, pm2_5, pm10, no2, co, o3, updated_at)
                        VALUES (:sid, :pm2_5, :pm10, :no2, :co, :o3, :updated_at)
                    """),
                    {
                        "sid": str(sid),
                        "pm2_5": safe_float(row["PM2.5"]),
                        "pm10": safe_float(row["PM10"]),
                        "no2": safe_float(row["NO2"]),
                        "co": safe_float(row["CO"]),
                        "o3": safe_float(row["O3"]),
                        "updated_at": dt
                    }
                )
            inserted += 1

        db.commit()
        print(f"Inserted/Updated {inserted} latest_readings rows.")
    except Exception as e:
        db.rollback()
        print("Error inserting:", e)
    finally:
        db.close()

if __name__ == "__main__":
    populate_latest_from_station_hour()
