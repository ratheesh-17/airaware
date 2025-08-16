from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()  # load .env in backend/

app = FastAPI(title="AirAware Backend")

# include routers
from .predict_route import router as predict_router
app.include_router(predict_router)

@app.get("/health")
def health():
    return {"status": "ok"}
