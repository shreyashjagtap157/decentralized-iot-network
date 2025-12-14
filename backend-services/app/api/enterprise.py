"""
Enterprise Dashboard API Extensions
Multi-tenant support, SLA management, and enterprise features.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import uuid

from app.db.models import get_db

router = APIRouter(prefix="/api/v1/enterprise", tags=["enterprise"])


# ==================== Models ====================

class OrganizationCreate(BaseModel):
    name: str
    admin_email: str
    plan: str = "starter"  # starter, business, enterprise


class Organization(BaseModel):
    id: str
    name: str
    admin_email: str
    plan: str
    created_at: datetime
    device_limit: int
    api_key: str
    is_active: bool


class SLAConfig(BaseModel):
    organization_id: str
    min_uptime: float = 99.5        # Percentage
    max_latency_ms: int = 100
    min_bandwidth_mbps: float = 10
    guaranteed_nodes: int = 3
    priority_routing: bool = True
    dedicated_support: bool = False


class UsageQuota(BaseModel):
    organization_id: str
    monthly_data_limit_gb: float
    monthly_api_calls: int
    concurrent_connections: int
    current_data_used_gb: float = 0
    current_api_calls: int = 0


class APIKey(BaseModel):
    key: str
    organization_id: str
    name: str
    permissions: List[str]
    rate_limit: int
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool


class EnterpriseMetrics(BaseModel):
    organization_id: str
    period_start: datetime
    period_end: datetime
    total_data_transferred_gb: float
    total_api_calls: int
    avg_latency_ms: float
    uptime_percentage: float
    active_devices: int
    sla_breaches: int


# ==================== Storage (In-memory for demo) ====================

organizations: Dict[str, Organization] = {}
sla_configs: Dict[str, SLAConfig] = {}
usage_quotas: Dict[str, UsageQuota] = {}
api_keys: Dict[str, APIKey] = {}


# ==================== Plan Limits ====================

PLAN_LIMITS = {
    "starter": {
        "device_limit": 10,
        "monthly_data_gb": 100,
        "api_calls": 10000,
        "concurrent_connections": 50,
        "sla_uptime": 99.0,
        "priority_routing": False
    },
    "business": {
        "device_limit": 100,
        "monthly_data_gb": 1000,
        "api_calls": 100000,
        "concurrent_connections": 500,
        "sla_uptime": 99.5,
        "priority_routing": True
    },
    "enterprise": {
        "device_limit": 10000,
        "monthly_data_gb": 10000,
        "api_calls": 1000000,
        "concurrent_connections": 5000,
        "sla_uptime": 99.9,
        "priority_routing": True,
        "dedicated_support": True
    }
}


# ==================== Endpoints ====================

@router.post("/organizations", response_model=Organization)
async def create_organization(org: OrganizationCreate):
    """Create a new enterprise organization."""
    if org.plan not in PLAN_LIMITS:
        raise HTTPException(400, "Invalid plan")
    
    limits = PLAN_LIMITS[org.plan]
    org_id = str(uuid.uuid4())
    api_key = f"iot_{secrets.token_hex(32)}"
    
    organization = Organization(
        id=org_id,
        name=org.name,
        admin_email=org.admin_email,
        plan=org.plan,
        created_at=datetime.utcnow(),
        device_limit=limits["device_limit"],
        api_key=api_key,
        is_active=True
    )
    
    organizations[org_id] = organization
    
    # Create default SLA config
    sla_configs[org_id] = SLAConfig(
        organization_id=org_id,
        min_uptime=limits["sla_uptime"],
        priority_routing=limits.get("priority_routing", False),
        dedicated_support=limits.get("dedicated_support", False)
    )
    
    # Create usage quota
    usage_quotas[org_id] = UsageQuota(
        organization_id=org_id,
        monthly_data_limit_gb=limits["monthly_data_gb"],
        monthly_api_calls=limits["api_calls"],
        concurrent_connections=limits["concurrent_connections"]
    )
    
    return organization


@router.get("/organizations/{org_id}", response_model=Organization)
async def get_organization(org_id: str):
    """Get organization details."""
    if org_id not in organizations:
        raise HTTPException(404, "Organization not found")
    return organizations[org_id]


@router.get("/organizations/{org_id}/sla", response_model=SLAConfig)
async def get_sla_config(org_id: str):
    """Get SLA configuration for an organization."""
    if org_id not in sla_configs:
        raise HTTPException(404, "SLA config not found")
    return sla_configs[org_id]


@router.put("/organizations/{org_id}/sla", response_model=SLAConfig)
async def update_sla_config(org_id: str, config: SLAConfig):
    """Update SLA configuration (enterprise only)."""
    if org_id not in organizations:
        raise HTTPException(404, "Organization not found")
    
    org = organizations[org_id]
    if org.plan != "enterprise":
        raise HTTPException(403, "Custom SLA only available for enterprise plan")
    
    config.organization_id = org_id
    sla_configs[org_id] = config
    return config


@router.get("/organizations/{org_id}/usage", response_model=UsageQuota)
async def get_usage_quota(org_id: str):
    """Get current usage and quota for an organization."""
    if org_id not in usage_quotas:
        raise HTTPException(404, "Usage data not found")
    return usage_quotas[org_id]


@router.get("/organizations/{org_id}/metrics", response_model=EnterpriseMetrics)
async def get_enterprise_metrics(
    org_id: str,
    period_days: int = Query(30, ge=1, le=365)
):
    """Get detailed metrics for an organization."""
    if org_id not in organizations:
        raise HTTPException(404, "Organization not found")
    
    now = datetime.utcnow()
    period_start = now - timedelta(days=period_days)
    
    # In production, query from database
    # For demo, return mock data
    return EnterpriseMetrics(
        organization_id=org_id,
        period_start=period_start,
        period_end=now,
        total_data_transferred_gb=usage_quotas.get(org_id, UsageQuota(
            organization_id=org_id,
            monthly_data_limit_gb=100,
            monthly_api_calls=10000,
            concurrent_connections=50
        )).current_data_used_gb,
        total_api_calls=12500,
        avg_latency_ms=45.3,
        uptime_percentage=99.87,
        active_devices=75,
        sla_breaches=0
    )


@router.post("/organizations/{org_id}/api-keys", response_model=APIKey)
async def create_api_key(
    org_id: str,
    name: str,
    permissions: List[str] = ["read"],
    expires_days: Optional[int] = None
):
    """Create a new API key for an organization."""
    if org_id not in organizations:
        raise HTTPException(404, "Organization not found")
    
    import secrets
    key = f"iot_sk_{secrets.token_hex(24)}"
    
    api_key = APIKey(
        key=key,
        organization_id=org_id,
        name=name,
        permissions=permissions,
        rate_limit=PLAN_LIMITS[organizations[org_id].plan]["api_calls"] // 30,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=expires_days) if expires_days else None,
        is_active=True
    )
    
    api_keys[key] = api_key
    return api_key


@router.get("/organizations/{org_id}/api-keys", response_model=List[APIKey])
async def list_api_keys(org_id: str):
    """List all API keys for an organization."""
    return [k for k in api_keys.values() if k.organization_id == org_id]


@router.delete("/organizations/{org_id}/api-keys/{key}")
async def revoke_api_key(org_id: str, key: str):
    """Revoke an API key."""
    if key not in api_keys:
        raise HTTPException(404, "API key not found")
    if api_keys[key].organization_id != org_id:
        raise HTTPException(403, "Key does not belong to organization")
    
    api_keys[key].is_active = False
    return {"status": "revoked"}


# ==================== SLA Monitoring ====================

@router.get("/organizations/{org_id}/sla/breaches")
async def get_sla_breaches(
    org_id: str,
    period_days: int = Query(30, ge=1, le=365)
):
    """Get SLA breach history."""
    if org_id not in organizations:
        raise HTTPException(404, "Organization not found")
    
    # In production, query from database
    return {
        "organization_id": org_id,
        "period_days": period_days,
        "breaches": [],
        "total_breaches": 0,
        "sla_compliance_percentage": 100.0
    }


@router.get("/organizations/{org_id}/billing")
async def get_billing_summary(org_id: str):
    """Get billing summary for an organization."""
    if org_id not in organizations:
        raise HTTPException(404, "Organization not found")
    
    org = organizations[org_id]
    plans = {
        "starter": 49,
        "business": 199,
        "enterprise": 999
    }
    
    usage = usage_quotas.get(org_id)
    overage_cost = 0
    
    if usage:
        # $0.10 per GB overage
        if usage.current_data_used_gb > usage.monthly_data_limit_gb:
            overage = usage.current_data_used_gb - usage.monthly_data_limit_gb
            overage_cost = overage * 0.10
    
    return {
        "organization_id": org_id,
        "plan": org.plan,
        "base_cost": plans[org.plan],
        "overage_cost": overage_cost,
        "total_cost": plans[org.plan] + overage_cost,
        "billing_period": "monthly",
        "next_billing_date": (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1)
    }


import secrets
