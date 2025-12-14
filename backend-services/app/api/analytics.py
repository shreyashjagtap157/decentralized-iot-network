from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_
from app.db.models import get_db, CompensationTransaction, NetworkUsage, Device, User
from app.api.dependencies import get_current_user
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@router.get("/user-earnings")
async def get_user_earnings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    range: str = Query("7d", description="Time range (24h, 7d, 30d)")
):
    """Get complete user analytics including earnings, devices, and throughput"""
    
    # Determine start date based on range
    now = datetime.utcnow()
    if range == "24h":
        start_date = now - timedelta(hours=24)
    elif range == "30d":
        start_date = now - timedelta(days=30)
    else: # default 7d
        start_date = now - timedelta(days=7)
    
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Get User's Devices Stats
    user_devices_result = await db.execute(
        select(Device).where(Device.owner_address == current_user.username) # Assuming username is maps to owner_address for now
    )
    user_devices = user_devices_result.scalars().all()
    device_ids = [d.device_id for d in user_devices]
    
    total_devices = len(user_devices)
    active_devices = sum(1 for d in user_devices if d.status == 'ACTIVE')
    avg_quality = sum(d.quality_score for d in user_devices) / total_devices if total_devices > 0 else 0

    if not device_ids:
        return {
            "totalEarnings": 0,
            "todayEarnings": 0,
            "activeDevices": 0,
            "totalDevices": 0,
            "averageQuality": 0,
            "hourlyThroughput": [],
            "dailyEarnings": [],
            "deviceBreakdown": []
        }

    # 2. Get Compensation Transactions (Earnings)
    earnings_query = select(CompensationTransaction).where(
        and_(
            CompensationTransaction.device_id.in_(device_ids),
            CompensationTransaction.created_at >= start_date
        )
    )
    transactions_result = await db.execute(earnings_query)
    transactions = transactions_result.scalars().all()

    # Calculate Total Earnings
    total_earnings = sum(float(t.reward_amount or 0) for t in transactions)
    
    # Calculate Today's Earnings
    today_earnings = sum(float(t.reward_amount or 0) for t in transactions if t.created_at >= today_start)

    # Daily Earnings Breakdown
    daily_earnings_map = {}
    for t in transactions:
        date_str = t.created_at.date().isoformat()
        daily_earnings_map[date_str] = daily_earnings_map.get(date_str, 0) + float(t.reward_amount or 0)
    
    daily_earnings_list = [
        {"date": k, "amount": v} for k, v in sorted(daily_earnings_map.items())
    ]

    # Device Breakdown (Count by Type)
    device_types = {}
    for d in user_devices:
        device_types[d.device_type] = device_types.get(d.device_type, 0) + 1
    
    device_breakdown = [
        {"type": k, "count": v} for k, v in device_types.items()
    ]

    # 3. Get Network Usage (Throughput)
    usage_query = select(NetworkUsage).where(
        and_(
            NetworkUsage.device_id.in_(device_ids),
            NetworkUsage.timestamp >= start_date
        )
    )
    usage_result = await db.execute(usage_query)
    usage_records = usage_result.scalars().all()

    # Hourly Throughput
    hourly_throughput_map = {}
    for record in usage_records:
        # Round to nearest hour
        hour_str = record.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
        hourly_throughput_map[hour_str] = hourly_throughput_map.get(hour_str, 0) + record.bytes_transmitted

    hourly_throughput_list = [
        {"hour": k, "bytes": v} for k, v in sorted(hourly_throughput_map.items())
    ]

    # Return data in format expected by frontend (CamelCase keys to match interface)
    return {
        "totalEarnings": total_earnings,
        "todayEarnings": today_earnings,
        "activeDevices": active_devices,
        "totalDevices": total_devices,
        "averageQuality": round(avg_quality, 1),
        "hourlyThroughput": hourly_throughput_list,
        "dailyEarnings": daily_earnings_list,
        "deviceBreakdown": device_breakdown
    }

@router.get("/network-stats")
async def get_network_stats(
    db: AsyncSession = Depends(get_db),
    hours: int = Query(24, description="Number of hours to look back")
):
    """Get network-wide statistics"""
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    usage_stats = await db.execute(
        select(NetworkUsage).where(NetworkUsage.timestamp >= start_time)
    )
    usage_records = usage_stats.scalars().all()
    
    if not usage_records:
        return {
            "total_bytes": 0,
            "active_devices": 0,
            "average_quality": 0,
            "hourly_throughput": []
        }
    
    total_bytes = sum(r.bytes_transmitted for r in usage_records)
    active_devices = len(set(r.device_id for r in usage_records))
    avg_quality = sum(r.quality_score for r in usage_records) / len(usage_records)
    
    hourly_data = {}
    for record in usage_records:
        hour_key = record.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
        hourly_data[hour_key] = hourly_data.get(hour_key, 0) + record.bytes_transmitted
    
    return {
        "total_bytes": total_bytes,
        "active_devices": active_devices,
        "average_quality": round(avg_quality, 2),
        "hourly_throughput": [
            {"hour": k, "bytes": v} for k, v in sorted(hourly_data.items())
        ]
    }
