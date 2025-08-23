# backend/app/main.py
from fastapi import FastAPI
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
project_root = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=project_root / ".env")

app = FastAPI(title="AirAware Backend")

# include routers (relative import)
from .predict_route import router as predict_router
app.include_router(predict_router)

@app.get("/health")
def health():
    return {"status": "ok"}

