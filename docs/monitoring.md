# Monitoring Guide

This document covers monitoring, logging, and observability for the MCP system.

## Logging

### Log Configuration

MCP uses a structured logging system that can be configured in `mcp/config.py`:

```python
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": "mcp.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}
```

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General operational information
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error events that might still allow the application to continue
- **CRITICAL**: Critical events that may lead to application failure

### Log Categories

1. **Access Logs**
   ```python
   logger.info({
       "type": "access",
       "method": request.method,
       "path": request.path,
       "status": response.status_code,
       "duration_ms": duration
   })
   ```

2. **Plugin Logs**
   ```python
   logger.info({
       "type": "plugin",
       "plugin": plugin_name,
       "command": command,
       "status": status,
       "duration_ms": duration
   })
   ```

3. **Error Logs**
   ```python
   logger.error({
       "type": "error",
       "error": str(error),
       "traceback": traceback.format_exc(),
       "context": context
   })
   ```

4. **Audit Logs**
   ```python
   logger.info({
       "type": "audit",
       "action": action,
       "user": user,
       "details": sanitized_details
   })
   ```

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

## Health Checks

### Endpoint

MCP provides a health check endpoint at `/health`:

```python
@app.route('/health')
def health_check():
    return {
        "status": "healthy",
        "version": VERSION,
        "uptime": get_uptime(),
        "queue_size": get_queue_size(),
        "plugins": get_plugin_status()
    }
```

### Components

1. **Server Health**
   - Process status
   - Memory usage
   - CPU usage

2. **Plugin Health**
   - Plugin availability
   - Last execution time
   - Error rate

3. **Queue Health**
   - Queue size
   - Processing rate
   - Wait times

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