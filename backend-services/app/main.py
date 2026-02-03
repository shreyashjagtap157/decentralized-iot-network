

import logging
import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .api import devices, usage, auth, websockets, users, analytics, enterprise, staking, governance, bridge, nft, batch
from app.core.exceptions import register_exception_handlers
from app.services.mqtt_service import mqtt_service
from app.core.performance import profiler, measure_time
from app.core.database_optimization import DatabaseConnectionPooling, N_PlusOneQueryDetector
from passlib.context import CryptContext

# Import IoT enhancements
try:
    from edge.edge_computing import EdgeComputingCluster
    from blockchain.audit_trail import AuditTrailManager, AuditEvent, EventType
    from optimization.capacity_planner import CapacityOptimizer
    IOT_ENHANCEMENTS_AVAILABLE = True
except ImportError:
    IOT_ENHANCEMENTS_AVAILABLE = False

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Decentralized IoT Network API",
    description="Backend API for IoT device management, analytics, and blockchain rewards",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
register_exception_handlers(app)

# Initialize IoT enhancements
edge_cluster = None
audit_trail_manager = None
capacity_optimizer = None

def initialize_iot_enhancements():
    """Initialize edge computing, audit trail, and capacity planner."""
    global edge_cluster, audit_trail_manager, capacity_optimizer
    
    if not IOT_ENHANCEMENTS_AVAILABLE:
        logger.warning("IoT enhancements not available")
        return
    
    try:
        import yaml
        from pathlib import Path
        
        config_path = Path(__file__).parent.parent.parent / "config" / "backend.yaml"
        config = {}
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
        
        # Initialize edge computing cluster
        if config.get("edge_computing", {}).get("enabled", False):
            try:
                kafka_brokers = config.get("edge_computing", {}).get("kafka_brokers", ["localhost:9092"])
                edge_cluster = EdgeComputingCluster(
                    cluster_id=config.get("edge_computing", {}).get("cluster_id", "iot-edge-1"),
                    max_nodes=config.get("edge_computing", {}).get("max_nodes", 10),
                    kafka_brokers=kafka_brokers
                )
                logger.info("Edge computing cluster initialized")
            except Exception as e:
                logger.error(f"Failed to initialize edge cluster: {e}")
        
        # Initialize audit trail
        if config.get("audit_trail", {}).get("enabled", False):
            try:
                audit_trail_manager = AuditTrailManager(
                    db_path=config.get("audit_trail", {}).get("db_path", "./audit_trail.db"),
                    smart_contract_address=config.get("audit_trail", {}).get("smart_contract_address")
                )
                logger.info("Audit trail manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize audit trail: {e}")
        
        # Initialize capacity planner
        if config.get("capacity_planning", {}).get("enabled", False):
            try:
                capacity_optimizer = CapacityOptimizer(
                    replan_interval=config.get("capacity_planning", {}).get("replan_interval_hours", 1) * 3600,
                    cost_per_cpu_hour=config.get("capacity_planning", {}).get("cost_per_cpu_hour", 0.10),
                    cost_per_gb_month=config.get("capacity_planning", {}).get("cost_per_gb_memory_month", 5.0)
                )
                logger.info("Capacity optimizer initialized")
            except Exception as e:
                logger.error(f"Failed to initialize capacity optimizer: {e}")
    
    except Exception as e:
        logger.error(f"Error initializing IoT enhancements: {e}")

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

# Attach enhancement references to app state
app.state.edge_cluster = edge_cluster
app.state.audit_trail_manager = audit_trail_manager
app.state.capacity_optimizer = capacity_optimizer



# --- Check bcrypt backend availability at startup ---
@app.on_event("startup")
async def check_bcrypt_backend():
    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        pwd_context.hash("testpass123")
    except Exception as e:
        logger.error(f"Bcrypt backend error: {e}")
        raise RuntimeError("Bcrypt backend is not available or misconfigured. Please check your bcrypt/passlib installation.")
    
    # Initialize IoT enhancements on startup
    initialize_iot_enhancements()
    
    # Start edge cluster if available
    if edge_cluster:
        try:
            await edge_cluster.initialize()
            logger.info("Edge cluster initialized on startup")
        except Exception as e:
            logger.warning(f"Failed to initialize edge cluster on startup: {e}")
    
    # Start audit trail if available
    if audit_trail_manager:
        try:
            await audit_trail_manager.initialize()
            logger.info("Audit trail initialized on startup")
        except Exception as e:
            logger.warning(f"Failed to initialize audit trail on startup: {e}")
    
    # Start capacity planner if available
    if capacity_optimizer:
        try:
            await capacity_optimizer.start()
            logger.info("Capacity planner started on startup")
        except Exception as e:
            logger.warning(f"Failed to start capacity planner on startup: {e}")


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
app.include_router(batch.router)



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
    
    # Shutdown IoT enhancements
    if edge_cluster:
        try:
            await edge_cluster.shutdown()
            logger.info("Edge cluster shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down edge cluster: {e}")
    
    if audit_trail_manager:
        try:
            await audit_trail_manager.shutdown()
            logger.info("Audit trail shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down audit trail: {e}")
    
    if capacity_optimizer:
        try:
            await capacity_optimizer.stop()
            logger.info("Capacity planner shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down capacity planner: {e}")


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
