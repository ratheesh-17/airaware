import os
import requests
from dotenv import load_dotenv

# Load .env
load_dotenv()
API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")

# Base URL for Directions API
url = "https://api.openrouteservice.org/v2/directions/driving-car"

# Example coordinates: [lng, lat]
# Start: Berlin Brandenburg Gate
start = [13.377704, 52.516275]
# End: Berlin Central Station
end = [13.369545, 52.525084]

# Request body
body = {
    "coordinates": [start, end]
}

headers = {
    "Authorization": API_KEY,
    "Content-Type": "application/json"
}

response = requests.post(url, json=body, headers=headers)

if response.status_code == 200:
    data = response.json()
    distance = data["routes"][0]["summary"]["distance"] / 1000  # in km
    duration = data["routes"][0]["summary"]["duration"] / 60   # in minutes
    print(f"Distance: {distance:.2f} km")
    print(f"Duration: {duration:.2f} min")
else:
    print("Error:", response.status_code, response.text)
