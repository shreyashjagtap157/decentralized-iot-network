"""
Time-Series Database Integration for IoT

Provides TimescaleDB integration with hypertables, retention policies,
and continuous aggregates for efficient IoT sensor data storage.

Features:
- TimescaleDB hypertable management
- Automatic data compression and retention
- Continuous aggregates for real-time analytics
- Efficient time-range queries
- Multi-tenant data isolation
- Downsampling and rollup policies
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncGenerator, Optional

import asyncpg
from asyncpg import Pool

logger = logging.getLogger(__name__)


class AggregationInterval(Enum):
    """Aggregation time intervals"""
    SECOND = "1 second"
    MINUTE = "1 minute"
    FIVE_MINUTES = "5 minutes"
    FIFTEEN_MINUTES = "15 minutes"
    HOUR = "1 hour"
    DAY = "1 day"
    WEEK = "1 week"
    MONTH = "1 month"


class RetentionPolicy(Enum):
    """Data retention policies"""
    RAW_7_DAYS = 7
    RAW_30_DAYS = 30
    RAW_90_DAYS = 90
    AGGREGATED_1_YEAR = 365
    AGGREGATED_FOREVER = -1


class CompressionPolicy(Enum):
    """Compression policies"""
    COMPRESS_AFTER_1_DAY = "1 day"
    COMPRESS_AFTER_7_DAYS = "7 days"
    COMPRESS_AFTER_30_DAYS = "30 days"


@dataclass
class SensorReading:
    """Sensor data reading"""
    device_id: str
    sensor_type: str
    timestamp: datetime
    value: float
    unit: str
    quality: int = 100  # Data quality 0-100
    metadata: dict = None


@dataclass
class AggregatedData:
    """Aggregated sensor data"""
    device_id: str
    sensor_type: str
    bucket_time: datetime
    avg_value: float
    min_value: float
    max_value: float
    sum_value: float
    count: int
    stddev: float


@dataclass
class TimeSeriesQuery:
    """Time series query parameters"""
    device_ids: list[str]
    sensor_types: Optional[list[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    aggregation: Optional[AggregationInterval] = None
    limit: int = 10000


class TimescaleDBManager:
    """
    TimescaleDB connection and schema management.
    """
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[Pool] = None
    
    async def connect(self, min_size: int = 5, max_size: int = 20):
        """Create connection pool"""
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=min_size,
            max_size=max_size
        )
        logger.info("TimescaleDB connection pool created")
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("TimescaleDB connection pool closed")
    
    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get connection from pool"""
        async with self.pool.acquire() as conn:
            yield conn
    
    async def initialize_schema(self):
        """Initialize TimescaleDB schema with hypertables"""
        async with self.connection() as conn:
            # Enable TimescaleDB extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            
            # Create main sensor data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_data (
                    time TIMESTAMPTZ NOT NULL,
                    device_id TEXT NOT NULL,
                    sensor_type TEXT NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    unit TEXT NOT NULL,
                    quality INTEGER DEFAULT 100,
                    metadata JSONB,
                    PRIMARY KEY (device_id, sensor_type, time)
                );
            """)
            
            # Convert to hypertable
            await conn.execute("""
                SELECT create_hypertable(
                    'sensor_data', 
                    'time',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
            """)
            
            # Create device events table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS device_events (
                    time TIMESTAMPTZ NOT NULL,
                    device_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT,
                    details JSONB,
                    PRIMARY KEY (device_id, time, event_type)
                );
            """)
            
            await conn.execute("""
                SELECT create_hypertable(
                    'device_events', 
                    'time',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
            """)
            
            # Create device status table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS device_status (
                    time TIMESTAMPTZ NOT NULL,
                    device_id TEXT NOT NULL,
                    online BOOLEAN NOT NULL,
                    battery_level INTEGER,
                    signal_strength INTEGER,
                    firmware_version TEXT,
                    last_seen TIMESTAMPTZ,
                    PRIMARY KEY (device_id, time)
                );
            """)
            
            await conn.execute("""
                SELECT create_hypertable(
                    'device_status', 
                    'time',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 hour'
                );
            """)
            
            # Create indexes for common queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sensor_data_device_time 
                ON sensor_data (device_id, time DESC);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sensor_data_type_time 
                ON sensor_data (sensor_type, time DESC);
            """)
            
            logger.info("TimescaleDB schema initialized")
    
    async def create_continuous_aggregate(
        self,
        name: str,
        source_table: str,
        interval: AggregationInterval,
        columns: list[str] = None
    ):
        """Create continuous aggregate for automatic rollups"""
        if columns is None:
            columns = ["device_id", "sensor_type"]
        
        group_by = ", ".join(columns)
        select_cols = ", ".join(columns)
        
        async with self.connection() as conn:
            await conn.execute(f"""
                CREATE MATERIALIZED VIEW IF NOT EXISTS {name}
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('{interval.value}', time) AS bucket,
                    {select_cols},
                    AVG(value) AS avg_value,
                    MIN(value) AS min_value,
                    MAX(value) AS max_value,
                    SUM(value) AS sum_value,
                    COUNT(*) AS count,
                    STDDEV(value) AS stddev
                FROM {source_table}
                GROUP BY bucket, {group_by}
                WITH NO DATA;
            """)
            
            # Add refresh policy
            await conn.execute(f"""
                SELECT add_continuous_aggregate_policy(
                    '{name}',
                    start_offset => INTERVAL '1 week',
                    end_offset => INTERVAL '1 minute',
                    schedule_interval => INTERVAL '1 hour',
                    if_not_exists => TRUE
                );
            """)
            
            logger.info(f"Created continuous aggregate: {name}")
    
    async def set_retention_policy(
        self,
        table_name: str,
        retention_days: int
    ):
        """Set data retention policy"""
        async with self.connection() as conn:
            await conn.execute(f"""
                SELECT add_retention_policy(
                    '{table_name}',
                    INTERVAL '{retention_days} days',
                    if_not_exists => TRUE
                );
            """)
            logger.info(f"Set retention policy for {table_name}: {retention_days} days")
    
    async def set_compression_policy(
        self,
        table_name: str,
        compress_after: str
    ):
        """Enable compression for hypertable"""
        async with self.connection() as conn:
            # Enable compression
            await conn.execute(f"""
                ALTER TABLE {table_name} SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'device_id, sensor_type'
                );
            """)
            
            # Add compression policy
            await conn.execute(f"""
                SELECT add_compression_policy(
                    '{table_name}',
                    INTERVAL '{compress_after}',
                    if_not_exists => TRUE
                );
            """)
            
            logger.info(f"Enabled compression for {table_name}: after {compress_after}")


