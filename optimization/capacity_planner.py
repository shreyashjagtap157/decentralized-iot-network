"""
Capacity Planning & Cost Optimization for IoT

Predictive capacity planning, cost analysis, and resource optimization.

Features:
- Growth trend analysis
- Capacity forecasting
- Cost breakdown and optimization
- Resource utilization monitoring
- Scalability recommendations
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources"""
    COMPUTE = "compute"      # CPU/GPU hours
    STORAGE = "storage"      # GB stored
    BANDWIDTH = "bandwidth"  # GB transferred
    MEMORY = "memory"        # GB RAM
    DATABASE = "database"    # Queries, connections
    API_CALLS = "api_calls"


class CostCategory(Enum):
    """Cost categories"""
    INFRASTRUCTURE = "infrastructure"
    DATA_TRANSFER = "data_transfer"
    STORAGE = "storage"
    COMPUTE = "compute"
    LICENSING = "licensing"
    OPERATIONAL = "operational"


@dataclass
class ResourceMetrics:
    """Resource usage metrics"""
    timestamp: datetime
    resource_type: ResourceType
    
    used: float
    available: float
    utilization_percent: float
    
    peak_today: float
    average_7day: float
    average_30day: float
    
    trend: str = "stable"  # increasing, stable, decreasing
    forecast_7day: float = 0.0
    forecast_30day: float = 0.0


@dataclass
class CostBreakdown:
    """Cost breakdown"""
    timestamp: datetime
    category: CostCategory
    
    current_cost: float
    daily_cost: float
    monthly_cost: float
    annual_cost: float
    
    unit_cost: float
    usage_volume: float
    
    period_over_period_change: float = 0.0


@dataclass
class CapacityForecast:
    """Capacity forecast"""
    resource_type: ResourceType
    forecast_days: int
    
    current_usage: float
    forecast_7day: float
    forecast_30day: float
    forecast_90day: float
    
    confidence: float
    trend_description: str
    
    capacity_limit: float
    days_until_capacity: Optional[int] = None


class TrendAnalyzer:
    """
    Analyzes trends in resource usage.
    """
    
    def __init__(self, lookback_days: int = 90):
        self.lookback_days = lookback_days
        self.usage_history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def record_usage(self, resource_type: str, usage: float):
        """Record resource usage"""
        if resource_type not in self.usage_history:
            self.usage_history[resource_type] = []
        
        self.usage_history[resource_type].append((datetime.utcnow(), usage))
        
        # Keep only lookback period
        cutoff = datetime.utcnow() - timedelta(days=self.lookback_days)
        self.usage_history[resource_type] = [
            (t, u) for t, u in self.usage_history[resource_type]
            if t > cutoff
        ]
    
    def get_trend(self, resource_type: str) -> Dict[str, Any]:
        """Analyze trend for resource"""
        if resource_type not in self.usage_history:
            return {}
        
        history = self.usage_history[resource_type]
        if len(history) < 2:
            return {}
        
        values = [v for _, v in sorted(history)]
        times = [t for t, _ in sorted(history)]
        
        # Calculate metrics
        current = values[-1]
        avg_7day = np.mean(values[-7:]) if len(values) >= 7 else current
        avg_30day = np.mean(values[-30:]) if len(values) >= 30 else avg_7day
        
        # Trend calculation
        if len(values) >= 7:
            early = np.mean(values[-14:-7])
            recent = np.mean(values[-7:])
            trend_pct = (recent - early) / (early + 0.01) * 100
        else:
            trend_pct = 0
        
        # Determine trend direction
        if trend_pct > 5:
            trend = "increasing"
        elif trend_pct < -5:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # Linear regression for forecast
        x = np.arange(len(values))
        y = np.array(values)
        
        if len(values) >= 3:
            z = np.polyfit(x, y, 1)
            forecast_7day = current + z[0] * 7
            forecast_30day = current + z[0] * 30
        else:
            forecast_7day = current
            forecast_30day = current
        
        return {
            "current": float(current),
            "avg_7day": float(avg_7day),
            "avg_30day": float(avg_30day),
            "trend": trend,
            "trend_pct": float(trend_pct),
            "forecast_7day": float(max(0, forecast_7day)),
            "forecast_30day": float(max(0, forecast_30day))
        }


