# Kismet Elasticsearch Integration Guide

This guide covers the complete setup and testing of Kismet real-time data export to Elasticsearch with offline support and Kibana visualization.

## Overview

The Elasticsearch integration provides:
- **Real-time streaming** from Kismet to Elasticsearch
- **Offline mode** with local SQLite buffering
- **Store-and-forward** capability for disconnected environments
- **Automatic reconnection** and sync when connectivity is restored
- **Kibana-ready** data structure with geo-location support

## Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install elasticsearch websockets

# Or install all dependencies
pip install -r examples/requirements.txt
```

### 2. Test with Local Kismet

```bash
# Start in offline mode (no Elasticsearch required)
python3 kismet_elasticsearch_export.py --offline

# Test with console output first
python3 kismet_realtime_export.py --export-type console
```

### 3. Connect to Remote Elasticsearch

```bash
# Connect to remote Elasticsearch cluster
python3 kismet_elasticsearch_export.py \
    --es-hosts "https://your-elasticsearch-cluster:9200" \
    --es-username "elastic" \
    --es-password "your-password" \
    --index-prefix "kismet-field"
```

## Deployment Scenarios

### Scenario 1: Local Kismet + Remote Elasticsearch (Online)

**Use Case**: Kismet running locally with internet connection to remote Elasticsearch/Kibana

```bash
python3 kismet_elasticsearch_export.py \
    --kismet-host localhost \
    --es-hosts "https://your-cluster.elastic-cloud.com:9243" \
    --es-username "elastic" \
    --es-password "your-password" \
    --update-rate 5
```

### Scenario 2: Local Kismet + Offline Mode (Disconnected)

**Use Case**: Kismet running in field without internet connection

```bash
# Run in offline mode - data stored locally
python3 kismet_elasticsearch_export.py \
    --kismet-host localhost \
    --offline \
    --update-rate 1 \
    --buffer-db "field_data.db"
```

### Scenario 3: Sync Offline Data Later (Store-and-Forward)

**Use Case**: Sync collected offline data when connectivity is restored

```bash
# Sync offline data to Elasticsearch
python3 kismet_elasticsearch_export.py \
    --sync-only \
    --es-hosts "https://your-cluster.elastic-cloud.com:9243" \
    --es-username "elastic" \
    --es-password "your-password" \
    --buffer-db "field_data.db"
```

## Configuration Options

### Command Line Arguments

| Argument | Description | Default | Example |
|----------|-------------|---------|---------|
| `--kismet-host` | Kismet server hostname | localhost | 192.168.1.100 |
| `--kismet-port` | Kismet server port | 2501 | 2501 |
| `--update-rate` | Update rate in seconds | 5 | 1 |
| `--es-hosts` | Elasticsearch hosts | http://localhost:9200 | https://cluster.com:9200 |
| `--es-username` | Elasticsearch username | None | elastic |
| `--es-password` | Elasticsearch password | None | password123 |
| `--es-api-key` | Elasticsearch API key | None | base64-encoded-key |
| `--index-prefix` | Index prefix | kismet | kismet-field |
| `--offline` | Run in offline mode | False | --offline |
| `--sync-only` | Only sync offline data | False | --sync-only |
| `--buffer-db` | Offline buffer database | kismet_offline_buffer.db | field_data.db |

### Elasticsearch Authentication

**Username/Password Authentication**:
```bash
--es-username "elastic" --es-password "your-password"
```

**API Key Authentication**:
```bash
--es-api-key "your-base64-encoded-api-key"
```

**Multiple Elasticsearch Hosts**:
```bash
--es-hosts "https://node1:9200" "https://node2:9200" "https://node3:9200"
```

## Data Structure

### Device Index (`kismet-devices-YYYY.MM`)

```json
{
  "timestamp": "2025-01-21T16:30:45.123Z",
  "mac_addr": "aa:bb:cc:dd:ee:ff",
  "name": "iPhone",
  "username": "John's Phone",
  "phy_type": "IEEE802.11",
  "manufacturer": "Apple",
  "first_seen": 1642435845,
  "last_seen": 1642435945,
  "channel": "6",
  "frequency": 2437000,
  "total_packets": 1250,
  "tx_packets": 800,
  "rx_packets": 450,
  "data_size": 1048576,
  "signal_dbm": -45,
  "noise_dbm": -95,
  "snr_db": 50,
  "location": {
    "lat": 40.7128,
    "lon": -74.0060
  },
  "latitude": 40.7128,
  "longitude": -74.0060,
  "altitude": 10.5
}
```

### Event Index (`kismet-events-YYYY.MM`)

```json
{
  "timestamp": "2025-01-21T16:30:45.123Z",
  "event_type": "NEWDEVICE",
  "device_mac": "aa:bb:cc:dd:ee:ff",
  "event_data": {
    "device_key": "...",
    "additional_data": "..."
  }
}
```

## Kibana Dashboard Setup

### 1. Create Index Patterns

In Kibana, go to **Stack Management > Index Patterns**:

1. **Device Data Pattern**:
   - Index pattern: `kismet-devices-*`
   - Time field: `timestamp`

2. **Event Data Pattern**:
   - Index pattern: `kismet-events-*`
   - Time field: `timestamp`

### 2. Sample Visualizations

**Device Count Over Time**:
```json
{
  "query": {
    "match_all": {}
  },
  "aggs": {
    "devices_over_time": {
      "date_histogram": {
        "field": "timestamp",
        "calendar_interval": "1m"
      }
    }
  }
}
```

**Signal Strength Heatmap**:
```json
{
  "query": {
    "range": {
      "signal_dbm": {
        "gte": -100,
        "lte": 0
      }
    }
  },
  "aggs": {
    "signal_ranges": {
      "histogram": {
        "field": "signal_dbm",
        "interval": 10
      }
    }
  }
}
```

**Geographic Distribution** (if GPS data available):
```json
{
  "query": {
    "exists": {
      "field": "location"
    }
  },
  "aggs": {
    "device_locations": {
      "geohash_grid": {
        "field": "location",
        "precision": 5
      }
    }
  }
}
```

### 3. Sample Dashboard Panels

**Device Statistics Panel**:
- Metric: Count of unique `mac_addr`
- Time range: Last 24 hours
- Refresh: Every 30 seconds

**Manufacturer Breakdown**:
- Pie chart of `manufacturer` field
- Filter: Last 1 hour
- Top 10 manufacturers

**Signal Strength Timeline**:
- Line chart of average `signal_dbm`
- X-axis: `timestamp`
- Y-axis: Average signal strength
- Interval: 5 minutes

## Testing Procedures

### 1. Local Testing Setup

```bash
# Terminal 1: Start Kismet (if not already running)
sudo kismet