class SensorDataRepository:
    """
    Repository for sensor data operations.
    """
    
    def __init__(self, db_manager: TimescaleDBManager):
        self.db = db_manager
    
    async def insert_reading(self, reading: SensorReading):
        """Insert single sensor reading"""
        async with self.db.connection() as conn:
            await conn.execute("""
                INSERT INTO sensor_data (time, device_id, sensor_type, value, unit, quality, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (device_id, sensor_type, time) 
                DO UPDATE SET value = EXCLUDED.value, quality = EXCLUDED.quality
            """, 
                reading.timestamp,
                reading.device_id,
                reading.sensor_type,
                reading.value,
                reading.unit,
                reading.quality,
                reading.metadata
            )
    
    async def insert_batch(self, readings: list[SensorReading]):
        """Insert batch of sensor readings efficiently"""
        if not readings:
            return
        
        async with self.db.connection() as conn:
            # Use COPY for efficient bulk insert
            await conn.copy_records_to_table(
                'sensor_data',
                records=[
                    (r.timestamp, r.device_id, r.sensor_type, r.value, r.unit, r.quality, r.metadata)
                    for r in readings
                ],
                columns=['time', 'device_id', 'sensor_type', 'value', 'unit', 'quality', 'metadata']
            )
        
        logger.debug(f"Inserted {len(readings)} sensor readings")
    
    async def query_readings(
        self,
        query: TimeSeriesQuery
    ) -> list[SensorReading]:
        """Query sensor readings with flexible filters"""
        sql = "SELECT time, device_id, sensor_type, value, unit, quality, metadata FROM sensor_data WHERE 1=1"
        params = []
        param_idx = 1
        
        if query.device_ids:
            sql += f" AND device_id = ANY(${param_idx})"
            params.append(query.device_ids)
            param_idx += 1
        
        if query.sensor_types:
            sql += f" AND sensor_type = ANY(${param_idx})"
            params.append(query.sensor_types)
            param_idx += 1
        
        if query.start_time:
            sql += f" AND time >= ${param_idx}"
            params.append(query.start_time)
            param_idx += 1
        
        if query.end_time:
            sql += f" AND time <= ${param_idx}"
            params.append(query.end_time)
            param_idx += 1
        
        sql += " ORDER BY time DESC"
        
        if query.limit:
            sql += f" LIMIT {query.limit}"
        
        async with self.db.connection() as conn:
            rows = await conn.fetch(sql, *params)
        
        return [
            SensorReading(
                device_id=row['device_id'],
                sensor_type=row['sensor_type'],
                timestamp=row['time'],
                value=row['value'],
                unit=row['unit'],
                quality=row['quality'],
                metadata=row['metadata']
            )
            for row in rows
        ]
    
    async def query_aggregated(
        self,
        query: TimeSeriesQuery
    ) -> list[AggregatedData]:
        """Query aggregated sensor data"""
        if not query.aggregation:
            query.aggregation = AggregationInterval.HOUR
        
        sql = f"""
            SELECT 
                time_bucket('{query.aggregation.value}', time) AS bucket,
                device_id,
                sensor_type,
                AVG(value) AS avg_value,
                MIN(value) AS min_value,
                MAX(value) AS max_value,
                SUM(value) AS sum_value,
                COUNT(*) AS count,
                STDDEV(value) AS stddev
            FROM sensor_data
            WHERE 1=1
        """
        params = []
        param_idx = 1
        
        if query.device_ids:
            sql += f" AND device_id = ANY(${param_idx})"
            params.append(query.device_ids)
            param_idx += 1
        
        if query.sensor_types:
            sql += f" AND sensor_type = ANY(${param_idx})"
            params.append(query.sensor_types)
            param_idx += 1
        
        if query.start_time:
            sql += f" AND time >= ${param_idx}"
            params.append(query.start_time)
            param_idx += 1
        
        if query.end_time:
            sql += f" AND time <= ${param_idx}"
            params.append(query.end_time)
            param_idx += 1
        
        sql += " GROUP BY bucket, device_id, sensor_type ORDER BY bucket DESC"
        
        if query.limit:
            sql += f" LIMIT {query.limit}"
        
        async with self.db.connection() as conn:
            rows = await conn.fetch(sql, *params)
        
        return [
            AggregatedData(
                device_id=row['device_id'],
                sensor_type=row['sensor_type'],
                bucket_time=row['bucket'],
                avg_value=row['avg_value'],
                min_value=row['min_value'],
                max_value=row['max_value'],
                sum_value=row['sum_value'],
                count=row['count'],
                stddev=row['stddev'] or 0
            )
            for row in rows
        ]
    
    async def get_latest_readings(
        self,
        device_ids: list[str],
        sensor_types: Optional[list[str]] = None
    ) -> dict[str, dict[str, SensorReading]]:
        """Get latest reading for each device/sensor combination"""
        sql = """
            SELECT DISTINCT ON (device_id, sensor_type)
                time, device_id, sensor_type, value, unit, quality, metadata
            FROM sensor_data
            WHERE device_id = ANY($1)
        """
        params = [device_ids]
        
        if sensor_types:
            sql += " AND sensor_type = ANY($2)"
            params.append(sensor_types)
        
        sql += " ORDER BY device_id, sensor_type, time DESC"
        
        async with self.db.connection() as conn:
            rows = await conn.fetch(sql, *params)
        
        result = {}
        for row in rows:
            device_id = row['device_id']
            sensor_type = row['sensor_type']
            
            if device_id not in result:
                result[device_id] = {}
            
            result[device_id][sensor_type] = SensorReading(
                device_id=device_id,
                sensor_type=sensor_type,
                timestamp=row['time'],
                value=row['value'],
                unit=row['unit'],
                quality=row['quality'],
                metadata=row['metadata']
            )
        
        return result
    
    async def get_statistics(
        self,
        device_id: str,
        sensor_type: str,
        start_time: datetime,
        end_time: datetime
    ) -> dict:
        """Get statistical summary for a sensor"""
        async with self.db.connection() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COUNT(*) as count,
                    AVG(value) as avg,
                    MIN(value) as min,
                    MAX(value) as max,
                    STDDEV(value) as stddev,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) as median,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value) as p95,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY value) as p99
                FROM sensor_data
                WHERE device_id = $1 
                AND sensor_type = $2
                AND time >= $3 
                AND time <= $4
            """, device_id, sensor_type, start_time, end_time)
        
        return {
            "count": row['count'],
            "avg": row['avg'],
            "min": row['min'],
            "max": row['max'],
            "stddev": row['stddev'],
            "median": row['median'],
            "p95": row['p95'],
            "p99": row['p99']
        }


class DeviceEventRepository:
    """
    Repository for device events.
    """
    
    def __init__(self, db_manager: TimescaleDBManager):
        self.db = db_manager
    
    async def log_event(
        self,
        device_id: str,
        event_type: str,
        severity: str,
        message: str,
        details: dict = None
    ):
        """Log device event"""
        async with self.db.connection() as conn:
            await conn.execute("""
                INSERT INTO device_events (time, device_id, event_type, severity, message, details)
                VALUES (NOW(), $1, $2, $3, $4, $5)
            """, device_id, event_type, severity, message, details)
    
    async def get_events(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[list[str]] = None,
        severity: Optional[list[str]] = None,
        limit: int = 100
    ) -> list[dict]:
        """Query device events"""
        sql = "SELECT * FROM device_events WHERE device_id = $1"
        params = [device_id]
        param_idx = 2
        
        if start_time:
            sql += f" AND time >= ${param_idx}"
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            sql += f" AND time <= ${param_idx}"
            params.append(end_time)
            param_idx += 1
        
        if event_types:
            sql += f" AND event_type = ANY(${param_idx})"
            params.append(event_types)
            param_idx += 1
        
        if severity:
            sql += f" AND severity = ANY(${param_idx})"
            params.append(severity)
            param_idx += 1
        
        sql += f" ORDER BY time DESC LIMIT {limit}"
        
        async with self.db.connection() as conn:
            rows = await conn.fetch(sql, *params)
        
        return [dict(row) for row in rows]
    
    async def get_event_counts(
        self,
        device_id: str,
        interval: AggregationInterval,
        start_time: datetime,
        end_time: datetime
    ) -> list[dict]:
        """Get event counts by time bucket"""
        async with self.db.connection() as conn:
            rows = await conn.fetch(f"""
                SELECT 
                    time_bucket('{interval.value}', time) AS bucket,
                    event_type,
                    severity,
                    COUNT(*) as count
                FROM device_events
                WHERE device_id = $1 AND time >= $2 AND time <= $3
                GROUP BY bucket, event_type, severity
                ORDER BY bucket DESC
            """, device_id, start_time, end_time)
        
        return [dict(row) for row in rows]


class DataDownsampler:
    """
    Handles data downsampling and rollup operations.
    """
    
    def __init__(self, db_manager: TimescaleDBManager):
        self.db = db_manager
    
    async def downsample_to_table(
        self,
        source_table: str,
        target_table: str,
        interval: AggregationInterval,
        start_time: datetime,
        end_time: datetime
    ):
        """Downsample data from source to target table"""
        async with self.db.connection() as conn:
            await conn.execute(f"""
                INSERT INTO {target_table} (bucket, device_id, sensor_type, 
                    avg_value, min_value, max_value, sum_value, count, stddev)
                SELECT 
                    time_bucket('{interval.value}', time) AS bucket,
                    device_id,
                    sensor_type,
                    AVG(value) AS avg_value,
                    MIN(value) AS min_value,
                    MAX(value) AS max_value,
                    SUM(value) AS sum_value,
                    COUNT(*) AS count,
                    STDDEV(value) AS stddev
                FROM {source_table}
                WHERE time >= $1 AND time < $2
                GROUP BY bucket, device_id, sensor_type
                ON CONFLICT DO NOTHING
            """, start_time, end_time)
        
        logger.info(f"Downsampled {source_table} to {target_table}")
    
    async def create_rollup_tables(self):
        """Create rollup tables for different time intervals"""
        intervals = [
            ("sensor_data_hourly", "1 hour"),
            ("sensor_data_daily", "1 day"),
            ("sensor_data_weekly", "1 week"),
            ("sensor_data_monthly", "1 month")
        ]
        
        async with self.db.connection() as conn:
            for table_name, interval in intervals:
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        bucket TIMESTAMPTZ NOT NULL,
                        device_id TEXT NOT NULL,
                        sensor_type TEXT NOT NULL,
                        avg_value DOUBLE PRECISION,
                        min_value DOUBLE PRECISION,
                        max_value DOUBLE PRECISION,
                        sum_value DOUBLE PRECISION,
                        count BIGINT,
                        stddev DOUBLE PRECISION,
                        PRIMARY KEY (device_id, sensor_type, bucket)
                    );
                """)
                
                # Convert to hypertable
                await conn.execute(f"""
                    SELECT create_hypertable(
                        '{table_name}',
                        'bucket',
                        if_not_exists => TRUE
                    );
                """)
        
        logger.info("Created rollup tables")


