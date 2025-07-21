# Kismet Real-Time Data Export

This document describes the real-time data export solution for Kismet, allowing you to stream device data and events to external databases and systems in real-time.

## Overview

The real-time export system leverages Kismet's existing WebSocket infrastructure to provide:

- **Real-time device monitoring** via `/devices/monitor` endpoint
- **Event streaming** via `/eventbus/events` endpoint  
- **Multiple export destinations** (PostgreSQL, InfluxDB, MQTT, Console)
- **Configurable update rates** and field filtering
- **Automatic reconnection** and error handling

## Quick Start

### 1. Basic Console Output (Testing)

```bash
# Test connection to Kismet server
python3 kismet_realtime_export.py --kismet-host localhost --export-type console

# With custom update rate
python3 kismet_realtime_export.py --kismet-host 192.168.1.100 --update-rate 1 --export-type console
```

### 2. PostgreSQL Export

```bash
# Install dependencies
pip install asyncpg

# Export to PostgreSQL
python3 kismet_realtime_export.py \
    --export-type postgres \
    --postgres-conn "postgresql://user:password@localhost:5432/kismet_db"
```

### 3. InfluxDB Export (Time Series)

```bash
# Install dependencies
pip install influxdb-client

# Export to InfluxDB
python3 kismet_realtime_export.py \
    --export-type influxdb \
    --influx-url "http://localhost:8086" \
    --influx-token "your-influxdb-token" \
    --influx-org "your-org" \
    --influx-bucket "kismet-data"
```

### 4. MQTT Export

```bash
# Install dependencies
pip install paho-mqtt

# Export to MQTT broker
python3 kismet_realtime_export.py \
    --export-type mqtt \
    --mqtt-host "mqtt.example.com" \
    --mqtt-topic-prefix "kismet" \
    --mqtt-username "user" \
    --mqtt-password "pass"
```

## Data Schema

### Device Data Structure

Each device update contains the following normalized fields:

```json
{
    "timestamp": "2025-01-17T16:30:45.123456",
    "mac_addr": "aa:bb:cc:dd:ee:ff",
    "name": "Device Name",
    "username": "Custom User Name",
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
    "latitude": 40.7128,
    "longitude": -74.0060,
    "altitude": 10.5
}
```

### Event Data Structure

Events from the event bus include:

```json
{
    "event_type": "NEWDEVICE",
    "timestamp": "2025-01-17T16:30:45.123456",
    "device_key": "...",
    "event_data": { ... }
}
```

## Database Schemas

### PostgreSQL Schema

The PostgreSQL exporter automatically creates this table:

```sql
CREATE TABLE kismet_devices (
    mac_addr TEXT PRIMARY KEY,
    name TEXT,
    username TEXT,
    phy_type TEXT,
    manufacturer TEXT,
    first_seen BIGINT,
    last_seen BIGINT,
    channel TEXT,
    frequency BIGINT,
    total_packets BIGINT,
    tx_packets BIGINT,
    rx_packets BIGINT,
    data_size BIGINT,
    signal_dbm INTEGER,
    noise_dbm INTEGER,
    snr_db INTEGER,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    altitude DOUBLE PRECISION,
    last_updated TIMESTAMP DEFAULT NOW()
);
```

### InfluxDB Schema

Data is stored in two measurements:

**device_metrics** (time series data):
- Tags: `mac_addr`, `phy_type`, `manufacturer`
- Fields: `signal_dbm`, `noise_dbm`, `snr_db`, `total_packets`, etc.
- Timestamp: Device last seen time

**kismet_events** (event data):
- Fields: `event_data` (JSON)
- Timestamp: Event occurrence time

### MQTT Topics

Device data is published to:
```
kismet/devices/{mac_addr_with_underscores}
```

Events are published to:
```
kismet/events
```

## Configuration Options

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--kismet-host` | Kismet server hostname | localhost |
| `--kismet-port` | Kismet server port | 2501 |
| `--update-rate` | Update rate in seconds | 5 |
| `--export-type` | Export destination | console |

### PostgreSQL Options

| Argument | Description | Required |
|----------|-------------|----------|
| `--postgres-conn` | Connection string | Yes |

Example: `postgresql://user:pass@host:5432/dbname`

### InfluxDB Options

| Argument | Description | Required |
|----------|-------------|----------|
| `--influx-url` | InfluxDB URL | Yes |
| `--influx-token` | Authentication token | Yes |
| `--influx-org` | Organization name | Yes |
| `--influx-bucket` | Bucket name | Yes |

### MQTT Options

| Argument | Description | Default |
|----------|-------------|---------|
| `--mqtt-host` | MQTT broker hostname | Required |
| `--mqtt-port` | MQTT broker port | 1883 |
| `--mqtt-topic-prefix` | Topic prefix | kismet |
| `--mqtt-username` | Username | None |
| `--mqtt-password` | Password | None |

## Performance Considerations

### Typical Performance

- **Small environment** (10-50 devices): ~1-5 updates/second
- **Medium environment** (100-500 devices): ~20-100 updates/second  
- **Large environment** (1000+ devices): ~200+ updates/second

### Optimization Tips

