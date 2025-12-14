"""
Error monitoring and logging setup
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
import logging
import sys
from typing import Optional
import os

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

def setup_sentry(dsn: Optional[str] = None, environment: str = "development"):
    """Setup Sentry error monitoring"""
    if dsn or os.getenv("SENTRY_DSN"):
        sentry_sdk.init(
            dsn=dsn or os.getenv("SENTRY_DSN"),
            integrations=[
                FastApiIntegration(auto_enabling_integrations=False),
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
            traces_sample_rate=0.1,
            environment=environment,
            attach_stacktrace=True,
            send_default_pii=False,
        )
        logging.info("Sentry error monitoring initialized")
    else:
        logging.warning("Sentry DSN not provided, error monitoring disabled")

def setup_logging():
    """Setup application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log', encoding='utf-8')
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)

def log_error(error: Exception, context: dict = None):
    """Log error with context"""
    logger = logging.getLogger(__name__)
    logger.error(f"Error occurred: {str(error)}", extra={'context': context})
    
    # Send to Sentry if available
    if sentry_sdk.Hub.current.client:
        with sentry_sdk.configure_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)

def log_api_usage(endpoint: str, user_id: str, response_time: float):
    """Log API usage metrics"""
    logger = logging.getLogger("api.usage")
    logger.info(
        "API_USAGE",
        extra={
            'endpoint': endpoint,
            'user_id': user_id,
            'response_time': response_time,
        }
    )

def log_device_activity(device_id: str, activity_type: str, data: dict):
    """Log device activity"""
    logger = logging.getLogger("device.activity")
    logger.info(
        f"DEVICE_ACTIVITY: {activity_type}",
        extra={
            'device_id': device_id,
            'activity_type': activity_type,
            'data': data,
        }
    )

def setup_tracing(service_name: str):
    """Setup OpenTelemetry distributed tracing"""
    resource = Resource(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter()
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)

    # Optional: Console exporter for debugging
    console_exporter = ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(console_exporter))

    trace.set_tracer_provider(provider)

    # Instrument libraries
    FastAPIInstrumentor.instrument_app()
    RequestsInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()

    logging.info("OpenTelemetry tracing initialized")
