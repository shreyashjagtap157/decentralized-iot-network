"""
Integration of edge computing, blockchain audit trail, and capacity planning
into the decentralized IoT network backend.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json

from edge.edge_computing import EdgeComputingCluster, FogNodeDevice
from blockchain.audit_trail import AuditTrailManager, AuditEvent, EventType
from optimization.capacity_planner import CapacityOptimizer

logger = logging.getLogger(__name__)


class EnhancedIoTBackend:
    """
    Enhanced IoT backend with edge computing, blockchain audit trail,
    and intelligent capacity planning.
    """
    
    def __init__(
        self,
        enable_edge_computing: bool = True,
        enable_audit_trail: bool = True,
        enable_capacity_planning: bool = True,
        kafka_brokers: Optional[List[str]] = None,
        smart_contract_address: Optional[str] = None
    ):
        self.kafka_brokers = kafka_brokers or ["localhost:9092"]
        self.smart_contract_address = smart_contract_address or "0x0000000000000000000000000000000000000000"
        
        # Initialize edge computing cluster
        self.edge_cluster: Optional[EdgeComputingCluster] = None
        if enable_edge_computing:
            self.edge_cluster = EdgeComputingCluster(
                cluster_id="iot-edge-1",
                max_nodes=10,
                kafka_brokers=self.kafka_brokers
            )
        
        # Initialize blockchain audit trail manager
        self.audit_trail: Optional[AuditTrailManager] = None
        if enable_audit_trail:
            self.audit_trail = AuditTrailManager(
                db_path="./audit_trail.db",
                smart_contract_address=self.smart_contract_address
            )
        
        # Initialize capacity planner
        self.capacity_planner: Optional[CapacityOptimizer] = None
        if enable_capacity_planning:
            self.capacity_planner = CapacityOptimizer(
                replan_interval=3600,  # 1 hour
                cost_per_cpu_hour=0.10,
                cost_per_gb_month=5.0
            )
        
        self.running = False
    
    async def startup_backend(self):
        """Initialize all IoT backend components."""
        if self.edge_cluster:
            try:
                await self.edge_cluster.initialize()
                logger.info(f"Edge computing cluster initialized: {self.edge_cluster.cluster_id}")
            except Exception as e:
                logger.error(f"Failed to initialize edge cluster: {e}")
        
        if self.audit_trail:
            try:
                await self.audit_trail.initialize()
                logger.info("Blockchain audit trail initialized")
            except Exception as e:
                logger.error(f"Failed to initialize audit trail: {e}")
        
        if self.capacity_planner:
            try:
                await self.capacity_planner.start()
                logger.info("Capacity planner started")
            except Exception as e:
                logger.error(f"Failed to start capacity planner: {e}")
    
    async def shutdown_backend(self):
        """Shutdown all IoT backend components."""
        if self.capacity_planner:
            try:
                await self.capacity_planner.stop()
                logger.info("Capacity planner stopped")
            except Exception as e:
                logger.error(f"Error stopping capacity planner: {e}")
        
        if self.audit_trail:
            try:
                await self.audit_trail.shutdown()
                logger.info("Audit trail shutdown")
            except Exception as e:
                logger.error(f"Error during audit trail shutdown: {e}")
        
        if self.edge_cluster:
            try:
                await self.edge_cluster.shutdown()
                logger.info("Edge cluster shutdown")
            except Exception as e:
                logger.error(f"Error during edge cluster shutdown: {e}")
    
    async def register_fog_node(
        self,
        node_id: str,
        location: str,
        cpu_cores: int,
        memory_gb: int,
        storage_gb: int,
        network_latency_ms: float
    ) -> bool:
        """Register a new fog node in the edge cluster."""
        if not self.edge_cluster:
            return False
        
        try:
            node = FogNodeDevice(
                node_id=node_id,
                location=location,
                cpu_cores=cpu_cores,
                memory_gb=memory_gb,
                storage_gb=storage_gb,
                network_latency_ms=network_latency_ms
            )
            
            self.edge_cluster.add_node(node)
            
            # Log audit event for node registration
            if self.audit_trail:
                await self.audit_trail.create_event(
                    AuditEvent(
                        event_type=EventType.DEVICE_REGISTERED,
                        device_id=node_id,
                        timestamp=datetime.utcnow(),
                        description=f"Fog node registered: {location}",
                        metadata={
                            'cpu': cpu_cores,
                            'memory': memory_gb,
                            'storage': storage_gb
                        }
                    )
                )
            
            logger.info(f"Fog node registered: {node_id} @ {location}")
            return True
        except Exception as e:
            logger.error(f"Failed to register fog node: {e}")
            return False
    
    async def process_sensor_data(
        self,
        device_id: str,
        sensor_type: str,
        value: float,
        timestamp: Optional[datetime] = None
    ) -> Dict:
        """
        Process sensor data through edge computing cluster.
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        result = {
            'device_id': device_id,
            'sensor_type': sensor_type,
            'raw_value': value,
            'timestamp': timestamp.isoformat(),
            'processed_value': None,
            'anomaly_detected': False,
            'edge_processed': False,
            'audit_recorded': False
        }
        
        try:
            # Process through edge cluster if available
            if self.edge_cluster:
                processed = await self.edge_cluster.process_sensor_data(
                    device_id=device_id,
                    sensor_type=sensor_type,
                    value=value,
                    timestamp=timestamp
                )
                result['processed_value'] = processed['value']
                result['anomaly_detected'] = processed['anomaly']
                result['edge_processed'] = True
                
                logger.debug(f"Edge processed {sensor_type} from {device_id}: "
                           f"{value:.2f} -> {processed['value']:.2f}")
            
            # Log to audit trail if anomaly detected
            if result['anomaly_detected'] and self.audit_trail:
                await self.audit_trail.create_event(
                    AuditEvent(
                        event_type=EventType.ANOMALY_DETECTED,
                        device_id=device_id,
                        timestamp=timestamp,
                        description=f"Anomaly in {sensor_type} reading",
                        metadata={
                            'sensor_type': sensor_type,
                            'value': value,
                            'processed_value': result['processed_value']
                        }
                    )
                )
                result['audit_recorded'] = True
                logger.warning(f"Anomaly detected: {device_id} {sensor_type}={value:.2f}")
        
        except Exception as e:
            logger.error(f"Failed to process sensor data: {e}")
        
        return result
    
    async def get_cluster_status(self) -> Dict:
        """Get comprehensive edge cluster status."""
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'cluster_status': None,
            'capacity_plan': None,
            'audit_trail_stats': None
        }
        
        if self.edge_cluster:
            try:
                cluster_info = self.edge_cluster.get_status()
                status['cluster_status'] = {
                    'cluster_id': cluster_info['cluster_id'],
                    'nodes': cluster_info['nodes'],
                    'total_capacity': cluster_info['total_capacity'],
                    'used_capacity': cluster_info['used_capacity'],
                    'utilization_pct': cluster_info['utilization_pct']
                }
                logger.debug(f"Cluster utilization: {cluster_info['utilization_pct']:.1%}")
            except Exception as e:
                logger.warning(f"Failed to get cluster status: {e}")
        
        if self.capacity_planner:
            try:
                plan = self.capacity_planner.get_current_plan()
                status['capacity_plan'] = {
                    'planned_nodes': plan['planned_nodes'],
                    'estimated_cost': plan['estimated_cost'],
                    'scaling_actions': plan.get('scaling_actions', []),
                    'next_review': plan.get('next_review', '')
                }
                logger.debug(f"Capacity plan: {plan['planned_nodes']} nodes, "
                           f"${plan['estimated_cost']:.2f}/month")
            except Exception as e:
                logger.warning(f"Failed to get capacity plan: {e}")
        
        if self.audit_trail:
            try:
                stats = self.audit_trail.get_statistics()
                status['audit_trail_stats'] = {
                    'total_events': stats['total_events'],
                    'anomalies_logged': stats['anomalies_logged'],
                    'operations_logged': stats['operations_logged'],
                    'merkle_root': stats.get('merkle_root', 'pending')
                }
                logger.debug(f"Audit: {stats['total_events']} events, "
                           f"{stats['anomalies_logged']} anomalies")
            except Exception as e:
                logger.warning(f"Failed to get audit stats: {e}")
        
        return status
    
    async def optimize_resource_allocation(self) -> Dict:
        """Run optimization to allocate resources efficiently."""
        if not self.capacity_planner:
            return {'error': 'Capacity planner not enabled'}
        
        try:
            optimization_result = self.capacity_planner.optimize()
            
            logger.info(f"Resource optimization completed: "
                       f"{optimization_result['scaling_actions']} actions recommended")
            
            # Log optimization event
            if self.audit_trail:
                await self.audit_trail.create_event(
                    AuditEvent(
                        event_type=EventType.CONFIG_CHANGED,
                        device_id='cluster',
                        timestamp=datetime.utcnow(),
                        description="Resource optimization executed",
                        metadata=optimization_result
                    )
                )
            
            return optimization_result
        except Exception as e:
            logger.error(f"Resource optimization failed: {e}")
            return {'error': str(e)}
    
    async def get_audit_trail_summary(self, hours: int = 24) -> Dict:
        """Get audit trail summary for the specified period."""
        if not self.audit_trail:
            return {'error': 'Audit trail not enabled'}
        
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            events = self.audit_trail.get_events_since(since)
            
            summary = {
                'period': f"Last {hours} hours",
                'total_events': len(events),
                'event_types': {},
                'anomalies': [],
                'merkle_verification': None
            }
            
            for event in events:
                event_type = event.event_type.value
                summary['event_types'][event_type] = summary['event_types'].get(event_type, 0) + 1
                
                if event.event_type == EventType.ANOMALY_DETECTED:
                    summary['anomalies'].append({
                        'device_id': event.device_id,
                        'timestamp': event.timestamp.isoformat(),
                        'description': event.description
                    })
            
            # Get merkle verification
            summary['merkle_verification'] = self.audit_trail.verify_merkle_tree()
            
            logger.info(f"Audit summary: {summary['total_events']} events, "
                       f"{len(summary['anomalies'])} anomalies")
            
            return summary
        except Exception as e:
            logger.error(f"Failed to get audit trail summary: {e}")
            return {'error': str(e)}
    
    async def backend_operations_loop(self):
        """Main backend operations loop."""
        self.running = True
        iteration = 0
        
        try:
            while self.running:
                iteration += 1
                
                # Every minute: Get cluster status
                if iteration % 12 == 0:
                    status = await self.get_cluster_status()
                    logger.info(f"Cluster: {status['cluster_status']['utilization_pct']:.1%} "
                              f"utilized if cluster_status")
                
                # Every 5 minutes: Optimize resources
                if iteration % 60 == 0:
                    await self.optimize_resource_allocation()
                
                # Every 10 minutes: Get audit trail summary
                if iteration % 120 == 0:
                    audit_summary = await self.get_audit_trail_summary(hours=1)
                    logger.info(f"Audit: {audit_summary['total_events']} events, "
                              f"{len(audit_summary['anomalies'])} anomalies")
                
                await asyncio.sleep(5)  # 5 second loop interval
        
        except asyncio.CancelledError:
            logger.info("Backend operations loop cancelled")
        except Exception as e:
            logger.error(f"Error in backend loop: {e}")
        finally:
            self.running = False
    
    async def run(self):
        """Run enhanced IoT backend."""
        await self.startup_backend()
        
        # Register some example fog nodes
        await self.register_fog_node(
            node_id="fog_node_1",
            location="warehouse_1",
            cpu_cores=8,
            memory_gb=16,
            storage_gb=256,
            network_latency_ms=2.5
        )
        
        await self.register_fog_node(
            node_id="fog_node_2",
            location="warehouse_2",
            cpu_cores=4,
            memory_gb=8,
            storage_gb=128,
            network_latency_ms=3.1
        )
        
        try:
            await self.backend_operations_loop()
        except KeyboardInterrupt:
            logger.info("Backend operations interrupted")
        finally:
            await self.shutdown_backend()


async def main():
    """Main IoT backend entry point."""
    iot_backend = EnhancedIoTBackend(
        enable_edge_computing=True,
        enable_audit_trail=True,
        enable_capacity_planning=True,
        kafka_brokers=["localhost:9092"],
        smart_contract_address="0x1234567890123456789012345678901234567890"
    )
    
    logger.info("Enhanced IoT backend initialized")
    
    try:
        await iot_backend.run()
    except Exception as e:
        logger.error(f"IoT backend failed: {e}")
    finally:
        logger.info("IoT backend shutdown complete")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
