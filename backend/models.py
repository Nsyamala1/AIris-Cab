from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class TrackedRoute(Base):
    __tablename__ = "tracked_routes"
    
    id = Column(Integer, primary_key=True, index=True)
    pickup = Column(String)
    dropoff = Column(String)
    passenger_count = Column(Integer, default=1)
    phone_number = Column(String)  # Store phone number in E.164 format (+1XXXXXXXXXX)
    target_price = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer)
    service = Column(String)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

# SQLite database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./price_tracker.db"

# Create engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)
