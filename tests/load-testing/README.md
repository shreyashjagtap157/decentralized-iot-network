# Load Testing Guide

## Overview

Load testing is performed using **k6**, a modern load testing tool that allows scripting in JavaScript.

## Installation

### Install k6

```bash
# macOS
brew install k6

# Linux (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install k6

# Windows (via Chocolatey)
choco install k6

# Or download from https://k6.io/docs/getting-started/installation/
```

## Running Tests

### API Load Test

```bash
# Run basic API load test
k6 run tests/load-testing/api-load-test.js

# Run with custom settings
k6 run --vus 50 --duration 5m tests/load-testing/api-load-test.js

# Run with output to file
k6 run --out csv=results.csv tests/load-testing/api-load-test.js
```

### Database Load Test

```bash
# Run database-focused load test
k6 run tests/load-testing/database-load-test.js

# Ramp up test: gradually increase load
k6 run -s 10s:10 -s 20s:50 -s 10s:100 tests/load-testing/database-load-test.js
```

## Test Scenarios

### Basic Load Test
- 10 virtual users
- 30-second duration
- Tests basic endpoints: registration, device data submission, health check

### Database Load Test
- 20 virtual users
- 1-minute duration
- Tests database query performance with read-heavy operations

## Interpreting Results

### Key Metrics

| Metric | Description |
|--------|-------------|
| `http_req_duration` | Time taken for HTTP request to complete |
| `http_req_failed` | Percentage of failed requests |
| `iterations` | Total number of test iterations completed |
| `vus` | Virtual users (concurrent connections) |

### Example Output

```
    ✓ health check status is 200
    ✓ user registration status is 200
    ✓ device registration status is 200
    ✓ data submission status is 200

    checks.........................: 100.00% ✓ 400     ✗ 0
    data_received..................: 34 kB   1.1 kB/s
    data_sent......................: 32 kB   1.1 kB/s
    dropped_iterations.............: 0
    http_req_blocked...............: avg=0.22ms   min=0.04ms   med=0.12ms   max=3.52ms   p(90)=0.42ms   p(95)=0.72ms
    http_req_connecting............: avg=0.06ms   min=0.00ms   med=0.00ms   max=1.18ms   p(90)=0.00ms   p(95)=0.00ms
    http_req_duration..............: avg=11.75ms  min=1.53ms   med=10.44ms  max=98.78ms  p(90)=19.12ms  p(95)=25.33ms ✓
    http_req_failed................: 0.00%   ✓ 0       ✗ 400
    http_req_receiving.............: avg=0.51ms   min=0.04ms   med=0.46ms   max=3.24ms   p(90)=0.75ms   p(95)=0.89ms
    http_req_sending...............: avg=0.26ms   min=0.04ms   med=0.18ms   max=1.60ms   p(90)=0.50ms   p(95)=0.70ms
    http_req_tls_handshaking.......: avg=0.00ms   min=0.00ms   med=0.00ms   max=0.00ms   p(90)=0.00ms   p(95)=0.00ms
    http_req_waiting...............: avg=10.98ms  min=1.36ms   med=9.71ms   max=96.93ms  p(90)=18.38ms  p(95)=24.85ms
    http_reqs.......................: 400     13.07/s
    iteration_duration.............: avg=4.03s    min=4.00s    med=4.03s    max=4.09s    p(90)=4.06s    p(95)=4.07s
    iterations.....................: 100     3.27/s
    vus............................: 10      min=10    max=10
    vus_max........................: 10      min=10    max=10
```

## Performance Targets

### Target Thresholds

- **95% of requests should complete in < 500ms** (API endpoints)
- **Error rate < 10%** (acceptable for load testing)
- **99% of requests should complete in < 2000ms** (database queries)

## Advanced Testing

### Spike Test

```javascript
export const options = {
  stages: [
    { duration: '2m', target: 2 },
    { duration: '5m', target: 100 },   // Spike
    { duration: '2m', target: 2 },
  ],
};
```

### Soak Test

```javascript
export const options = {
  stages: [
    { duration: '5m', target: 100 },
    { duration: '8h', target: 100 },   // Long duration
    { duration: '5m', target: 0 },
  ],
};
```

### Stress Test

```javascript
export const options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 200 },
    { duration: '5m', target: 300 },
    { duration: '5m', target: 400 },
    { duration: '5m', target: 500 },
    { duration: '2m', target: 0 },
  ],
};
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Load Testing

on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2 AM

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: grafana/k6-action@v0.3.0
        with:
          filename: tests/load-testing/api-load-test.js
```

## Monitoring and Reporting

### Export Results

```bash
# JSON output
k6 run --out json=results.json tests/load-testing/api-load-test.js

# CSV output
k6 run --out csv=results.csv tests/load-testing/api-load-test.js

# InfluxDB integration
k6 run -o influxdb=http://localhost:8086/k6 tests/load-testing/api-load-test.js
```

### Analyze Results

```bash
# Install jq for JSON parsing
sudo apt-get install jq

# Extract specific metrics
cat results.json | jq '.metrics."http_req_duration".values'
```

## Best Practices

1. **Realistic Scenarios**: Mimic real user behavior
2. **Gradual Ramp-up**: Start small and increase load gradually
3. **Monitor Resources**: Track CPU, memory, and network usage
4. **Isolate Tests**: Run tests in a dedicated environment
5. **Regular Testing**: Schedule load tests regularly
6. **Document Results**: Keep baseline metrics for comparison
7. **Fail Fast**: Set appropriate thresholds and fail on violations

## References

- [k6 Documentation](https://k6.io/docs/)
- [k6 API Reference](https://k6.io/docs/javascript-api/)
- [k6 Best Practices](https://k6.io/docs/misc/best-practices/)
