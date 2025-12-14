from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Enum as SQLAlchemyEnum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DeviceStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"

class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


from sqlalchemy.dialects.postgresql import UUID
import uuid

class Device(Base):
    """
    SQLAlchemy model for IoT device records.
    """
    __tablename__ = "devices"
    device_id = Column(String, primary_key=True, index=True)
    device_type = Column(String)
    owner_address = Column(String)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    hashed_signature = Column(String, nullable=True)
    status = Column(SQLAlchemyEnum(DeviceStatus), default=DeviceStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime, nullable=True)


class NetworkUsage(Base):
    """
    SQLAlchemy model for network usage records.
    """
    __tablename__ = "network_usage"
    usage_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String, ForeignKey("devices.device_id"), index=True)
    bytes_transmitted = Column(Integer)
    bytes_received = Column(Integer)
    connection_quality = Column(Integer)
    user_sessions = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    compensated = Column(Boolean, default=False)


class CompensationTransaction(Base):
    """
    SQLAlchemy model for compensation transaction records.
    Tracks blockchain transactions for device usage compensation.
    """
    __tablename__ = "compensation_transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String, ForeignKey("devices.device_id"), index=True)
    owner_address = Column(String, index=True)
    usage_period_start = Column(DateTime)
    usage_period_end = Column(DateTime)
    total_bytes = Column(Integer)
    average_quality = Column(Float)
    reward_amount = Column(Float, nullable=True)
    blockchain_tx_hash = Column(String, unique=True, nullable=True)
    status = Column(SQLAlchemyEnum(TransactionStatus), default=TransactionStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class User(Base):
    """
    SQLAlchemy model for user accounts.
    """
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
