# Kismet Real-Time Export Examples

This directory contains complete examples and configurations for deploying the Kismet real-time export system.

## Quick Start

### 1. Setup and Test

```bash
# Make setup script executable
chmod +x setup.sh

# Run initial setup
./setup.sh

# Install Python dependencies locally
./setup.sh install

# Test connection to Kismet (make sure Kismet is running first)
./setup.sh test
```

### 2. Docker Deployment (Recommended)

```bash
# Start all services (PostgreSQL, InfluxDB, MQTT, Grafana, Export clients)
./setup.sh start

# Check service status
./setup.sh status

# View logs
./setup.sh logs

# Stop services
./setup.sh stop
```

### 3. Standalone Usage

```bash
# Console output (testing)
python3 kismet_realtime_export.py --kismet-host localhost --export-type console

# PostgreSQL export
python3 kismet_realtime_export.py \
    --export-type postgres \
    --postgres-conn "postgresql://user:pass@localhost:5432/kismet_db"

# InfluxDB export
python3 kismet_realtime_export.py \
    --export-type influxdb \
    --influx-url "http://localhost:8086" \
    --influx-token "your-token" \
    --influx-org "your-org" \
    --influx-bucket "kismet-data"

# MQTT export
python3 kismet_realtime_export.py \
    --export-type mqtt \
    --mqtt-host "localhost" \
    --mqtt-topic-prefix "kismet"
```

## File Structure

```
examples/
├── docker-compose.yml          # Complete Docker stack
├── Dockerfile.export           # Export client container
├── requirements.txt            # Python dependencies
├── docker_entrypoint.sh        # Container startup script
├── init-db.sql                # PostgreSQL initialization
├── mosquitto.conf             # MQTT broker configuration
├── setup.sh                   # Setup and management script
├── EXAMPLES.md                # This file
└── grafana/
    └── provisioning/
        └── datasources/
            └── datasources.yml # Grafana data sources
```

## Configuration Examples

### Environment Variables (Docker)

```bash
# Kismet connection
KISMET_HOST=192.168.1.100
KISMET_PORT=2501
UPDATE_RATE=5

# PostgreSQL export
EXPORT_TYPE=postgres
POSTGRES_CONN=postgresql://kismet:password@postgres:5432/kismet_db

# InfluxDB export
EXPORT_TYPE=influxdb
INFLUX_URL=http://influxdb:8086
INFLUX_TOKEN=your-token
INFLUX_ORG=your-org
INFLUX_BUCKET=kismet-data

# MQTT export
EXPORT_TYPE=mqtt
MQTT_HOST=mosquitto
MQTT_PORT=1883
MQTT_TOPIC_PREFIX=kismet
MQTT_USERNAME=user
MQTT_PASSWORD=pass
```

### Custom Docker Compose

```yaml
version: '3.8'
services:
  kismet-export:
    build:
      context: .
      dockerfile: Dockerfile.export
    environment:
      KISMET_HOST: your-kismet-server
      EXPORT_TYPE: postgres
      POSTGRES_CONN: postgresql://user:pass@your-db:5432/kismet
      UPDATE_RATE: 1
    restart: unless-stopped
```

## Database Queries

### PostgreSQL Examples

```sql
-- Recent device activity
SELECT mac_addr, name, phy_type, signal_dbm, last_updated 
FROM kismet_devices 
WHERE last_updated > NOW() - INTERVAL '5 minutes'
ORDER BY last_updated DESC;

-- Device statistics by PHY type
SELECT * FROM device_stats;

-- Strong signal devices (close proximity)
SELECT mac_addr, name, signal_dbm, latitude, longitude
FROM kismet_devices 
WHERE signal_dbm > -40 
AND last_updated > NOW() - INTERVAL '1 hour';

-- Device summary
SELECT * FROM get_device_summary();

-- Cleanup old data (older than 30 days)
SELECT cleanup_old_data(30);
```

### InfluxDB Examples (Flux)

```flux
// Device count over time
from(bucket: "kismet-data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> group(columns: ["_time"])
  |> count()
  |> yield(name: "device_count")

// Average signal strength by PHY type
from(bucket: "kismet-data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "device_metrics" and r._field == "signal_dbm")
  |> group(columns: ["phy_type"])
  |> mean()
  |> yield(name: "avg_signal")

// Top manufacturers by device count
from(bucket: "kismet-data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "device_metrics")
  |> group(columns: ["manufacturer"])
  |> count()
  |> sort(columns: ["_value"], desc: true)
  |> limit(n: 10)
```

## MQTT Integration Examples

### Python MQTT Subscriber

```python
import paho.mqtt.client as mqtt
import json

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe("kismet/devices/+")
    client.subscribe("kismet/events")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = json.loads(msg.payload.decode())
    
    if topic.startswith("kismet/devices/"):
        mac_addr = payload['mac_addr']
        signal = payload['signal_dbm']
        print(f"Device {mac_addr}: {signal}dBm")
    elif topic == "kismet/events":
        print(f"Event: {payload}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)
client.loop_forever()
```

### Node.js MQTT Subscriber