# Terminal 2: Test offline mode
python3 kismet_elasticsearch_export.py --offline --update-rate 1

# Terminal 3: Monitor buffer
watch -n 5 'sqlite3 kismet_offline_buffer.db "SELECT COUNT(*) as total_devices, COUNT(CASE WHEN synced=0 THEN 1 END) as unsynced FROM device_buffer"'
```

### 2. Elasticsearch Connection Test

```bash
# Test Elasticsearch connectivity
curl -u elastic:password "https://your-cluster:9200/_cluster/health"

# Test with minimal data
python3 kismet_elasticsearch_export.py \
    --es-hosts "https://your-cluster:9200" \
    --es-username "elastic" \
    --es-password "password" \
    --update-rate 10
```

### 3. Offline/Online Sync Test

```bash
# Step 1: Collect data offline
python3 kismet_elasticsearch_export.py --offline --update-rate 1 &
OFFLINE_PID=$!

# Let it run for a few minutes, then stop
sleep 300
kill $OFFLINE_PID

# Step 2: Check buffer status
sqlite3 kismet_offline_buffer.db "SELECT COUNT(*) FROM device_buffer WHERE synced=0"

# Step 3: Sync to Elasticsearch
python3 kismet_elasticsearch_export.py \
    --sync-only \
    --es-hosts "https://your-cluster:9200" \
    --es-username "elastic" \
    --es-password "password"

# Step 4: Verify in Kibana
# Check that data appears in kismet-devices-* indices
```

## Performance Considerations

### Local Buffer Performance

- **SQLite database**: Handles thousands of records efficiently
- **Disk space**: ~1KB per device record, ~500 bytes per event
- **Memory usage**: ~10-50MB for typical operation
- **Batch size**: 1000 records per sync operation (configurable)

### Elasticsearch Performance

- **Index strategy**: Monthly indices (`kismet-devices-2025.01`)
- **Sharding**: Single shard per index (suitable for moderate volume)
- **Refresh interval**: 30 seconds (balances performance vs. real-time)
- **Bulk operations**: Used for efficient data ingestion

### Network Considerations

- **Bandwidth**: ~2-10KB per device update
- **Compression**: Elasticsearch HTTP compression enabled
- **Retry logic**: Automatic retry with exponential backoff
- **Connection pooling**: Single persistent connection per client

## Troubleshooting

### Common Issues

**Connection refused to Kismet**:
```bash
# Check if Kismet is running
ps aux | grep kismet

# Check WebSocket endpoint
curl -I http://localhost:2501/devices/monitor

