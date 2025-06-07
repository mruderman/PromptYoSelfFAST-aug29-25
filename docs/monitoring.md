# Monitoring Guide (STDIO Edition)

This document covers monitoring, logging, and observability for the MCP STDIO daemon.

## Logging

- All requests and terminal responses are logged using `logger.py`.
- Logs include job ID, plugin, action, status, and duration.
- Sensitive data is never logged.
- Log files are written to `mcp.log`.

## Observability

- Monitor CPU and RAM usage of the MCP process.
- Monitor queue length and job durations.
- Use log analysis for troubleshooting and auditing.

## Health Checks

- Use the `health` command via STDIO to check daemon status.
- Example:
  ```json
  {"id": "abcd", "command": "health"}
  ```
  Response:
  ```json
  {"id": "abcd", "status": "success", "payload": "ok"}
  ```

## Troubleshooting

- Check `mcp.log` for errors and job status.
- Ensure all plugin output is valid JSON.
- Use the `reload-help` command to refresh help cache if plugins change.

## Metrics

### Prometheus Metrics

MCP exposes metrics in Prometheus format at `/metrics`:

```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter(
    'mcp_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'mcp_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

# Plugin metrics
PLUGIN_EXECUTION_COUNT = Counter(
    'mcp_plugin_executions_total',
    'Total number of plugin executions',
    ['plugin', 'command', 'status']
)

PLUGIN_EXECUTION_DURATION = Histogram(
    'mcp_plugin_execution_duration_seconds',
    'Plugin execution duration in seconds',
    ['plugin', 'command']
)

# Queue metrics
QUEUE_SIZE = Gauge(
    'mcp_queue_size',
    'Current size of the job queue',
    ['plugin']
)

QUEUE_WAIT_TIME = Histogram(
    'mcp_queue_wait_seconds',
    'Time jobs spend in queue',
    ['plugin']
)
```

### Metric Types

1. **Counters**
   - Total requests
   - Successful/failed operations
   - Error counts

2. **Gauges**
   - Queue size
   - Active connections
   - Resource usage

3. **Histograms**
   - Request duration
   - Plugin execution time
   - Queue wait time

## Alerting

### Alert Rules

1. **High Error Rate**
   ```yaml
   - alert: HighErrorRate
     expr: rate(mcp_requests_total{status=~"5.."}[5m]) > 0.1
     for: 5m
     labels:
       severity: critical
     annotations:
       summary: High error rate detected
   ```

2. **Queue Backlog**
   ```yaml
   - alert: QueueBacklog
     expr: mcp_queue_size > 100
     for: 10m
     labels:
       severity: warning
     annotations:
       summary: Job queue is backing up
   ```

3. **Slow Responses**
   ```yaml
   - alert: SlowResponses
     expr: histogram_quantile(0.95, rate(mcp_request_duration_seconds_bucket[5m])) > 1
     for: 5m
     labels:
       severity: warning
     annotations:
       summary: 95th percentile of requests are slow
   ```

### Alert Channels

1. **Email**
   ```yaml
   receivers:
   - name: 'email'
     email_configs:
     - to: 'team@example.com'
       from: 'alerts@example.com'
   ```

2. **Slack**
   ```yaml
   receivers:
   - name: 'slack'
     slack_configs:
     - channel: '#alerts'
       api_url: 'https://hooks.slack.com/services/...'
   ```

3. **PagerDuty**
   ```yaml
   receivers:
   - name: 'pagerduty'
     pagerduty_configs:
     - service_key: '...'
   ```

## Dashboards

### Grafana Dashboard

1. **Overview**
   - Request rate
   - Error rate
   - Response time
   - Queue size

2. **Plugin Performance**
   - Execution count
   - Success rate
   - Duration
   - Queue wait time

3. **System Health**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network traffic

### Dashboard Panels

1. **Request Metrics**
   ```json
   {
     "title": "Request Rate",
     "type": "graph",
     "datasource": "Prometheus",
     "targets": [{
       "expr": "rate(mcp_requests_total[5m])",
       "legendFormat": "{{method}} {{endpoint}}"
     }]
   }
   ```

2. **Plugin Metrics**
   ```json
   {
     "title": "Plugin Execution Rate",
     "type": "graph",
     "datasource": "Prometheus",
     "targets": [{
       "expr": "rate(mcp_plugin_executions_total[5m])",
       "legendFormat": "{{plugin}} {{command}}"
     }]
   }
   ```

3. **Queue Metrics**
   ```json
   {
     "title": "Queue Size",
     "type": "gauge",
     "datasource": "Prometheus",
     "targets": [{
       "expr": "mcp_queue_size",
       "legendFormat": "{{plugin}}"
     }]
   }
   ```

## Troubleshooting

### Common Issues

1. **High Error Rate**
   - Check plugin logs
   - Verify configuration
   - Monitor resource usage

2. **Slow Performance**
   - Check queue size
   - Monitor plugin execution time
   - Review system resources

3. **Queue Backlog**
   - Check plugin health
   - Review execution times
   - Consider scaling

### Debug Tools

1. **Log Analysis**
   ```bash
   # View recent errors
   grep "ERROR" mcp.log | tail -n 100

   # Check plugin execution times
   grep "plugin" mcp.log | jq 'select(.duration_ms > 1000)'
   ```

2. **Metric Queries**
   ```bash
   # Check error rate
   curl -s localhost:5000/metrics | grep mcp_requests_total

   # Check queue size
   curl -s localhost:5000/metrics | grep mcp_queue_size
   ```

3. **Health Check**
   ```bash
   # Check system health
   curl -s localhost:5000/health | jq
   ``` 