class CostCalculator:
    """
    Calculates and tracks costs.
    """
    
    def __init__(self):
        self.pricing: Dict[ResourceType, float] = {
            ResourceType.COMPUTE: 0.25,      # $ per CPU-hour
            ResourceType.STORAGE: 0.023,      # $ per GB-month
            ResourceType.BANDWIDTH: 0.09,     # $ per GB
            ResourceType.MEMORY: 0.05,        # $ per GB-hour
            ResourceType.DATABASE: 0.0001,    # $ per query
            ResourceType.API_CALLS: 0.00005   # $ per call
        }
        
        self.usage_history: Dict[ResourceType, List[Tuple[datetime, float]]] = {}
        self.cost_history: List[CostBreakdown] = []
    
    def set_pricing(self, resource_type: ResourceType, price_per_unit: float):
        """Set pricing for resource"""
        self.pricing[resource_type] = price_per_unit
    
    def record_usage(self, resource_type: ResourceType, amount: float):
        """Record usage"""
        if resource_type not in self.usage_history:
            self.usage_history[resource_type] = []
        
        self.usage_history[resource_type].append((datetime.utcnow(), amount))
    
    def calculate_cost(
        self,
        resource_type: ResourceType,
        amount: float
    ) -> float:
        """Calculate cost for usage"""
        return amount * self.pricing.get(resource_type, 0)
    
    def get_cost_breakdown(self) -> Dict[ResourceType, CostBreakdown]:
        """Get current cost breakdown"""
        breakdown = {}
        
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        month_ago = now - timedelta(days=30)
        year_ago = now - timedelta(days=365)
        
        for resource_type, history in self.usage_history.items():
            # Calculate usage in different periods
            total_usage = sum(u for t, u in history)
            daily_usage = sum(u for t, u in history if t > day_ago)
            monthly_usage = sum(u for t, u in history if t > month_ago)
            yearly_usage = sum(u for t, u in history if t > year_ago)
            
            unit_cost = self.pricing.get(resource_type, 0)
            
            current_cost = daily_usage * unit_cost
            daily_cost = (monthly_usage / 30) * unit_cost if monthly_usage > 0 else 0
            monthly_cost = monthly_usage * unit_cost
            annual_cost = yearly_usage * unit_cost
            
            # Calculate period-over-period change
            last_30 = sum(u for t, u in history if month_ago < t <= month_ago + timedelta(days=30))
            first_30 = sum(u for t, u in history if year_ago < t <= year_ago + timedelta(days=30))
            
            pop_change = (
                (last_30 - first_30) / (first_30 + 0.01) * 100
                if first_30 > 0 else 0
            )
            
            breakdown[resource_type] = CostBreakdown(
                timestamp=now,
                category=self._resource_to_category(resource_type),
                current_cost=current_cost,
                daily_cost=daily_cost,
                monthly_cost=monthly_cost,
                annual_cost=annual_cost,
                unit_cost=unit_cost,
                usage_volume=monthly_usage,
                period_over_period_change=pop_change
            )
        
        return breakdown
    
    @staticmethod
    def _resource_to_category(resource_type: ResourceType) -> CostCategory:
        """Map resource type to cost category"""
        mapping = {
            ResourceType.COMPUTE: CostCategory.COMPUTE,
            ResourceType.STORAGE: CostCategory.STORAGE,
            ResourceType.BANDWIDTH: CostCategory.DATA_TRANSFER,
            ResourceType.MEMORY: CostCategory.COMPUTE,
            ResourceType.DATABASE: CostCategory.INFRASTRUCTURE,
            ResourceType.API_CALLS: CostCategory.INFRASTRUCTURE
        }
        return mapping.get(resource_type, CostCategory.OPERATIONAL)