1. **Adjust update rate**: Higher rates = more data, lower latency
2. **Database indexing**: Index on `mac_addr`, `last_seen`, `phy_type`
3. **Network bandwidth**: JSON payloads are ~2-10KB per device
4. **Connection pooling**: Use connection pooling for high-volume scenarios

### Memory Usage

- **Client memory**: ~10-50MB for typical usage
- **Network buffer**: Automatically managed by WebSocket library
- **Database connections**: Single connection per exporter

## Monitoring and Troubleshooting

### Statistics Output

The client displays runtime statistics:

```
=== Kismet Export Statistics ===
Runtime: 300.5 seconds
Devices processed: 1,250
Alerts processed: 15
Processing rate: 4.16 devices/second
Last update: 2025-01-17 16:35:22
```

### Common Issues

**Connection refused**:
- Verify Kismet server is running
- Check hostname/port configuration
- Ensure WebSocket endpoints are enabled

**Authentication errors**:
- Kismet WebSocket endpoints require authentication
- Configure API keys in Kismet if needed

**Database connection errors**:
- Verify database credentials and connectivity
- Check firewall settings
- Ensure database exists and user has permissions

**High memory usage**:
- Reduce update rate
- Check for connection leaks
- Monitor database query performance

### Logging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration Examples

### Grafana Dashboard (InfluxDB)

Create visualizations using InfluxDB queries:

```sql
-- Device count over time
SELECT count(DISTINCT("mac_addr")) FROM "device_metrics" 
WHERE time >= now() - 1h GROUP BY time(5m)

-- Signal strength distribution
SELECT mean("signal_dbm") FROM "device_metrics" 
WHERE time >= now() - 1h GROUP BY "phy_type", time(1m)

-- Top manufacturers
SELECT count(DISTINCT("mac_addr")) FROM "device_metrics" 
WHERE time >= now() - 1h GROUP BY "manufacturer"
```

### Alerting (PostgreSQL)

Create alerts for new devices:

```sql
-- Devices seen in last 5 minutes
SELECT mac_addr, name, phy_type, signal_dbm 
FROM kismet_devices 
WHERE last_updated > NOW() - INTERVAL '5 minutes';

-- Strong signal devices (potential proximity)
SELECT mac_addr, name, signal_dbm, latitude, longitude
FROM kismet_devices 
WHERE signal_dbm > -30 AND last_updated > NOW() - INTERVAL '1 hour';
```

### MQTT Integration

Subscribe to device updates:

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    if msg.topic.startswith("kismet/devices/"):
        device_data = json.loads(msg.payload.decode())
        print(f"Device update: {device_data['mac_addr']} - {device_data['signal_dbm']}dBm")

client = mqtt.Client()
client.on_message = on_message
client.connect("mqtt-broker", 1883, 60)
client.subscribe("kismet/devices/+")
client.loop_forever()
```

## Advanced Usage

### Custom Field Selection

Modify the `monitor_config` in the script to select specific fields:

```python
"fields": [
    "kismet.device.base.macaddr",
    "kismet.device.base.signal",
    "kismet.device.base.location"
]
```

### Multiple Export Destinations

Run multiple instances with different export types:

```bash
# Terminal 1: PostgreSQL export
python3 kismet_realtime_export.py --export-type postgres --postgres-conn "..."

# Terminal 2: MQTT export  
python3 kismet_realtime_export.py --export-type mqtt --mqtt-host "..."
```

### Custom Exporters

Extend the system by creating custom exporter classes:

```python
class CustomExporter:
    async def export_device(self, device_info):
        # Custom export logic
        pass
        
    async def export_event(self, event_data):
        # Custom event handling
        pass
        
    async def close(self):
        # Cleanup
        pass
```

## Security Considerations

### Network Security

- Use TLS/SSL for database connections
- Configure MQTT with authentication and encryption
- Restrict network access to Kismet server
- Use VPN for remote connections

### Data Privacy

- Device MAC addresses are personally identifiable
- Consider MAC address hashing for privacy
- Implement data retention policies
- Secure database access with proper authentication

### Access Control

- Limit access to export client
- Use read-only database users where possible
- Monitor export client logs for suspicious activity
- Implement rate limiting if needed

## Future Enhancements

### Planned Features

1. **Delta updates**: Only send changed fields
2. **Compression**: WebSocket compression for large payloads
3. **Batching**: Group multiple updates in single message
4. **Filtering**: Server-side filtering by device type, signal strength, etc.
5. **Encryption**: End-to-end encryption for sensitive data

### Plugin Development

The next phase will include:

1. **Native Kismet plugin**: C++ plugin integrated into Kismet server
2. **Enhanced MQTT publisher**: Built-in MQTT publishing capability
3. **Webhook support**: HTTP POST to custom endpoints
4. **Database plugins**: Direct database integration without external client

## Support

For issues and questions:

1. Check Kismet documentation: https://www.kismetwireless.net/docs/
2. Review WebSocket endpoint documentation
3. Test with console exporter first
4. Check database connectivity independently
5. Enable debug logging for detailed troubleshooting

## License

This export client follows the same license as Kismet (GPL v2).
