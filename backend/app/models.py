# backend/app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Date
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    preferences = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RouteData(Base):
    __tablename__ = "routes"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    route_geojson = Column(Text, nullable=False)
    aqi = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class PredictionData(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String(255), nullable=False)
    predicted_aqi = Column(Float, nullable=False)
    prediction_time = Column(DateTime(timezone=True), server_default=func.now())

class LatestReading(Base):
    __tablename__ = "latest_readings"
    station_id = Column(String(64), primary_key=True)
    pm2_5 = Column(Float)
    pm10 = Column(Float)
    no2 = Column(Float)
    co = Column(Float)
    o3 = Column(Float)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class APIUsage(Base):
    __tablename__ = "api_usage"
    api_name = Column(String(64), primary_key=True)
    date = Column(Date, primary_key=True)
    count = Column(Integer, default=0)

