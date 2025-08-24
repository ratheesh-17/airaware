import requests
import pandas as pd
from pathlib import Path
import time

# Your API Key here
API_KEY = "2b8a81b2643e650da9c9ba9717c1cdf1bf5a0bc250dbae0e24448c7688cdf258"

# Output file path
DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
DATASETS_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = DATASETS_DIR / "stations_with_coordinates.csv"

# API endpoint
URL = "https://api.openaq.org/v3/locations"

def fetch_all_stations():
    print("📡 Fetching ALL station data from OpenAQ API...")
    headers = {"X-API-Key": API_KEY}
    params = {
        "country_id": "IN",  # Correct param for v3
        "limit": 1000,       # Max per request
        "page": 1
    }

    all_results = []
    while True:
        try:
            print(f"🔄 Fetching page {params['page']}...")
            response = requests.get(URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                print("✅ No more data found.")
                break

            all_results.extend(results)
            print(f"📥 Retrieved {len(results)} records (Total: {len(all_results)})")

            meta = data.get("meta", {})
            if not meta.get("found") or len(results) < params["limit"]:
                break

            params["page"] += 1
            time.sleep(1)  # Avoid rate limits

        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            break

    if all_results:
        df = pd.json_normalize(all_results)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ Saved {len(df)} stations to {OUTPUT_FILE}")
    else:
        print("⚠️ No data fetched!")

if __name__ == "__main__":
    fetch_all_stations()
