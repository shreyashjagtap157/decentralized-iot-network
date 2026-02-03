"""
IoT Network Anomaly Detection Service
ML-based detection of unusual device behavior patterns for security and maintenance.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import numpy as np
from scipy import stats
import json

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    TRAFFIC_SPIKE = "traffic_spike"
    TRAFFIC_DROP = "traffic_drop"
    LATENCY_ANOMALY = "latency_anomaly"
    PATTERN_DEVIATION = "pattern_deviation"
    QUALITY_DEGRADATION = "quality_degradation"
    SECURITY_THREAT = "security_threat"
    DEVICE_FAILURE = "device_failure"
    UNUSUAL_TIMING = "unusual_timing"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DeviceMetrics:
    """Metrics collected from an IoT device"""
    device_id: str
    timestamp: datetime
    bytes_transmitted: int = 0
    bytes_received: int = 0
    latency_ms: float = 0.0
    packet_loss_rate: float = 0.0
    quality_score: float = 100.0
    connection_count: int = 0
    error_count: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    uptime_seconds: int = 0


@dataclass
class Anomaly:
    """Detected anomaly"""
    id: str
    device_id: str
    anomaly_type: AnomalyType
    severity: Severity
    timestamp: datetime
    description: str
    metrics: Dict[str, Any]
    confidence: float = 0.0
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class DeviceProfile:
    """Learned behavioral profile for a device"""
    device_id: str
    
    # Traffic patterns (hourly averages)
    hourly_traffic_mean: np.ndarray = field(default_factory=lambda: np.zeros(24))
    hourly_traffic_std: np.ndarray = field(default_factory=lambda: np.ones(24))
    
    # General statistics
    avg_latency: float = 0.0
    std_latency: float = 10.0
    avg_quality: float = 100.0
    std_quality: float = 5.0
    avg_error_rate: float = 0.0
    
    # Baseline metrics
    typical_packet_loss: float = 0.01
    typical_connection_count: float = 10.0
    
    # Learning metadata
    samples_collected: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    is_trained: bool = False


class IsolationForest:
    """Simple Isolation Forest implementation for anomaly detection"""
    
    def __init__(self, n_trees: int = 100, sample_size: int = 256, contamination: float = 0.1):
        self.n_trees = n_trees
        self.sample_size = sample_size
        self.contamination = contamination
        self.trees: List[Dict] = []
        self.threshold: float = 0.0
        
    def fit(self, X: np.ndarray):
        """Fit the isolation forest"""
        n_samples = len(X)
        self.trees = []
        
        for _ in range(self.n_trees):
            # Sample data
            sample_idx = np.random.choice(n_samples, min(self.sample_size, n_samples), replace=False)
            sample = X[sample_idx]
            
            # Build tree
            tree = self._build_tree(sample, 0, max_depth=int(np.ceil(np.log2(self.sample_size))))
            self.trees.append(tree)
        
        # Calculate threshold
        scores = self.decision_function(X)
        self.threshold = np.percentile(scores, 100 * (1 - self.contamination))
        
    def _build_tree(self, X: np.ndarray, depth: int, max_depth: int) -> Dict:
        """Recursively build an isolation tree"""
        n_samples, n_features = X.shape
        
        if depth >= max_depth or n_samples <= 1:
            return {"type": "leaf", "size": n_samples}
        
        # Random split
        feature = np.random.randint(n_features)
        min_val, max_val = X[:, feature].min(), X[:, feature].max()
        
        if min_val == max_val:
            return {"type": "leaf", "size": n_samples}
        
        split_value = np.random.uniform(min_val, max_val)
        
        left_mask = X[:, feature] < split_value
        right_mask = ~left_mask
        
        return {
            "type": "split",
            "feature": feature,
            "value": split_value,
            "left": self._build_tree(X[left_mask], depth + 1, max_depth),
            "right": self._build_tree(X[right_mask], depth + 1, max_depth)
        }
    
    def _path_length(self, x: np.ndarray, tree: Dict, depth: int = 0) -> float:
        """Calculate path length for a single sample"""
        if tree["type"] == "leaf":
            # Adjustment for unbuilt subtrees
            n = tree["size"]
            if n <= 1:
                return depth
            return depth + 2 * (np.log(n - 1) + 0.5772156649) - 2 * (n - 1) / n
        
        if x[tree["feature"]] < tree["value"]:
            return self._path_length(x, tree["left"], depth + 1)
        return self._path_length(x, tree["right"], depth + 1)
    
    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """Compute anomaly scores"""
        avg_path_lengths = np.zeros(len(X))
        
        for tree in self.trees:
            for i, x in enumerate(X):
                avg_path_lengths[i] += self._path_length(x, tree)
        
        avg_path_lengths /= self.n_trees
        
        # Normalize
        c = 2 * (np.log(self.sample_size - 1) + 0.5772156649) - 2 * (self.sample_size - 1) / self.sample_size
        scores = 2 ** (-avg_path_lengths / c)
        
        return scores
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict anomalies (1 = anomaly, 0 = normal)"""
        scores = self.decision_function(X)
        return (scores > self.threshold).astype(int)


