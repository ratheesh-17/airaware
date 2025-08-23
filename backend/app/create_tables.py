# backend/app/create_tables.py
import logging
from .database import Base, engine
from . import models

logger = logging.getLogger(__name__)

def create_all_tables():
    Base.metadata.create_all(bind=engine)
    logger.info("✅ All tables created successfully.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_all_tables()
