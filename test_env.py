import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

api_key = os.getenv("OPENROUTESERVICE_API_KEY")

if api_key:
    print("✅ API Key loaded successfully!")
    print("Key:", api_key[:10] + "..." + api_key[-5:])  # only partial for safety
else:
    print("❌ API Key not found. Check .env file location.")
