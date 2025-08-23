# backend/app/api_quota.py
from datetime import date
from functools import wraps
import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session
import os

from .database import SessionLocal
from .models import APIUsage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# config from env (safe defaults)
DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", "90"))
API_LIMITS = {
    "openweathermap": int(os.getenv("OPENWEATHER_DAILY_LIMIT", "500")),
    "openrouteservice": int(os.getenv("OPENROUTESERVICE_DAILY_LIMIT", "800")),
    "sendgrid": int(os.getenv("SENDGRID_DAILY_LIMIT", "90")),
}
CRITICAL_APIS = set(["openweathermap", "openrouteservice"])
WARN_THRESHOLD = 0.8

def get_today():
    return date.today()

def check_and_increment(db: Session, api_name: str) -> bool:
    limit = API_LIMITS.get(api_name, DEFAULT_LIMIT)
    today = get_today()
    row = db.query(APIUsage).filter(APIUsage.api_name == api_name, APIUsage.date == today).first()
    if row is None:
        row = APIUsage(api_name=api_name, date=today, count=1)
        db.add(row)
        db.commit()
        return True
    if row.count >= limit:
        return False
    row.count += 1
    db.add(row)
    db.commit()
    return True

def get_usage(db: Session, api_name: str) -> int:
    today = get_today()
    row = db.query(APIUsage).filter(APIUsage.api_name == api_name, APIUsage.date == today).first()
    return row.count if row else 0

def any_critical_exhausted(db: Session) -> bool:
    today = get_today()
    for api in CRITICAL_APIS:
        limit = API_LIMITS.get(api, DEFAULT_LIMIT)
        row = db.query(APIUsage).filter(APIUsage.api_name == api, APIUsage.date == today).first()
        if row and row.count >= limit:
            return True
    return False

def check_system_enabled(db: Session):
    if any_critical_exhausted(db):
        raise HTTPException(status_code=503, detail="A critical API daily limit reached. Service disabled for today.")
    return True

def guard_api(api_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            db = kwargs.get("db", None)
            if db is None:
                for a in args:
                    if hasattr(a, "query"):
                        db = a
                        break
            if db is None:
                logger.error("DB session not provided to guard_api for %s", api_name)
                raise HTTPException(status_code=500, detail="Server misconfiguration: DB not provided to quota guard")

            allowed = check_and_increment(db, api_name)
            if not allowed:
                logger.info("%s quota exhausted", api_name)
                raise HTTPException(status_code=429, detail=f"Daily limit reached for {api_name}")

            limit = API_LIMITS.get(api_name, DEFAULT_LIMIT)
            used = get_usage(db, api_name)
            if used >= int(limit * WARN_THRESHOLD):
                logger.warning("%s usage at %d/%d (>= %.0f%%)", api_name, used, limit, WARN_THRESHOLD*100)

            return func(*args, **kwargs)
        return wrapper
    return decorator
