# ForgedFate Filebeat Integration Guide

This guide shows you how to easily integrate Kismet logs with Elasticsearch using our automated Filebeat integration tool.

## 🚀 Quick Start

### Option 1: Web Interface (Recommended)
1. Start ForgedFate Kismet
2. Open web interface at `http://localhost:2501`
3. Go to **API Configuration** → **Elasticsearch Export**
4. Click **"Setup Filebeat Integration"**
5. Fill in your Elasticsearch details
6. Copy and run the generated command

### Option 2: Command Line
```bash
# Navigate to Kismet directory
cd /path/to/ForgedFate/kismet

# Run the integration tool
sudo python3 filebeat_integration.py \
    --elasticsearch-url "https://your-elasticsearch:9200" \
    --username "your-username" \
    --password "your-password" \
    --device-name "your-device-name"
```

## 📋 Prerequisites

### 1. Install Filebeat
```bash
# Download and install Filebeat
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.14.0-amd64.deb
sudo dpkg -i filebeat-8.14.0-amd64.deb
```

### 2. Install Python Dependencies
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip python3-yaml
pip3 install pyyaml
```

### 3. Ensure Kismet Has Generated Logs
```bash
# Run Kismet to generate some logs first
sudo kismet

# Verify logs exist
ls -la /opt/kismet/logs/Kismet-*/
```

## 🔧 Advanced Configuration

### Custom Log Directory
If your Kismet logs are in a different location:

```bash
# Edit the integration script
nano filebeat_integration.py

# Change this line:
self.kismet_log_dir = "/your/custom/log/path"
```

### Multiple Elasticsearch Clusters
For multiple clusters, run the tool multiple times with different configurations:

```bash
# Production cluster
sudo python3 filebeat_integration.py \
    --elasticsearch-url "https://prod-es:9200" \
    --username "prod-user" \
    --index-prefix "kismet-prod"

# Development cluster  
sudo python3 filebeat_integration.py \
    --elasticsearch-url "https://dev-es:9200" \
    --username "dev-user" \
    --index-prefix "kismet-dev"
```

### SSL Configuration
For custom SSL settings:

```bash
sudo python3 filebeat_integration.py \
    --elasticsearch-url "https://secure-es:9200" \
    --ssl-verify certificate \
    --username "secure-user" \
    --password "secure-password"
```

## 📊 What Gets Created

### Elasticsearch Indices
The integration creates separate indices for each log type:

- `kismet-devices` - All detected devices
- `kismet-bluetooth` - Bluetooth-specific devices  
- `kismet-wifi` - WiFi devices and networks
- `kismet-packets` - Raw packet data
- `kismet-alerts` - Security alerts and notifications

### Filebeat Configuration
The tool generates a complete Filebeat configuration including:

- **Input streams** for each log type
- **JSON parsing** for structured data
- **Field enrichment** with device and source information
- **Index routing** to appropriate Elasticsearch indices
- **Error handling** and retry logic

## 🔍 Verification

### Check Filebeat Status
```bash
# Service status
sudo systemctl status filebeat

# Live logs
sudo journalctl -u filebeat -f

# Test configuration
sudo filebeat test config
sudo filebeat test output
```

### Verify Data in Elasticsearch
```bash
# Check indices
curl -X GET "your-elasticsearch:9200/_cat/indices/kismet-*?v"

# Sample data
curl -X GET "your-elasticsearch:9200/kismet-devices/_search?size=1&pretty"
```

### Web Interface Verification
1. Open Kibana or Elasticsearch web interface
2. Look for indices starting with `kismet-`
3. Create index patterns for each log type
4. Build dashboards and visualizations

## 🛠️ Troubleshooting

### Common Issues

**Filebeat not starting:**
```bash
# Check configuration syntax
sudo filebeat test config

# Check permissions
sudo chown root:root /etc/filebeat/filebeat.yml
sudo chmod 600 /etc/filebeat/filebeat.yml
```

**No data appearing in Elasticsearch:**
```bash
# Check if logs exist
ls -la /opt/kismet/logs/Kismet-*/

# Check Filebeat is reading files
sudo filebeat test input

# Check Elasticsearch connectivity
sudo filebeat test output
```

**Permission errors:**
```bash
# Ensure Filebeat can read Kismet logs
sudo usermod -a -G kismet filebeat
sudo chmod g+r /opt/kismet/logs/Kismet-*/*
```

### Log Analysis
```bash
# Filebeat logs
sudo tail -f /var/log/filebeat/filebeat

# Kismet logs
sudo tail -f /opt/kismet/logs/Kismet-*/kismet.log

# System logs
sudo journalctl -u filebeat -u kismet -f
```

## 🎯 Best Practices

### Performance Optimization
- **Adjust scan frequency** based on log volume
- **Use appropriate batch sizes** for high-throughput scenarios
- **Monitor Elasticsearch cluster health** during initial data load

### Security
- **Use strong passwords** for Elasticsearch authentication
- **Enable SSL/TLS** for production deployments
- **Restrict Filebeat permissions** to minimum required

### Monitoring
- **Set up alerts** for Filebeat service failures
- **Monitor index sizes** and implement retention policies
- **Track data ingestion rates** and performance metrics

## 📈 Integration with ForgedFate Features

### Connectivity Testing
The Filebeat integration works seamlessly with ForgedFate's connectivity testing:

1. **Test Elasticsearch connection** first using the connectivity tester
2. **Verify credentials** work before setting up Filebeat
3. **Monitor connection health** in real-time
4. **Get diagnostic reports** if issues arise

### Real-time Monitoring
- **Background health checks** ensure Elasticsearch remains accessible
- **Automatic alerts** if connectivity is lost
- **Performance metrics** track data flow rates

### Diagnostic Reports
- **Comprehensive troubleshooting** information
- **Network path analysis** for connectivity issues
- **Configuration validation** and recommendations

## 🔄 Maintenance

### Regular Tasks
```bash
# Update Filebeat configuration
sudo python3 filebeat_integration.py --dry-run

# Rotate logs
sudo logrotate /etc/logrotate.d/filebeat

# Check disk space
df -h /var/log/filebeat
df -h /opt/kismet/logs
```

### Updates
When updating ForgedFate:
1. **Backup current Filebeat configuration**
2. **Re-run integration tool** to update configuration
3. **Test connectivity** using ForgedFate's testing features
4. **Verify data flow** continues normally

## 📞 Support

For issues with the Filebeat integration:

1. **Check this guide** for common solutions
2. **Use ForgedFate's diagnostic tools** for connectivity issues
3. **Review Filebeat and Elasticsearch logs** for detailed error information
4. **Test individual components** (Filebeat config, ES connectivity, log files)

The ForgedFate Filebeat integration makes it easy to get your wireless monitoring data into Elasticsearch for powerful analysis and visualization!
