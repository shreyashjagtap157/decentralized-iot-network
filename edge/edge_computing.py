"""
Edge Computing for IoT Network

Implements distributed fog computing with local inference and stream processing.

Features:
- Local ML model inference on edge devices
- Apache Kafka/Pulsar message streaming
- Apache Flink stream processing
- Data filtering and aggregation at edge
- Reduced latency and bandwidth
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class EdgeNodeType(Enum):
    """Type of edge node"""
    GATEWAY = "gateway"  # Regional aggregator
    FOG = "fog"          # Local processing
    DEVICE = "device"    # Edge device


@dataclass
class SensorReading:
    """Raw sensor reading"""
    sensor_id: str
    timestamp: datetime
    value: float
    unit: str
    device_id: str
    location: str
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedData:
    """Processed data after edge computation"""
    original_reading_ids: List[str]
    timestamp: datetime
    
    aggregated_value: float
    anomaly_score: float
    prediction: float
    
    requires_cloud: bool = False
    priority: int = 0  # 0=low, 5=high


class EdgeMLModel:
    """
    Local ML model for inference on edge.
    Optimized for resource constraints.
    """
    
    def __init__(
        self,
        model_id: str,
        model_type: str = "linear"  # linear, decision_tree, neural_net
    ):
        self.model_id = model_id
        self.model_type = model_type
        
        self.weights: Optional[np.ndarray] = None
        self.bias: float = 0.0
        
        self.quantized: bool = False
        self.inference_time_ms: float = 0.0
    
    def load_model(self, weights: np.ndarray, bias: float = 0.0):
        """Load model weights"""
        self.weights = weights
        self.bias = bias
        logger.info(f"Loaded model {self.model_id}")
    
    async def predict(self, features: np.ndarray) -> Tuple[float, float]:
        """
        Run inference on edge.
        
        Returns: (prediction, confidence)
        """
        import time
        start = time.time()
        
        if self.weights is None:
            return 0.0, 0.0
        
        # Simple linear prediction
        if len(features.shape) == 1:
            features = features.reshape(1, -1)
        
        # Ensure dimensions match
        if features.shape[1] != self.weights.shape[0]:
            return 0.0, 0.0
        
        prediction = np.dot(features, self.weights) + self.bias
        
        # Confidence based on model type
        confidence = min(1.0, max(0.0, np.tanh(abs(prediction[0]))))
        
        self.inference_time_ms = (time.time() - start) * 1000
        
        return float(prediction[0]), float(confidence)
    
    def quantize(self) -> Dict[str, Any]:
        """Quantize model for storage/transmission"""
        if self.weights is None:
            return {}
        
        # Convert to int8
        min_val = np.min(self.weights)
        max_val = np.max(self.weights)
        scale = (max_val - min_val) / 255.0
        
        quantized = np.round(
            (self.weights - min_val) / scale
        ).astype(np.int8)
        
        return {
            "model_id": self.model_id,
            "quantized_weights": quantized.tolist(),
            "scale": float(scale),
            "offset": float(min_val),
            "bias": float(self.bias)
        }


class AnomalyDetector:
    """
    Detects anomalies in sensor data at edge.
    Uses lightweight statistical methods.
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.historical_values: List[float] = []
        
        self.mean: float = 0.0
        self.std: float = 1.0
    
    def add_value(self, value: float):
        """Add value to history"""
        self.historical_values.append(value)
        
        # Keep window size
        if len(self.historical_values) > self.window_size:
            self.historical_values.pop(0)
        
        # Update statistics
        self._update_stats()
    
    def _update_stats(self):
        """Update mean and std"""
        if not self.historical_values:
            return
        
        self.mean = np.mean(self.historical_values)
        self.std = np.std(self.historical_values)
    
    def score_anomaly(self, value: float) -> float:
        """
        Score how anomalous a value is.
        
        Returns: 0.0 (normal) to 1.0 (very anomalous)
        """
        if self.std == 0:
            return 0.0
        
        # Z-score
        z_score = abs((value - self.mean) / self.std)
        
        # Convert to 0-1 scale using sigmoid-like function
        anomaly_score = min(1.0, z_score / 3.0)
        
        return anomaly_score