class AnomalyDetector:
    """
    Multi-method anomaly detection for IoT devices.
    
    Methods used:
    - Statistical (z-score, percentile-based)
    - Isolation Forest (unsupervised ML)
    - Time-series pattern analysis
    - Heuristic rules for known threats
    """
    
    def __init__(
        self,
        z_score_threshold: float = 3.0,
        window_size: int = 100,
        learning_period_hours: int = 24
    ):
        self.z_score_threshold = z_score_threshold
        self.window_size = window_size
        self.learning_period = timedelta(hours=learning_period_hours)
        
        self.device_profiles: Dict[str, DeviceProfile] = {}
        self.device_history: Dict[str, deque] = {}
        self.isolation_forests: Dict[str, IsolationForest] = {}
        self.detected_anomalies: List[Anomaly] = []
        
        self._anomaly_counter = 0
    
    def _get_or_create_profile(self, device_id: str) -> DeviceProfile:
        if device_id not in self.device_profiles:
            self.device_profiles[device_id] = DeviceProfile(device_id=device_id)
            self.device_history[device_id] = deque(maxlen=self.window_size)
        return self.device_profiles[device_id]
    
    def record_metrics(self, metrics: DeviceMetrics) -> List[Anomaly]:
        """Record device metrics and check for anomalies"""
        profile = self._get_or_create_profile(metrics.device_id)
        history = self.device_history[metrics.device_id]
        
        # Store in history
        history.append(metrics)
        
        # Update profile
        self._update_profile(profile, metrics)
        
        # Detect anomalies
        anomalies = []
        
        if profile.is_trained:
            # Statistical detection
            stat_anomalies = self._detect_statistical_anomalies(metrics, profile)
            anomalies.extend(stat_anomalies)
            
            # Pattern-based detection
            if len(history) >= 10:
                pattern_anomalies = self._detect_pattern_anomalies(metrics, list(history), profile)
                anomalies.extend(pattern_anomalies)
            
            # ML-based detection
            if metrics.device_id in self.isolation_forests:
                ml_anomalies = self._detect_ml_anomalies(metrics)
                anomalies.extend(ml_anomalies)
        
        # Heuristic detection (always active)
        heuristic_anomalies = self._detect_heuristic_anomalies(metrics)
        anomalies.extend(heuristic_anomalies)
        
        # Store detected anomalies
        self.detected_anomalies.extend(anomalies)
        
        return anomalies
    
    def _update_profile(self, profile: DeviceProfile, metrics: DeviceMetrics):
        """Update device profile with new metrics"""
        hour = metrics.timestamp.hour
        profile.samples_collected += 1
        
        # Exponential moving average update
        alpha = min(0.1, 1.0 / profile.samples_collected)
        
        # Update hourly traffic pattern
        traffic = metrics.bytes_transmitted + metrics.bytes_received
        profile.hourly_traffic_mean[hour] = (1 - alpha) * profile.hourly_traffic_mean[hour] + alpha * traffic
        
        # Update latency stats
        profile.avg_latency = (1 - alpha) * profile.avg_latency + alpha * metrics.latency_ms
        
        # Update quality stats
        profile.avg_quality = (1 - alpha) * profile.avg_quality + alpha * metrics.quality_score
        
        # Mark as trained after learning period
        if profile.samples_collected >= 100:
            profile.is_trained = True
        
        profile.last_updated = datetime.utcnow()
    
    def _detect_statistical_anomalies(
        self,
        metrics: DeviceMetrics,
        profile: DeviceProfile
    ) -> List[Anomaly]:
        """Detect anomalies using statistical methods"""
        anomalies = []
        hour = metrics.timestamp.hour
        
        # Traffic anomaly
        traffic = metrics.bytes_transmitted + metrics.bytes_received
        expected_traffic = profile.hourly_traffic_mean[hour]
        traffic_std = max(profile.hourly_traffic_std[hour], 1.0)
        
        if expected_traffic > 0:
            z_score = abs(traffic - expected_traffic) / traffic_std
            if z_score > self.z_score_threshold:
                severity = Severity.MEDIUM if z_score < 5 else Severity.HIGH
                anomaly_type = AnomalyType.TRAFFIC_SPIKE if traffic > expected_traffic else AnomalyType.TRAFFIC_DROP
                
                anomalies.append(self._create_anomaly(
                    device_id=metrics.device_id,
                    anomaly_type=anomaly_type,
                    severity=severity,
                    description=f"Traffic deviation: {z_score:.1f} standard deviations from normal",
                    metrics={"traffic": traffic, "expected": expected_traffic, "z_score": z_score},
                    confidence=min(0.95, z_score / 5)
                ))
        
        # Latency anomaly
        if profile.std_latency > 0:
            latency_z = abs(metrics.latency_ms - profile.avg_latency) / max(profile.std_latency, 1.0)
            if latency_z > self.z_score_threshold:
                anomalies.append(self._create_anomaly(
                    device_id=metrics.device_id,
                    anomaly_type=AnomalyType.LATENCY_ANOMALY,
                    severity=Severity.MEDIUM,
                    description=f"Latency {metrics.latency_ms:.0f}ms vs expected {profile.avg_latency:.0f}ms",
                    metrics={"latency_ms": metrics.latency_ms, "expected": profile.avg_latency},
                    confidence=min(0.9, latency_z / 5)
                ))
        
        # Quality degradation
        if metrics.quality_score < profile.avg_quality - 2 * max(profile.std_quality, 5):
            anomalies.append(self._create_anomaly(
                device_id=metrics.device_id,
                anomaly_type=AnomalyType.QUALITY_DEGRADATION,
                severity=Severity.MEDIUM if metrics.quality_score > 50 else Severity.HIGH,
                description=f"Quality score dropped to {metrics.quality_score:.0f} (avg: {profile.avg_quality:.0f})",
                metrics={"quality": metrics.quality_score, "expected": profile.avg_quality},
                confidence=0.8
            ))
        
        return anomalies
    
    def _detect_pattern_anomalies(
        self,
        current: DeviceMetrics,
        history: List[DeviceMetrics],
        profile: DeviceProfile
    ) -> List[Anomaly]:
        """Detect anomalies in temporal patterns"""
        anomalies = []
        
        # Check for unusual timing (device active at unexpected hour)
        hour = current.timestamp.hour
        expected_activity = profile.hourly_traffic_mean[hour]
        current_traffic = current.bytes_transmitted + current.bytes_received
        
        if expected_activity < 100 and current_traffic > 10000:
            anomalies.append(self._create_anomaly(
                device_id=current.device_id,
                anomaly_type=AnomalyType.UNUSUAL_TIMING,
                severity=Severity.MEDIUM,
                description=f"Unusual activity at hour {hour} (typically inactive)",
                metrics={"hour": hour, "traffic": current_traffic, "expected": expected_activity},
                confidence=0.7
            ))
        
        # Check for pattern deviation (sudden change in behavior)
        if len(history) >= 10:
            recent_errors = [m.error_count for m in history[-10:]]
            historical_errors = [m.error_count for m in history[:-10]] if len(history) > 10 else [0]
            
            if np.mean(recent_errors) > np.mean(historical_errors) + 3 * max(np.std(historical_errors), 1):
                anomalies.append(self._create_anomaly(
                    device_id=current.device_id,
                    anomaly_type=AnomalyType.PATTERN_DEVIATION,
                    severity=Severity.HIGH,
                    description="Significant increase in error rate detected",
                    metrics={
                        "recent_error_avg": float(np.mean(recent_errors)),
                        "historical_avg": float(np.mean(historical_errors))
                    },
                    confidence=0.85
                ))
        
        return anomalies
    
    def _detect_ml_anomalies(self, metrics: DeviceMetrics) -> List[Anomaly]:
        """Detect anomalies using Isolation Forest"""
        anomalies = []
        
        if metrics.device_id not in self.isolation_forests:
            return anomalies
        
        iforest = self.isolation_forests[metrics.device_id]
        
        # Create feature vector
        features = np.array([[
            metrics.bytes_transmitted,
            metrics.bytes_received,
            metrics.latency_ms,
            metrics.packet_loss_rate,
            metrics.quality_score,
            metrics.error_count,
            metrics.connection_count
        ]])
        
        try:
            score = iforest.decision_function(features)[0]
            is_anomaly = iforest.predict(features)[0]
            
            if is_anomaly:
                anomalies.append(self._create_anomaly(
                    device_id=metrics.device_id,
                    anomaly_type=AnomalyType.PATTERN_DEVIATION,
                    severity=Severity.MEDIUM if score < 0.7 else Severity.HIGH,
                    description="ML model detected unusual behavior pattern",
                    metrics={"anomaly_score": float(score)},
                    confidence=float(score)
                ))
        except Exception as e:
            logger.error(f"ML detection failed: {e}")
        
        return anomalies
    
    def _detect_heuristic_anomalies(self, metrics: DeviceMetrics) -> List[Anomaly]:
        """Detect anomalies using heuristic rules"""
        anomalies = []
        
        # High packet loss - potential network attack or hardware issue
        if metrics.packet_loss_rate > 0.1:
            severity = Severity.HIGH if metrics.packet_loss_rate > 0.3 else Severity.MEDIUM
            anomalies.append(self._create_anomaly(
                device_id=metrics.device_id,
                anomaly_type=AnomalyType.DEVICE_FAILURE,
                severity=severity,
                description=f"High packet loss rate: {metrics.packet_loss_rate:.1%}",
                metrics={"packet_loss_rate": metrics.packet_loss_rate},
                confidence=0.9
            ))
        
        # Excessive connections - possible DDoS or bot activity
        if metrics.connection_count > 1000:
            anomalies.append(self._create_anomaly(
                device_id=metrics.device_id,
                anomaly_type=AnomalyType.SECURITY_THREAT,
                severity=Severity.CRITICAL if metrics.connection_count > 5000 else Severity.HIGH,
                description=f"Excessive connections: {metrics.connection_count}",
                metrics={"connection_count": metrics.connection_count},
                confidence=0.95
            ))
        
        # High error rate
        if metrics.error_count > 100:
            anomalies.append(self._create_anomaly(
                device_id=metrics.device_id,
                anomaly_type=AnomalyType.DEVICE_FAILURE,
                severity=Severity.HIGH,
                description=f"High error count: {metrics.error_count}",
                metrics={"error_count": metrics.error_count},
                confidence=0.85
            ))
        
        # Zero quality score - device not functioning
        if metrics.quality_score <= 0:
            anomalies.append(self._create_anomaly(
                device_id=metrics.device_id,
                anomaly_type=AnomalyType.DEVICE_FAILURE,
                severity=Severity.CRITICAL,
                description="Device quality score is zero - possible failure",
                metrics={"quality_score": metrics.quality_score},
                confidence=0.99
            ))
        
        return anomalies
    
    def _create_anomaly(
        self,
        device_id: str,
        anomaly_type: AnomalyType,
        severity: Severity,
        description: str,
        metrics: Dict[str, Any],
        confidence: float
    ) -> Anomaly:
        """Create an anomaly record"""
        self._anomaly_counter += 1
        return Anomaly(
            id=f"ANM-{self._anomaly_counter:06d}",
            device_id=device_id,
            anomaly_type=anomaly_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            description=description,
            metrics=metrics,
            confidence=confidence
        )
    
    def train_ml_model(self, device_id: str):
        """Train the Isolation Forest model for a device"""
        if device_id not in self.device_history:
            return
        
        history = list(self.device_history[device_id])
        if len(history) < 50:
            logger.info(f"Not enough data to train model for {device_id}")
            return
        
        # Create feature matrix
        X = np.array([
            [
                m.bytes_transmitted,
                m.bytes_received,
                m.latency_ms,
                m.packet_loss_rate,
                m.quality_score,
                m.error_count,
                m.connection_count
            ]
            for m in history
        ])
        
        # Train model
        iforest = IsolationForest(n_trees=50, sample_size=min(128, len(history)))
        iforest.fit(X)
        self.isolation_forests[device_id] = iforest
        
        logger.info(f"Trained ML model for device {device_id} with {len(history)} samples")
    
    def get_anomalies(
        self,
        device_id: Optional[str] = None,
        severity: Optional[Severity] = None,
        since: Optional[datetime] = None,
        unresolved_only: bool = False
    ) -> List[Anomaly]:
        """Query detected anomalies"""
        results = self.detected_anomalies
        
        if device_id:
            results = [a for a in results if a.device_id == device_id]
        if severity:
            results = [a for a in results if a.severity == severity]
        if since:
            results = [a for a in results if a.timestamp >= since]
        if unresolved_only:
            results = [a for a in results if not a.resolved]
        
        return results
    
    def acknowledge_anomaly(self, anomaly_id: str) -> bool:
        """Acknowledge an anomaly"""
        for anomaly in self.detected_anomalies:
            if anomaly.id == anomaly_id:
                anomaly.acknowledged = True
                return True
        return False
    
    def resolve_anomaly(self, anomaly_id: str) -> bool:
        """Mark an anomaly as resolved"""
        for anomaly in self.detected_anomalies:
            if anomaly.id == anomaly_id:
                anomaly.resolved = True
                return True
        return False
    
    def get_device_health_score(self, device_id: str) -> float:
        """Calculate overall health score for a device (0-100)"""
        recent_anomalies = self.get_anomalies(
            device_id=device_id,
            since=datetime.utcnow() - timedelta(hours=24),
            unresolved_only=True
        )
        
        if not recent_anomalies:
            return 100.0
        
        # Deduct points based on severity
        severity_weights = {
            Severity.LOW: 5,
            Severity.MEDIUM: 15,
            Severity.HIGH: 30,
            Severity.CRITICAL: 50
        }
        
        total_deduction = sum(severity_weights.get(a.severity, 10) for a in recent_anomalies)
        return max(0.0, 100.0 - total_deduction)


# Factory function
def create_anomaly_detector(
    z_threshold: float = 3.0,
    window_size: int = 100
) -> AnomalyDetector:
    return AnomalyDetector(
        z_score_threshold=z_threshold,
        window_size=window_size
    )
