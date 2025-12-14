"""
ML-Based Traffic Routing Service
Implements intelligent node selection and load balancing using machine learning.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class NodeMetrics:
    """Metrics for a network node."""
    node_id: str
    latitude: float
    longitude: float
    bandwidth_available: float      # Mbps
    current_connections: int
    max_connections: int
    avg_latency: float              # ms
    packet_loss: float              # percentage
    quality_score: float            # 0-100
    uptime_percentage: float
    last_seen: datetime
    

@dataclass
class RoutingDecision:
    """Result of ML routing decision."""
    node_id: str
    score: float
    estimated_latency: float
    estimated_bandwidth: float
    confidence: float


class TrafficPredictor:
    """Predicts traffic patterns for nodes."""
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def prepare_features(self, metrics: NodeMetrics, hour: int, day_of_week: int) -> np.ndarray:
        """Prepare features for prediction."""
        return np.array([[
            metrics.bandwidth_available,
            metrics.current_connections,
            metrics.avg_latency,
            metrics.quality_score,
            hour,
            day_of_week,
            metrics.uptime_percentage
        ]])
    
    def train(self, historical_data: List[Dict]):
        """Train the traffic prediction model."""
        if len(historical_data) < 100:
            logger.warning("Insufficient data for training")
            return
            
        X = []
        y = []
        
        for record in historical_data:
            features = [
                record['bandwidth'],
                record['connections'],
                record['latency'],
                record['quality'],
                record['hour'],
                record['day_of_week'],
                record['uptime']
            ]
            X.append(features)
            y.append(record['future_load'])
        
        X = np.array(X)
        y = np.array(y)
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        logger.info("Traffic predictor trained successfully")
    
    def predict_load(self, metrics: NodeMetrics, hours_ahead: int = 1) -> float:
        """Predict future load for a node."""
        if not self.is_trained:
            # Fallback to simple heuristic
            return metrics.current_connections / max(metrics.max_connections, 1)
        
        now = datetime.utcnow()
        future = now + timedelta(hours=hours_ahead)
        
        features = self.prepare_features(metrics, future.hour, future.weekday())
        features_scaled = self.scaler.transform(features)
        
        return float(self.model.predict(features_scaled)[0])
    
    def save_model(self, path: str):
        """Save trained model to disk."""
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained
        }, path)
    
    def load_model(self, path: str):
        """Load trained model from disk."""
        data = joblib.load(path)
        self.model = data['model']
        self.scaler = data['scaler']
        self.is_trained = data['is_trained']


class QualityPredictor:
    """Predicts node quality and reliability."""
    
    def __init__(self):
        self.model = GradientBoostingClassifier(n_estimators=50, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def predict_reliability(self, metrics: NodeMetrics) -> float:
        """Predict reliability score for a node."""
        if not self.is_trained:
            # Heuristic fallback
            return (
                metrics.quality_score * 0.4 +
                metrics.uptime_percentage * 0.3 +
                (100 - metrics.packet_loss * 10) * 0.3
            ) / 100
        
        features = np.array([[
            metrics.quality_score,
            metrics.uptime_percentage,
            metrics.packet_loss,
            metrics.avg_latency,
            metrics.bandwidth_available
        ]])
        
        features_scaled = self.scaler.transform(features)
        proba = self.model.predict_proba(features_scaled)
        
        return float(proba[0][1])  # Probability of being reliable


class MLRoutingService:
    """Main ML-based routing service."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.traffic_predictor = TrafficPredictor()
        self.quality_predictor = QualityPredictor()
        self.nodes: Dict[str, NodeMetrics] = {}
        
        # Routing weights (can be adjusted via governance)
        self.weights = {
            'latency': 0.25,
            'bandwidth': 0.25,
            'quality': 0.20,
            'load': 0.15,
            'distance': 0.15
        }
        
    async def connect(self):
        """Connect to Redis."""
        self.redis = await redis.from_url(self.redis_url)
        logger.info("ML Routing service connected to Redis")
        
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
    
    async def update_node_metrics(self, node_id: str, metrics: Dict):
        """Update metrics for a node."""
        self.nodes[node_id] = NodeMetrics(
            node_id=node_id,
            latitude=metrics.get('latitude', 0),
            longitude=metrics.get('longitude', 0),
            bandwidth_available=metrics.get('bandwidth', 100),
            current_connections=metrics.get('connections', 0),
            max_connections=metrics.get('max_connections', 100),
            avg_latency=metrics.get('latency', 50),
            packet_loss=metrics.get('packet_loss', 0),
            quality_score=metrics.get('quality', 80),
            uptime_percentage=metrics.get('uptime', 99),
            last_seen=datetime.utcnow()
        )
        
        # Cache in Redis
        if self.redis:
            await self.redis.hset(
                f"node:{node_id}:metrics",
                mapping=metrics
            )
            await self.redis.expire(f"node:{node_id}:metrics", 300)
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in km."""
        from math import radians, cos, sin, sqrt, atan2
        
        R = 6371  # Earth's radius in km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def calculate_node_score(
        self,
        node: NodeMetrics,
        user_lat: float,
        user_lon: float
    ) -> Tuple[float, Dict]:
        """Calculate composite score for a node."""
        
        # Normalize metrics
        latency_score = max(0, 1 - node.avg_latency / 200)  # Assume 200ms is worst
        bandwidth_score = min(1, node.bandwidth_available / 100)  # Normalize to 100 Mbps
        quality_score = node.quality_score / 100
        
        # Load factor (prefer less loaded nodes)
        current_load = node.current_connections / max(node.max_connections, 1)
        predicted_load = self.traffic_predictor.predict_load(node)
        load_score = 1 - (current_load * 0.6 + predicted_load * 0.4)
        
        # Distance factor
        distance = self.calculate_distance(user_lat, user_lon, node.latitude, node.longitude)
        distance_score = max(0, 1 - distance / 500)  # 500km = 0 score
        
        # Reliability factor
        reliability = self.quality_predictor.predict_reliability(node)
        
        # Combined score
        scores = {
            'latency': latency_score,
            'bandwidth': bandwidth_score,
            'quality': quality_score * reliability,
            'load': load_score,
            'distance': distance_score
        }
        
        total_score = sum(
            scores[key] * self.weights[key]
            for key in self.weights
        )
        
        return total_score, scores
    
    async def select_best_nodes(
        self,
        user_lat: float,
        user_lon: float,
        num_nodes: int = 3,
        min_quality: float = 50
    ) -> List[RoutingDecision]:
        """Select best nodes for a user."""
        
        # Filter active nodes
        now = datetime.utcnow()
        active_nodes = [
            node for node in self.nodes.values()
            if (now - node.last_seen).seconds < 300  # Active in last 5 mins
            and node.quality_score >= min_quality
            and node.current_connections < node.max_connections
        ]
        
        if not active_nodes:
            logger.warning("No active nodes available")
            return []
        
        # Score all nodes
        scored_nodes = []
        for node in active_nodes:
            score, details = self.calculate_node_score(node, user_lat, user_lon)
            scored_nodes.append((node, score, details))
        
        # Sort by score (highest first)
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N nodes
        results = []
        for node, score, details in scored_nodes[:num_nodes]:
            results.append(RoutingDecision(
                node_id=node.node_id,
                score=score,
                estimated_latency=node.avg_latency,
                estimated_bandwidth=node.bandwidth_available,
                confidence=min(score * 1.2, 1.0)
            ))
        
        return results
    
    async def get_load_balanced_nodes(
        self,
        required_bandwidth: float,
        num_nodes: int = 5
    ) -> List[RoutingDecision]:
        """Get load-balanced selection of nodes."""
        
        # Filter nodes with sufficient bandwidth
        suitable_nodes = [
            node for node in self.nodes.values()
            if node.bandwidth_available >= required_bandwidth
            and node.current_connections < node.max_connections * 0.8
        ]
        
        # Sort by load (least loaded first)
        suitable_nodes.sort(
            key=lambda n: n.current_connections / max(n.max_connections, 1)
        )
        
        results = []
        for node in suitable_nodes[:num_nodes]:
            results.append(RoutingDecision(
                node_id=node.node_id,
                score=node.quality_score / 100,
                estimated_latency=node.avg_latency,
                estimated_bandwidth=node.bandwidth_available,
                confidence=0.8
            ))
        
        return results
    
    async def update_weights_from_governance(self, new_weights: Dict[str, float]):
        """Update routing weights (called from governance)."""
        total = sum(new_weights.values())
        self.weights = {k: v / total for k, v in new_weights.items()}
        logger.info(f"Updated routing weights: {self.weights}")


# Singleton instance
routing_service = MLRoutingService()


async def get_routing_service() -> MLRoutingService:
    """Get the routing service instance."""
    if routing_service.redis is None:
        await routing_service.connect()
    return routing_service