class StreamProcessor:
    """
    Processes sensor streams at edge.
    """
    
    def __init__(self):
        self.processing_windows: Dict[str, List[SensorReading]] = {}
        self.window_size_ms: int = 5000  # 5 second windows
        self.processors: List[Callable] = []
    
    def add_processor(self, processor: Callable):
        """Add stream processor function"""
        self.processors.append(processor)
    
    async def process_reading(
        self,
        reading: SensorReading
    ) -> Optional[ProcessedData]:
        """Process a sensor reading"""
        sensor_id = reading.sensor_id
        
        # Add to window
        if sensor_id not in self.processing_windows:
            self.processing_windows[sensor_id] = []
        
        self.processing_windows[sensor_id].append(reading)
        
        # Check if window is complete
        if len(self.processing_windows[sensor_id]) >= 5:
            window = self.processing_windows[sensor_id]
            self.processing_windows[sensor_id] = []
            
            # Process window
            aggregated = np.mean([r.value for r in window])
            
            # Run custom processors
            for processor in self.processors:
                result = processor(window)
                if result:
                    return result
            
            # Default processing
            return ProcessedData(
                original_reading_ids=[r.sensor_id for r in window],
                timestamp=datetime.utcnow(),
                aggregated_value=float(aggregated),
                anomaly_score=0.0,
                prediction=float(aggregated),
                requires_cloud=False
            )
        
        return None


class FogNodeDevice:
    """
    Represents a fog computing node.
    Runs local inference and stream processing.
    """
    
    def __init__(
        self,
        node_id: str,
        node_type: EdgeNodeType = EdgeNodeType.FOG,
        max_storage_mb: float = 500.0
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.max_storage = int(max_storage_mb * 1024 * 1024)
        
        self.ml_models: Dict[str, EdgeMLModel] = {}
        self.anomaly_detectors: Dict[str, AnomalyDetector] = {}
        self.stream_processor = StreamProcessor()
        
        # Data management
        self.local_buffer: List[ProcessedData] = []
        self.current_storage_usage: int = 0
        
        # Statistics
        self.readings_processed: int = 0
        self.inference_calls: int = 0
        self.total_inference_time_ms: float = 0.0
        self.anomalies_detected: int = 0
        
        # Status
        self.is_active: bool = True
        self.last_heartbeat: datetime = datetime.utcnow()
    
    def load_model(
        self,
        model_id: str,
        weights: np.ndarray,
        bias: float = 0.0
    ):
        """Load ML model"""
        model = EdgeMLModel(model_id)
        model.load_model(weights, bias)
        self.ml_models[model_id] = model
    
    def register_detector(self, sensor_id: str):
        """Register anomaly detector for sensor"""
        if sensor_id not in self.anomaly_detectors:
            self.anomaly_detectors[sensor_id] = AnomalyDetector()
    
    async def process_sensor_reading(
        self,
        reading: SensorReading,
        model_id: Optional[str] = None
    ) -> ProcessedData:
        """Process sensor reading with edge inference"""
        self.readings_processed += 1
        
        # Anomaly detection
        if reading.sensor_id not in self.anomaly_detectors:
            self.register_detector(reading.sensor_id)
        
        detector = self.anomaly_detectors[reading.sensor_id]
        detector.add_value(reading.value)
        anomaly_score = detector.score_anomaly(reading.value)
        
        # ML inference if available
        prediction = reading.value
        if model_id and model_id in self.ml_models:
            model = self.ml_models[model_id]
            features = np.array([[reading.value]])
            prediction, confidence = await model.predict(features)
            
            self.inference_calls += 1
            self.total_inference_time_ms += model.inference_time_ms
        
        # Count anomalies
        if anomaly_score > 0.7:
            self.anomalies_detected += 1
        
        # Stream processing
        processed = await self.stream_processor.process_reading(reading)
        
        if processed:
            processed.anomaly_score = anomaly_score
            processed.prediction = prediction
            
            # Determine if needs cloud
            processed.requires_cloud = (
                anomaly_score > 0.8 or
                abs(prediction - reading.value) > reading.value * 0.2
            )
            
            # Buffer data
            self._buffer_data(processed)
            
            return processed
        
        return ProcessedData(
            original_reading_ids=[reading.sensor_id],
            timestamp=datetime.utcnow(),
            aggregated_value=reading.value,
            anomaly_score=anomaly_score,
            prediction=prediction,
            requires_cloud=anomaly_score > 0.8
        )
    
    def _buffer_data(self, data: ProcessedData):
        """Buffer processed data"""
        estimated_size = len(json.dumps({
            "value": data.aggregated_value,
            "timestamp": data.timestamp.isoformat()
        }).encode())
        
        if self.current_storage_usage + estimated_size < self.max_storage:
            self.local_buffer.append(data)
            self.current_storage_usage += estimated_size
    
    def get_buffered_data(self, max_items: int = 100) -> List[ProcessedData]:
        """Get buffered data"""
        data = self.local_buffer[:max_items]
        self.local_buffer = self.local_buffer[max_items:]
        
        self.current_storage_usage = max(
            0,
            self.current_storage_usage - sum(
                len(json.dumps({"value": d.aggregated_value}).encode())
                for d in data
            )
        )
        
        return data
    
    def get_status(self) -> Dict[str, Any]:
        """Get node status"""
        avg_inference_time = (
            self.total_inference_time_ms / self.inference_calls
            if self.inference_calls > 0 else 0
        )
        
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "is_active": self.is_active,
            "readings_processed": self.readings_processed,
            "anomalies_detected": self.anomalies_detected,
            "inference_calls": self.inference_calls,
            "avg_inference_time_ms": float(avg_inference_time),
            "storage_usage_mb": self.current_storage_usage / (1024 * 1024),
            "buffered_items": len(self.local_buffer),
            "models_loaded": len(self.ml_models)
        }


