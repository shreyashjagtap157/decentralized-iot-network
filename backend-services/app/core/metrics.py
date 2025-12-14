from prometheus_client import Counter, Histogram, Gauge

device_registrations_total = Counter('device_registrations_total', 'Total device registrations', ['status'])
active_devices_gauge = Gauge('active_devices_total', 'Number of active devices')
device_heartbeat_latency = Histogram('device_heartbeat_duration_seconds', 'Device heartbeat processing time')

bytes_relayed_total = Counter('network_bytes_relayed_total', 'Total bytes relayed', ['device_id'])
connection_quality_gauge = Gauge('connection_quality_score', 'Connection quality score', ['device_id'])
usage_reports_total = Counter('usage_reports_total', 'Total usage reports received', ['status'])

compensation_transactions_total = Counter('compensation_transactions_total', 'Total compensation transactions', ['status'])
blockchain_interaction_duration = Histogram('blockchain_interaction_duration_seconds', 'Blockchain interaction time')
pending_rewards_gauge = Gauge('pending_rewards_total', 'Total pending rewards in native token')