class CapacityPlanner:
    """
    Plans capacity requirements.
    """
    
    def __init__(self):
        self.resource_limits: Dict[ResourceType, float] = {
            ResourceType.COMPUTE: 10000,      # CPU-hours/month
            ResourceType.STORAGE: 100000,     # GB
            ResourceType.BANDWIDTH: 50000,    # GB/month
            ResourceType.MEMORY: 5000,        # GB
            ResourceType.DATABASE: 10000000,  # Queries/month
            ResourceType.API_CALLS: 100000000 # Calls/month
        }
        
        self.trend_analyzer = TrendAnalyzer()
        self.cost_calculator = CostCalculator()
    
    def set_capacity_limit(self, resource_type: ResourceType, limit: float):
        """Set capacity limit"""
        self.resource_limits[resource_type] = limit
    
    def forecast_capacity(
        self,
        resource_type: ResourceType
    ) -> CapacityForecast:
        """Forecast capacity needs"""
        trend = self.trend_analyzer.get_trend(resource_type.value)
        
        if not trend:
            return CapacityForecast(
                resource_type=resource_type,
                forecast_days=30,
                current_usage=0,
                forecast_7day=0,
                forecast_30day=0,
                forecast_90day=0,
                confidence=0,
                trend_description="insufficient_data",
                capacity_limit=self.resource_limits.get(resource_type, 0)
            )
        
        current = trend.get("current", 0)
        forecast_7day = trend.get("forecast_7day", current)
        forecast_30day = trend.get("forecast_30day", current)
        
        # 90-day forecast (simplified)
        daily_growth = (forecast_30day - current) / 30
        forecast_90day = current + daily_growth * 90
        
        # Calculate days until capacity
        capacity_limit = self.resource_limits.get(resource_type, float('inf'))
        daily_increase = (forecast_7day - current) / 7
        
        days_until_capacity = None
        if daily_increase > 0 and forecast_90day > capacity_limit:
            days_until_capacity = int((capacity_limit - current) / (daily_increase + 0.001))
        
        return CapacityForecast(
            resource_type=resource_type,
            forecast_days=30,
            current_usage=current,
            forecast_7day=forecast_7day,
            forecast_30day=forecast_30day,
            forecast_90day=forecast_90day,
            confidence=0.85,
            trend_description=trend.get("trend", "stable"),
            capacity_limit=capacity_limit,
            days_until_capacity=days_until_capacity
        )
    
    def get_scaling_recommendations(self) -> List[Dict[str, Any]]:
        """Get scaling recommendations"""
        recommendations = []
        
        for resource_type in ResourceType:
            forecast = self.forecast_capacity(resource_type)
            
            if forecast.days_until_capacity and forecast.days_until_capacity < 60:
                severity = "critical" if forecast.days_until_capacity < 14 else "warning"
                
                recommendations.append({
                    "resource": resource_type.value,
                    "severity": severity,
                    "message": f"Will exceed capacity in {forecast.days_until_capacity} days",
                    "current_usage": forecast.current_usage,
                    "capacity_limit": forecast.capacity_limit,
                    "forecast_30day": forecast.forecast_30day,
                    "required_increase_percent": (
                        (forecast.forecast_30day - forecast.capacity_limit) /
                        forecast.capacity_limit * 100
                    ) if forecast.capacity_limit > 0 else 0
                })
        
        return sorted(recommendations, key=lambda x: x.get("days", float('inf')))
    
    def get_cost_optimization_tips(self) -> List[Dict[str, Any]]:
        """Get cost optimization recommendations"""
        tips = []
        
        breakdown = self.cost_calculator.get_cost_breakdown()
        
        # Find highest cost items
        sorted_costs = sorted(
            breakdown.items(),
            key=lambda x: x[1].monthly_cost,
            reverse=True
        )
        
        for resource_type, cost_data in sorted_costs[:3]:
            if cost_data.period_over_period_change > 20:
                tips.append({
                    "resource": resource_type.value,
                    "monthly_cost": cost_data.monthly_cost,
                    "trend": "increasing",
                    "pct_change": cost_data.period_over_period_change,
                    "recommendation": f"Optimize {resource_type.value} usage - growing {cost_data.period_over_period_change:.1f}% month-over-month"
                })
            elif cost_data.period_over_period_change < -10:
                tips.append({
                    "resource": resource_type.value,
                    "monthly_cost": cost_data.monthly_cost,
                    "trend": "decreasing",
                    "pct_change": cost_data.period_over_period_change,
                    "recommendation": f"Good trend on {resource_type.value} costs"
                })
        
        return tips


class CapacityOptimizer:
    """
    Main coordinator for capacity planning and cost optimization.
    """
    
    def __init__(self):
        self.planner = CapacityPlanner()
        self.trend_analyzer = self.planner.trend_analyzer
        self.cost_calculator = self.planner.cost_calculator
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "cost_breakdown": {},
            "capacity_forecasts": {},
            "recommendations": [],
            "cost_optimization_tips": []
        }
        
        # Cost breakdown
        breakdown = self.cost_calculator.get_cost_breakdown()
        report["cost_breakdown"] = {
            resource.value: {
                "monthly_cost": cost.monthly_cost,
                "daily_cost": cost.daily_cost,
                "annual_cost": cost.annual_cost,
                "trend": "increasing" if cost.period_over_period_change > 0 else "decreasing",
                "change_pct": cost.period_over_period_change
            }
            for resource, cost in breakdown.items()
        }
        
        # Total costs
        total_monthly = sum(cost.monthly_cost for cost in breakdown.values())
        report["total_monthly_cost"] = float(total_monthly)
        report["total_annual_cost"] = float(total_monthly * 12)
        
        # Capacity forecasts
        for resource_type in ResourceType:
            forecast = self.planner.forecast_capacity(resource_type)
            report["capacity_forecasts"][resource_type.value] = {
                "current_usage": forecast.current_usage,
                "forecast_7day": forecast.forecast_7day,
                "forecast_30day": forecast.forecast_30day,
                "forecast_90day": forecast.forecast_90day,
                "trend": forecast.trend_description,
                "days_until_capacity": forecast.days_until_capacity
            }
        
        # Recommendations
        report["recommendations"] = self.planner.get_scaling_recommendations()
        report["cost_optimization_tips"] = self.planner.get_cost_optimization_tips()
        
        return report
