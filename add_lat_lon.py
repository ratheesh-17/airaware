import pandas as pd
import requests
import time

# Path to your CSV
CSV_PATH = "datasets/stations.csv"

# Load your station data
df = pd.read_csv(CSV_PATH)

# Add empty latitude and longitude columns if not present
if "latitude" not in df.columns:
    df["latitude"] = None
if "longitude" not in df.columns:
    df["longitude"] = None

# Function to fetch coordinates from OpenStreetMap (Nominatim)
def get_coordinates(station_name, city, state):
    query = f"{station_name}, {city}, {state}, India"
    url = f"https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1
    }
    headers = {"User-Agent": "airaware-app"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"Error fetching {query}: {e}")
    return None, None

# Loop through stations and fill coordinates
for idx, row in df.iterrows():
    if pd.isna(row["latitude"]) or pd.isna(row["longitude"]):
        lat, lon = get_coordinates(row["StationName"], row["City"], row["State"])
        df.at[idx, "latitude"] = lat
        df.at[idx, "longitude"] = lon
        print(f"Fetched: {row['StationName']} -> {lat}, {lon}")
        time.sleep(1)  # Be nice to OSM, avoid rate-limits

# Save updated CSV
df.to_csv(CSV_PATH, index=False)
print("✅ Updated CSV with latitude & longitude!")