```javascript
const mqtt = require('mqtt');
const client = mqtt.connect('mqtt://localhost:1883');

client.on('connect', () => {
    console.log('Connected to MQTT broker');
    client.subscribe('kismet/devices/+');
    client.subscribe('kismet/events');
});

client.on('message', (topic, message) => {
    const data = JSON.parse(message.toString());
    
    if (topic.startsWith('kismet/devices/')) {
        console.log(`Device ${data.mac_addr}: ${data.signal_dbm}dBm`);
    } else if (topic === 'kismet/events') {
        console.log('Event:', data);
    }
});
```

## Grafana Dashboard Examples

### Device Count Panel

```json
{
  "targets": [
    {
      "query": "SELECT COUNT(*) FROM kismet_devices WHERE last_updated > NOW() - INTERVAL '5 minutes'",
      "refId": "A"
    }
  ],
  "type": "stat",
  "title": "Active Devices"
}
```

### Signal Strength Time Series

```json
{
  "targets": [
    {
      "query": "from(bucket: \"kismet-data\") |> range(start: -1h) |> filter(fn: (r) => r._measurement == \"device_metrics\" and r._field == \"signal_dbm\") |> aggregateWindow(every: 1m, fn: mean)",
      "refId": "A"
    }
  ],
  "type": "timeseries",
  "title": "Average Signal Strength"
}
```

## Troubleshooting

### Common Issues

**Connection refused to Kismet**:
```bash
# Check if Kismet is running
ps aux | grep kismet

# Check if WebSocket endpoints are accessible
curl -I http://localhost:2501/devices/monitor

# Test with console export first
python3 kismet_realtime_export.py --export-type console
```

**Database connection errors**:
```bash
# Test PostgreSQL connection
psql -h localhost -U kismet -d kismet_db -c "SELECT version();"

# Test InfluxDB connection
curl -I http://localhost:8086/health

# Check Docker services
docker-compose ps
docker-compose logs postgres
```

**MQTT connection issues**:
```bash
# Test MQTT broker
mosquitto_pub -h localhost -t test -m "hello"
mosquitto_sub -h localhost -t test

# Check broker logs
docker-compose logs mosquitto
```

### Debug Mode

Enable debug logging in the export client:

```python
# Add to kismet_realtime_export.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Tuning

**High CPU usage**:
- Increase update rate (reduce frequency)
- Reduce field selection
- Use database connection pooling

**High memory usage**:
- Monitor WebSocket buffer sizes
- Check for connection leaks
- Reduce batch sizes

**Network issues**:
- Check firewall settings
- Monitor bandwidth usage
- Use compression if available

## Production Deployment

### Security Considerations

1. **Database Security**:
   - Use strong passwords
   - Enable SSL/TLS connections
   - Restrict network access
   - Regular security updates

2. **MQTT Security**:
   - Enable authentication
   - Use TLS encryption
   - Configure access control lists
   - Monitor connection logs

3. **Network Security**:
   - Use VPN for remote access
   - Firewall configuration
   - Network segmentation
   - Regular security audits

### Monitoring and Alerting

```bash
# Monitor export client health
docker-compose exec kismet-export-postgres ps aux

# Check database performance
docker-compose exec postgres pg_stat_activity

# Monitor MQTT broker
docker-compose exec mosquitto mosquitto_sub -t '$SYS/#'
```

### Backup and Recovery

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U kismet kismet_db > backup.sql

# Backup InfluxDB
docker-compose exec influxdb influx backup /tmp/backup

# Backup configuration
tar -czf config-backup.tar.gz docker-compose.yml *.conf *.sql
```

## Advanced Usage

### Custom Exporters

Create custom export destinations by extending the base exporter class:

```python
class CustomExporter:
    async def export_device(self, device_info):
        # Custom logic here
        pass
        
    async def export_event(self, event_data):
        # Custom event handling
        pass
        
    async def close(self):
        # Cleanup
        pass
```

### Multiple Kismet Servers

Monitor multiple Kismet servers simultaneously:

```yaml
services:
  kismet-export-server1:
    build: .
    environment:
      KISMET_HOST: server1.example.com
      EXPORT_TYPE: postgres
      POSTGRES_CONN: postgresql://user:pass@db:5432/kismet_server1
      
  kismet-export-server2:
    build: .
    environment:
      KISMET_HOST: server2.example.com
      EXPORT_TYPE: postgres
      POSTGRES_CONN: postgresql://user:pass@db:5432/kismet_server2
```

### Load Balancing

Use multiple export clients for high-volume scenarios:

```yaml
services:
  kismet-export-1:
    build: .
    environment:
      KISMET_HOST: kismet-server
      EXPORT_TYPE: postgres
      UPDATE_RATE: 10
      
  kismet-export-2:
    build: .
    environment:
      KISMET_HOST: kismet-server
      EXPORT_TYPE: influxdb
      UPDATE_RATE: 5
```

## Support

For additional help:

1. Check the main README_REALTIME_EXPORT.md
2. Review Kismet documentation
3. Test with console exporter first
4. Enable debug logging
5. Check service logs with `./setup.sh logs`
