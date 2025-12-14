# Horizontal Pod Autoscaling (HPA) Configuration

## Overview

Horizontal Pod Autoscaling automatically scales the number of pods based on observed metrics like CPU and memory usage.

## Configuration Details

### Backend Service HPA

```yaml
minReplicas: 2
maxReplicas: 10
targetCPU: 70%
targetMemory: 80%
```

- **Min**: Always maintain at least 2 backend pods for high availability
- **Max**: Scale up to 10 pods for peak load
- **Scale-up**: Aggressive (100% increase every 15 seconds)
- **Scale-down**: Conservative (50% decrease every 60 seconds)

### Celery Worker HPA

```yaml
minReplicas: 1
maxReplicas: 5
targetCPU: 75%
```

- Scales based on CPU usage of background job processors
- More conservative scaling compared to frontend

### Frontend Service HPA

```yaml
minReplicas: 2
maxReplicas: 8
targetCPU: 70%
```

- Maintains minimum 2 instances for load balancing
- Scales to handle web traffic spikes

## Metrics Server

HPA requires the Kubernetes Metrics Server to collect resource metrics.

### Install Metrics Server

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify installation
kubectl get deployment metrics-server -n kube-system
```

## Monitoring HPA Status

### Check HPA Status

```bash
# Get HPA status
kubectl get hpa -n iot-network

# Detailed HPA information
kubectl describe hpa backend-hpa -n iot-network

# Watch HPA in real-time
kubectl get hpa -n iot-network -w
```

### Example Output

```
NAME            REFERENCE                    TARGETS           MINPODS   MAXPODS   REPLICAS   AGE
backend-hpa     Deployment/backend           45%/70%, 60%/80%  2         10        3          5m
frontend-hpa    Deployment/frontend          35%/70%           2         8         2          5m
```

## Custom Metrics Autoscaling

### Using Prometheus Metrics

For advanced autoscaling based on custom metrics from Prometheus:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa-custom
  namespace: iot-network
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

### Install Prometheus Adapter

```bash
# Add Prometheus community Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus Adapter
helm install prometheus-adapter prometheus-community/prometheus-adapter \
  --namespace monitoring \
  --values prometheus-adapter-values.yaml
```

## Pod Disruption Budget (PDB)

Ensures high availability during voluntary disruptions (maintenance, updates):

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: backend-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: backend
```

## Performance Tuning

### Adjust Scaling Behavior

```yaml
behavior:
  scaleUp:
    stabilizationWindowSeconds: 0      # Scale up immediately
    policies:
    - type: Percent
      value: 100                       # Double capacity every 15 seconds
      periodSeconds: 15
    selectPolicy: Max                  # Choose most aggressive policy

  scaleDown:
    stabilizationWindowSeconds: 300    # Wait 5 minutes before scaling down
    policies:
    - type: Percent
      value: 50                        # Reduce by 50%
      periodSeconds: 60                # Every 60 seconds
    selectPolicy: Min                  # Choose most conservative policy
```

### Modify Target Metrics

```bash
# Edit HPA to change CPU threshold
kubectl patch hpa backend-hpa -n iot-network --type='json' \
  -p='[{"op": "replace", "path": "/spec/metrics/0/resource/target/averageUtilization", "value": 80}]'
```

## Troubleshooting

### HPA Not Scaling

```bash
# Check if metrics are available
kubectl describe hpa backend-hpa -n iot-network

# Verify metrics server
kubectl get deployment metrics-server -n kube-system

# Check resource requests
kubectl describe pod -n iot-network | grep -A 2 "Requests"
```

### Metrics Not Available

```bash
# Check metrics
kubectl top pods -n iot-network
kubectl top nodes

# If no metrics, ensure resource requests are defined in pod spec
```

### Rapid Scaling (Thrashing)

Increase stabilization window to prevent rapid up/down scaling:

```yaml
behavior:
  scaleDown:
    stabilizationWindowSeconds: 600   # Increase from 300 to 600
```

## Best Practices

1. **Always set resource requests**: HPA needs CPU/memory requests to calculate metrics
2. **Set appropriate thresholds**: 70-80% CPU, 80-90% memory are good starting points
3. **Use multiple metrics**: Combine CPU and memory for better decisions
4. **Implement PDB**: Ensure minimum availability during disruptions
5. **Monitor scaling events**: Track HPA decisions in prometheus/grafana
6. **Test autoscaling**: Simulate load to verify scaling behavior
7. **Use custom metrics**: For application-specific scaling decisions

## Monitoring HPA with Prometheus

### Prometheus Queries

```promql
# Number of desired replicas
kube_hpa_status_desired_replicas

# Current number of replicas
kube_hpa_status_current_replicas

# HPA scaling events
kube_hpa_status_current_replicas != kube_hpa_status_desired_replicas
```

## References

- [Kubernetes HPA Documentation](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Metrics Server](https://github.com/kubernetes-sigs/metrics-server)
- [Prometheus Adapter](https://github.com/kubernetes-sigs/prometheus-adapter)
- [Pod Disruption Budget](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