class MultiTenantDataManager:
    """
    Manages multi-tenant data isolation for IoT platform.
    """
    
    def __init__(self, db_manager: TimescaleDBManager):
        self.db = db_manager
    
    async def create_tenant_schema(self, tenant_id: str):
        """Create isolated schema for tenant"""
        async with self.db.connection() as conn:
            await conn.execute(f"""
                CREATE SCHEMA IF NOT EXISTS tenant_{tenant_id};
            """)
            
            # Create tenant-specific tables
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS tenant_{tenant_id}.sensor_data (
                    time TIMESTAMPTZ NOT NULL,
                    device_id TEXT NOT NULL,
                    sensor_type TEXT NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    unit TEXT NOT NULL,
                    quality INTEGER DEFAULT 100,
                    metadata JSONB,
                    PRIMARY KEY (device_id, sensor_type, time)
                );
            """)
            
            await conn.execute(f"""
                SELECT create_hypertable(
                    'tenant_{tenant_id}.sensor_data',
                    'time',
                    if_not_exists => TRUE
                );
            """)
        
        logger.info(f"Created schema for tenant: {tenant_id}")
    
    async def get_tenant_repository(
        self,
        tenant_id: str
    ) -> SensorDataRepository:
        """Get repository scoped to tenant"""
        # In production, would return repository with tenant-specific queries
        return SensorDataRepository(self.db)
    
    async def get_tenant_usage(self, tenant_id: str) -> dict:
        """Get storage usage for tenant"""
        async with self.db.connection() as conn:
            row = await conn.fetchrow(f"""
                SELECT 
                    pg_total_relation_size('tenant_{tenant_id}.sensor_data') as total_size,
                    (SELECT COUNT(*) FROM tenant_{tenant_id}.sensor_data) as row_count,
                    (SELECT COUNT(DISTINCT device_id) FROM tenant_{tenant_id}.sensor_data) as device_count
            """)
        
        return {
            "total_bytes": row['total_size'],
            "row_count": row['row_count'],
            "device_count": row['device_count']
        }


class TimeSeriesAnalytics:
    """
    Advanced analytics on time-series data.
    """
    
    def __init__(self, db_manager: TimescaleDBManager):
        self.db = db_manager
    
    async def detect_anomalies(
        self,
        device_id: str,
        sensor_type: str,
        lookback_hours: int = 24,
        threshold_stddev: float = 3.0
    ) -> list[SensorReading]:
        """Detect anomalous readings using statistical methods"""
        async with self.db.connection() as conn:
            rows = await conn.fetch("""
                WITH stats AS (
                    SELECT 
                        AVG(value) as mean,
                        STDDEV(value) as stddev
                    FROM sensor_data
                    WHERE device_id = $1 
                    AND sensor_type = $2
                    AND time >= NOW() - $3 * INTERVAL '1 hour'
                )
                SELECT s.time, s.device_id, s.sensor_type, s.value, s.unit, s.quality, s.metadata
                FROM sensor_data s, stats
                WHERE s.device_id = $1 
                AND s.sensor_type = $2
                AND s.time >= NOW() - $3 * INTERVAL '1 hour'
                AND ABS(s.value - stats.mean) > $4 * stats.stddev
                ORDER BY s.time DESC
            """, device_id, sensor_type, lookback_hours, threshold_stddev)
        
        return [
            SensorReading(
                device_id=row['device_id'],
                sensor_type=row['sensor_type'],
                timestamp=row['time'],
                value=row['value'],
                unit=row['unit'],
                quality=row['quality'],
                metadata=row['metadata']
            )
            for row in rows
        ]
    
    async def calculate_trends(
        self,
        device_id: str,
        sensor_type: str,
        interval: AggregationInterval,
        lookback_periods: int = 30
    ) -> dict:
        """Calculate trends and rates of change"""
        async with self.db.connection() as conn:
            rows = await conn.fetch(f"""
                SELECT 
                    time_bucket('{interval.value}', time) AS bucket,
                    AVG(value) as avg_value
                FROM sensor_data
                WHERE device_id = $1 
                AND sensor_type = $2
                AND time >= NOW() - $3 * INTERVAL '{interval.value}'
                GROUP BY bucket
                ORDER BY bucket
            """, device_id, sensor_type, lookback_periods)
        
        if len(rows) < 2:
            return {"trend": "insufficient_data"}
        
        values = [row['avg_value'] for row in rows]
        times = list(range(len(values)))
        
        # Simple linear regression
        n = len(values)
        sum_x = sum(times)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(times, values))
        sum_x2 = sum(x ** 2 for x in times)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        intercept = (sum_y - slope * sum_x) / n
        
        # Determine trend direction
        if slope > 0.01:
            trend = "increasing"
        elif slope < -0.01:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "slope": slope,
            "intercept": intercept,
            "current_value": values[-1],
            "predicted_next": slope * (n) + intercept,
            "data_points": n
        }
    
    async def forecast_simple(
        self,
        device_id: str,
        sensor_type: str,
        forecast_periods: int = 12,
        historical_periods: int = 168  # 1 week hourly
    ) -> list[dict]:
        """Simple moving average forecast"""
        async with self.db.connection() as conn:
            rows = await conn.fetch("""
                SELECT 
                    time_bucket('1 hour', time) AS bucket,
                    AVG(value) as avg_value
                FROM sensor_data
                WHERE device_id = $1 
                AND sensor_type = $2
                AND time >= NOW() - $3 * INTERVAL '1 hour'
                GROUP BY bucket
                ORDER BY bucket
            """, device_id, sensor_type, historical_periods)
        
        if len(rows) < 24:
            return []
        
        values = [row['avg_value'] for row in rows]
        last_bucket = rows[-1]['bucket']
        
        # Simple exponential smoothing
        alpha = 0.3
        smoothed = values[0]
        for v in values[1:]:
            smoothed = alpha * v + (1 - alpha) * smoothed
        
        # Generate forecast
        forecast = []
        current_value = smoothed
        
        for i in range(1, forecast_periods + 1):
            forecast_time = last_bucket + timedelta(hours=i)
            forecast.append({
                "time": forecast_time,
                "value": current_value,
                "confidence_lower": current_value * 0.9,
                "confidence_upper": current_value * 1.1
            })
        
        return forecast
