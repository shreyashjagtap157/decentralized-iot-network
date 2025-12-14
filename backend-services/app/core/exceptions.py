from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from .logging import logger

class DeviceNotFoundError(HTTPException):
    """
    Exception raised when a device is not found in the database.
    Args:
        device_id (str): The device identifier.
    """
    def __init__(self, device_id: str):
        super().__init__(
            status_code=404,
            detail=f"Device {device_id} not found"
        )

class InvalidUsageDataError(HTTPException):
    """
    Exception raised for invalid usage data submissions.
    Args:
        message (str): Error message describing the invalid data.
    """
    def __init__(self, message: str):
        super().__init__(
            status_code=422,
            detail=f"Invalid usage data: {message}"
        )

def register_exception_handlers(app):
    """
    Register global exception handlers for the FastAPI app.
    Args:
        app (FastAPI): The FastAPI application instance.
    """
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        logger.error("Validation error", errors=exc.errors())
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error", "errors": exc.errors()}
        )