# Test with basic export first
python3 kismet_realtime_export.py --export-type console
```

**Elasticsearch connection errors**:
```bash
# Test basic connectivity
curl -u username:password "https://your-cluster:9200/_cluster/health"

# Check authentication
curl -u username:password "https://your-cluster:9200/_security/_authenticate"

# Verify SSL/TLS
curl -k -u username:password "https://your-cluster:9200/_cluster/health"
```

**Offline buffer issues**:
```bash
# Check buffer database
sqlite3 kismet_offline_buffer.db ".tables"
sqlite3 kismet_offline_buffer.db "SELECT COUNT(*) FROM device_buffer"

# Check disk space
df -h .

# Check file permissions
ls -la kismet_offline_buffer.db
```

### Debug Mode

Enable detailed logging:

```python
# Add to script or set environment variable
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or run with debug output:
```bash
python3 -u kismet_elasticsearch_export.py --offline 2>&1 | tee debug.log
```

### Buffer Management

**Check buffer status**:
```bash
sqlite3 kismet_offline_buffer.db "
SELECT 
    'Devices' as type,
    COUNT(*) as total,
    COUNT(CASE WHEN synced=0 THEN 1 END) as unsynced,
    MIN(created_at) as oldest,
    MAX(created_at) as newest
FROM device_buffer
UNION ALL
SELECT 
    'Events' as type,
    COUNT(*) as total,
    COUNT(CASE WHEN synced=0 THEN 1 END) as unsynced,
    MIN(created_at) as oldest,
    MAX(created_at) as newest
FROM event_buffer;
"
```

**Clean up old synced data**:
```bash
sqlite3 kismet_offline_buffer.db "
DELETE FROM device_buffer 
WHERE synced = 1 AND created_at < datetime('now', '-7 days');

DELETE FROM event_buffer 
WHERE synced = 1 AND created_at < datetime('now', '-7 days');

VACUUM;
"
```

## Production Deployment

### Systemd Service

Create `/etc/systemd/system/kismet-elasticsearch.service`:

```ini
[Unit]
Description=Kismet Elasticsearch Export
After=network.target
Wants=network.target

[Service]
Type=simple
User=kismet
Group=kismet
WorkingDirectory=/opt/kismet-export
ExecStart=/usr/bin/python3 kismet_elasticsearch_export.py \
    --es-hosts "https://your-cluster:9200" \
    --es-username "elastic" \
    --es-password "your-password" \
    --index-prefix "kismet-production"
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable kismet-elasticsearch
sudo systemctl start kismet-elasticsearch
sudo systemctl status kismet-elasticsearch
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt kismet_elasticsearch_export.py ./
RUN pip install -r requirements.txt

CMD ["python3", "kismet_elasticsearch_export.py"]
```

```yaml
version: '3.8'
services:
  kismet-elasticsearch:
    build: .
    environment:
      - KISMET_HOST=host.docker.internal
      - ES_HOSTS=https://your-cluster:9200
      - ES_USERNAME=elastic
      - ES_PASSWORD=your-password
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### Monitoring and Alerting

**Log monitoring**:
```bash
# Monitor service logs
journalctl -u kismet-elasticsearch -f

# Monitor sync statistics
grep "Background sync" /var/log/kismet-elasticsearch.log
```

**Health checks**:
```bash
# Check if process is running
pgrep -f kismet_elasticsearch_export

# Check buffer growth
watch -n 60 'sqlite3 kismet_offline_buffer.db "SELECT COUNT(*) FROM device_buffer WHERE synced=0"'
```

## Security Considerations

### Network Security
- Use HTTPS for Elasticsearch connections
- Configure firewall rules for Kismet access
- Use VPN for remote Elasticsearch access
- Enable Elasticsearch security features

### Data Privacy
- MAC addresses are personally identifiable
- Consider data anonymization for compliance
- Implement data retention policies
- Secure buffer database files

### Authentication
- Use strong Elasticsearch passwords
- Rotate API keys regularly
- Limit Elasticsearch user permissions
- Monitor access logs

## Integration Examples

### Custom Kibana Dashboards

**Real-time Device Monitoring**:
- Live count of active devices
- Signal strength distribution
- Manufacturer breakdown
- Geographic heat map (if GPS available)

**Security Analysis**:
- New device alerts
- Unusual signal patterns
- Device movement tracking
- Anomaly detection

**Performance Metrics**:
- Data ingestion rates
- Buffer utilization
- Sync performance
- Error rates

This comprehensive guide provides everything needed to deploy and test the Kismet Elasticsearch integration in various scenarios, from local testing to production deployment with offline capability.
