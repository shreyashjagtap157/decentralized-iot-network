from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, Enum as SQLAlchemyEnum, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum
import os

# Database URL - convert to async driver
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
# Convert postgresql:// to postgresql+asyncpg:// for async support
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif DATABASE_URL.startswith("postgres://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Async engine with connection pooling
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=False,  # Set True for SQL debugging
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

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

async def get_db():
    """Async database session dependency"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

