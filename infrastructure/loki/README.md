# Centralized Logging with Loki and Promtail

## Overview

This setup provides centralized logging for the Decentralized IoT Network using Grafana Loki and Promtail.

**Loki**: A log aggregation system designed to work with Prometheus and Grafana.
**Promtail**: An agent that collects logs from pods and ships them to Loki.

## Architecture

```
┌─────────────────────────────────────────┐
│ Kubernetes Pods (All Namespaces)       │
│ ├─ Backend Services                   │
│ ├─ Web Dashboard                      │
│ ├─ Celery Workers                     │
│ └─ Other Services                     │
└─────────────────────────────────────────┘
            ↓
    Promtail (DaemonSet)
            ↓
    Loki (StatefulSet)
            ↓
    Grafana Dashboard
```

## Installation

### Deploy Loki and Promtail

```bash
# Deploy to Kubernetes
kubectl apply -f infrastructure/k8s/loki-deployment.yaml

# Verify deployment
kubectl get pods -n monitoring
kubectl get svc -n monitoring
```

### Verify Installation

```bash
# Check Loki is running
kubectl logs -n monitoring loki-0

# Check Promtail is collecting logs
kubectl get daemonset -n monitoring
kubectl logs -n monitoring -l app=promtail | head -20
```

## Configuration

### Loki Configuration

Located in `loki-config` ConfigMap:
- **Chunk idle period**: 3 minutes
- **Max streams per user**: 10,000
- **Retention**: Disabled (set retention period in production)
- **Storage backend**: Filesystem (use S3 for production)

### Promtail Configuration

Located in `promtail-config` ConfigMap:
- **Push URL**: `http://loki:3100/loki/api/v1/push`
- **Scrape targets**: All Kubernetes pods with labels
- **Relabel rules**: Extract app name, namespace, and pod name

## Querying Logs

### From Grafana Dashboard

1. Add Loki as a data source in Grafana
2. Go to Explore tab
3. Select Loki data source
4. Use LogQL to query logs

### LogQL Examples

```logql
# Get all logs from backend service
{app="backend"}

# Get all logs from iot-network namespace
{namespace="iot-network"}

# Get error logs
{app="backend"} | "ERROR"

# Parse JSON logs
{app="backend"} | json | level="error"

# Count logs by pod
count_over_time({namespace="iot-network"}[5m])

# Show recent 100 logs
{namespace="iot-network"} | tail 100
```

## Structured Logging in Backend

### Python Logging Configuration

```python
import json
import logging
from pythonjsonlogger import jsonlogger

# Configure JSON logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Usage
logger.info("Device registered", extra={"device_id": "dev-001", "user_id": "user-001"})
logger.error("Device registration failed", extra={"error": "duplicate_id"})
```

### Using Correlation IDs

```python
import uuid
from contextvars import ContextVar

# Store correlation ID in context
correlation_id_var = ContextVar('correlation_id', default=None)

def set_correlation_id():
    correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id

# Use in logging
logger.info(
    "Processing device data",
    extra={
        "correlation_id": correlation_id_var.get(),
        "device_id": "dev-001",
        "data": request_data
    }
)
```

## Monitoring and Alerts

### Set Up Loki Alerts

Create PrometheusRule for log pattern matching:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: loki-alerts
  namespace: monitoring
spec:
  groups:
  - name: loki.rules
    interval: 30s
    rules:
    - alert: HighErrorRate
      expr: |
        count_over_time({namespace="iot-network"} | "ERROR"[5m]) > 10
      for: 5m
      annotations:
        summary: "High error rate detected in logs"
```

## Performance Optimization

### Log Volume Reduction

1. **Sampling**: Reduce log volume for high-frequency events
2. **Log Levels**: Only ship ERROR and WARN in production
3. **Filter**: Exclude noisy services or endpoints

### Retention Policies

```yaml
# In loki-config.yaml
table_manager:
  retention_enabled: true
  retention_period: 7 days  # Adjust as needed
```

## Scaling Loki

### For High-Volume Logs

Use Loki in distributed mode:

```yaml
# Use object storage (S3, GCS)
storage_config:
  s3:
    s3: s3://your-bucket
    endpoint: s3.amazonaws.com
```

### Increase Promtail Resources

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "200m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## Troubleshooting

### Loki not receiving logs

```bash
# Check Promtail configuration
kubectl get cm -n monitoring promtail-config -o yaml

# Check Promtail logs
kubectl logs -n monitoring -l app=promtail

# Check network connectivity
kubectl exec -n monitoring loki-0 -- curl -v http://localhost:3100/loki/api/v1/status/buildinfo
```

### High disk usage

```bash
# Enable retention and reduce storage
kubectl set env statefulset/loki -n monitoring LOKI_RETENTION=7d

# Use object storage instead of filesystem
```

### Slow queries

```bash
# Check Loki logs for performance issues
kubectl logs -n monitoring loki-0 | grep "query"

# Optimize LogQL queries
# Use specific labels: {app="backend"} instead of {namespace="iot-network"}
```

## Best Practices

1. **Use structured logging**: Always log JSON format
2. **Add correlation IDs**: Track requests across services
3. **Set appropriate retention**: Balance cost and compliance
4. **Monitor Loki resources**: Track disk usage and query performance
5. **Use labels wisely**: Avoid high-cardinality labels
6. **Archive old logs**: Export to S3 or archival storage

## References

- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [LogQL Documentation](https://grafana.com/docs/loki/latest/logql/)
- [Promtail Documentation](https://grafana.com/docs/loki/latest/clients/promtail/)
- [Structured Logging](https://grafana.com/docs/loki/latest/logql/log_queries/)