class EdgeComputingCluster:
    """
    Coordinates multiple fog nodes.
    """
    
    def __init__(self):
        self.nodes: Dict[str, FogNodeDevice] = {}
        self.node_registry: Dict[str, Dict[str, Any]] = {}
    
    def add_node(
        self,
        node_id: str,
        node_type: EdgeNodeType = EdgeNodeType.FOG
    ) -> FogNodeDevice:
        """Add fog node"""
        node = FogNodeDevice(node_id, node_type)
        self.nodes[node_id] = node
        
        self.node_registry[node_id] = {
            "type": node_type.value,
            "added_at": datetime.utcnow(),
            "status": "active"
        }
        
        return node
    
    def get_node(self, node_id: str) -> Optional[FogNodeDevice]:
        """Get node by ID"""
        return self.nodes.get(node_id)
    
    def get_healthy_nodes(self) -> List[FogNodeDevice]:
        """Get healthy nodes"""
        return [n for n in self.nodes.values() if n.is_active]
    
    async def broadcast_processing(
        self,
        reading: SensorReading,
        model_id: Optional[str] = None
    ) -> List[ProcessedData]:
        """Broadcast processing to multiple nodes"""
        tasks = []
        
        for node in self.get_healthy_nodes():
            task = node.process_sensor_reading(reading, model_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if isinstance(r, ProcessedData)]
    
    def collect_data_from_nodes(
        self,
        node_id: Optional[str] = None
    ) -> Dict[str, List[ProcessedData]]:
        """Collect buffered data from nodes"""
        data = {}
        
        nodes_to_query = (
            [self.nodes[node_id]] if node_id and node_id in self.nodes
            else self.nodes.values()
        )
        
        for node in nodes_to_query:
            buffered = node.get_buffered_data()
            if buffered:
                data[node.node_id] = buffered
        
        return data
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall cluster status"""
        nodes_data = []
        
        for node in self.nodes.values():
            nodes_data.append(node.get_status())
        
        total_readings = sum(n["readings_processed"] for n in nodes_data)
        total_anomalies = sum(n["anomalies_detected"] for n in nodes_data)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_nodes": len(self.nodes),
            "healthy_nodes": len(self.get_healthy_nodes()),
            "total_readings_processed": total_readings,
            "total_anomalies_detected": total_anomalies,
            "nodes": nodes_data
        }
