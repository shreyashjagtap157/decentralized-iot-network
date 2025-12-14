from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
import uuid



class DeviceUpdate(BaseModel):
    """
    Schema for device update requests.
    """
    location_lat: Optional[float] = Field(None, ge=-90, le=90)
    location_lng: Optional[float] = Field(None, ge=-180, le=180)
    status: Optional[str] = None
    device_type: Optional[str] = None


class DeviceRegistration(BaseModel):
    """
    Schema for device registration requests.
    """
    device_id: str = Field(..., max_length=50)
    device_type: str = Field(..., max_length=20)
    owner_address: str = Field(..., pattern=r'^0x[a-fA-F0-9]{40}$')
    location_lat: float = Field(..., ge=-90, le=90)
    location_lng: float = Field(..., ge=-180, le=180)
    signature: str


class DeviceResponse(BaseModel):
    """
    Schema for device registration response.
    """
    device_id: str
    device_type: str
    owner_address: str
    status: str
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class NetworkUsageRequest(BaseModel):
    """
    Schema for network usage data submission.
    """
    bytes_transmitted: int = Field(..., ge=0)
    bytes_received: int = Field(..., ge=0)
    connection_quality: int = Field(..., ge=0, le=100)
    user_sessions: int = Field(..., ge=0)


class UserCreate(BaseModel):
    """
    Schema for user creation requests.
    """
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """
    Schema for user update requests.
    """
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """
    Schema for user response.
    """
    id: uuid.UUID
    username: str
    email: str
    full_name: Optional[str] = None
    role: str = "user"
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """
    Schema for authentication token response.
    """
    access_token: str
    token_type: str = "bearer"


class CompensationTransactionResponse(BaseModel):
    """
    Schema for compensation transaction response.
    """
    id: int
    device_id: str
    owner_address: str
    total_bytes: int
    average_quality: float
    reward_amount: Optional[float] = None
    status: str
    blockchain_tx_hash: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

