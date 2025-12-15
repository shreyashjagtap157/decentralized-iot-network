

import logging
import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .api import devices, usage, auth, websockets, users, analytics, enterprise, staking, governance, bridge, nft
from app.core.exceptions import register_exception_handlers
from app.services.mqtt_service import mqtt_service
from app.core.performance import profiler, measure_time
from app.core.database_optimization import DatabaseConnectionPooling, N_PlusOneQueryDetector
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Decentralized IoT Network API",
    description="Backend API for IoT device management, analytics, and blockchain rewards",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
register_exception_handlers(app)

# --- CORS Configuration ---
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "https://iot-network.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Production Middleware Stack ---
from app.core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware, RequestLoggingMiddleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

from prometheus_fastapi_instrumentator import Instrumentator
from app.core.config import settings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
import sys

# --- Configure Structlog for JSON Logs ---
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() 
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

# --- Rate Limiting Setup ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if settings.PROMETHEUS_METRICS:
    Instrumentator().instrument(app).expose(app)




# --- Check bcrypt backend availability at startup ---
@app.on_event("startup")
async def check_bcrypt_backend():
    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        pwd_context.hash("testpass123")
    except Exception as e:
        logger.error(f"Bcrypt backend error: {e}")
        raise RuntimeError("Bcrypt backend is not available or misconfigured. Please check your bcrypt/passlib installation.")



# Register routers as usual
app.include_router(devices.router)
app.include_router(usage.router)
app.include_router(auth.router)
app.include_router(websockets.router)
app.include_router(users.router)
app.include_router(analytics.router)
app.include_router(enterprise.router)
app.include_router(staking.router)
app.include_router(governance.router)
app.include_router(bridge.router)
app.include_router(nft.router)



# Initialize N+1 Query Detector
n_plus_one_detector = N_PlusOneQueryDetector()

# Example usage of profiling and optimization utilities
@profiler.profile_function
def example_function():
    with measure_time("Example Operation"):
        # Simulate some operation
        pass

# Apply connection pooling configuration
connection_pool_config = DatabaseConnectionPooling.tune_for_high_load()
# Log the configuration for debugging
logger.info(f"Connection Pool Config: {connection_pool_config}")

# Enable N+1 query detection (example session setup)
# session = Session()  # Replace with actual session
# n_plus_one_detector.detect_n_plus_one(session)


# Patch MQTT service for test environment to avoid connection errors
if os.environ.get("PYTEST_CURRENT_TEST"):
    async def _noop():
        pass
    mqtt_service.connect = _noop
    mqtt_service.disconnect = _noop

@app.on_event("startup")
async def startup_event():
    await mqtt_service.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await mqtt_service.disconnect()

@app.get("/health")
async def health_check():
    """
    Deep health check endpoint that verifies connectivity to all dependent services.
    Returns detailed status for monitoring systems.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Database check
    try:
        from app.db.models import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_status["checks"]["database"] = {"status": "up"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "down", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Redis check (optional)
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        r.ping()
        health_status["checks"]["redis"] = {"status": "up"}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "down", "error": str(e)}
        # Redis is optional, don't set degraded
    
    # MQTT check
    health_status["checks"]["mqtt"] = {
        "status": "up" if mqtt_service._client else "down"
    }
    
    return health_status

from datetime import datetime
