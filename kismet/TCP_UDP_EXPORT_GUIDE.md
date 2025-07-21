# TCP/UDP Export Guide for Kismet

This guide explains how to use the new TCP and UDP export capabilities in the Kismet real-time export client.

## Overview

The enhanced `kismet_realtime_export.py` now supports sending device data to any configurable TCP or UDP server, making it easy to integrate with custom applications, logging systems, or data processing pipelines.

## Key Features

- **Configurable Endpoints**: No hardcoded IP addresses or ports
- **Multiple Protocols**: Both TCP (reliable) and UDP (fast) support
- **Flexible Data Formats**: JSON, CSV, or simple pipe-delimited formats
- **Automatic Reconnection**: TCP connections automatically reconnect on failure
- **Sequence Numbering**: Data integrity with sequence numbers and timestamps

## Quick Start

### Basic TCP Export
```bash
# Send to 172.18.18.20:8685 (default values)
python kismet_realtime_export.py --export-type tcp

# Send to custom server
python kismet_realtime_export.py --export-type tcp --server-host 192.168.1.100 --server-port 9999
```

### Basic UDP Export
```bash
# Send to 172.18.18.20:8685 (default values)
python kismet_realtime_export.py --export-type udp

# Send to custom server
python kismet_realtime_export.py --export-type udp --server-host 192.168.1.100 --server-port 9999
```

## Command Line Options

### Core Options
- `--export-type {tcp,udp}` - Choose TCP or UDP transport
- `--server-host HOST` - Target server IP/hostname (default: 172.18.18.20)
- `--server-port PORT` - Target server port (default: 8685)
- `--data-format {json,csv,simple}` - Data format (default: json)

### Kismet Connection Options
- `--kismet-host HOST` - Kismet server hostname (default: localhost)
- `--kismet-port PORT` - Kismet server port (default: 2501)
- `--update-rate SECONDS` - Update rate in seconds (default: 5)

## Data Formats

### JSON Format (Default)
Full device data with metadata:
```json
{
  "type": "device",
  "data": {
    "timestamp": "2024-01-21T12:34:56.789",
    "mac_addr": "AA:BB:CC:DD:EE:FF",
    "phy_type": "IEEE802.11",
    "signal_dbm": -45,
    "total_packets": 1234,
    "manufacturer": "Apple",
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "sequence": 1,
  "timestamp": 1642781696.789
}
```

### CSV Format
Compact comma-separated values:
```
DEVICE,AA:BB:CC:DD:EE:FF,IEEE802.11,-45,1234,2024-01-21T12:34:56.789
```

### Simple Format
Pipe-delimited key fields:
```
DEVICE|AA:BB:CC:DD:EE:FF|IEEE802.11|-45|1234
```

## Usage Examples

### 1. Default Configuration
```bash
# Uses 172.18.18.20:8685 with JSON format
python kismet_realtime_export.py --export-type tcp
```

### 2. Custom Server with CSV Format
```bash
python kismet_realtime_export.py \
  --export-type tcp \
  --server-host 10.0.0.50 \
  --server-port 8080 \
  --data-format csv
```

### 3. High-Speed UDP with Simple Format
```bash
python kismet_realtime_export.py \
  --export-type udp \
  --server-host 172.18.18.20 \
  --server-port 8685 \
  --data-format simple \
  --update-rate 1
```

### 4. Remote Kismet with Custom Export
```bash
python kismet_realtime_export.py \
  --export-type tcp \
  --kismet-host 192.168.1.50 \
  --kismet-port 2501 \
  --server-host 172.18.18.20 \
  --server-port 8685 \
  --update-rate 2
```

## TCP vs UDP Comparison

| Feature | TCP | UDP |
|---------|-----|-----|
| **Reliability** | Guaranteed delivery | Best effort |
| **Speed** | Slower (connection overhead) | Faster |
| **Connection** | Persistent connection | Connectionless |
| **Reconnection** | Automatic | N/A |
| **Use Case** | Critical data logging | High-throughput monitoring |

## Server Implementation

Your receiving server should listen on the configured port and handle the data format you've chosen:

### Simple Python TCP Server Example
```python
import socket
import json

def tcp_server(host='0.0.0.0', port=8685):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"Listening on {host}:{port}")
        
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    
                    # Parse JSON data
                    try:
                        message = json.loads(data.decode('utf-8').strip())
                        print(f"Received: {message}")
                    except json.JSONDecodeError:
                        print(f"Raw data: {data.decode('utf-8')}")

if __name__ == "__main__":
    tcp_server()
```

### Simple Python UDP Server Example
```python
import socket
import json

def udp_server(host='0.0.0.0', port=8685):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, port))
        print(f"UDP server listening on {host}:{port}")
        
        while True:
            data, addr = s.recvfrom(1024)
            try:
                message = json.loads(data.decode('utf-8'))
                print(f"From {addr}: {message}")
            except json.JSONDecodeError:
                print(f"Raw from {addr}: {data.decode('utf-8')}")

if __name__ == "__main__":
    udp_server()
```

## Integration Examples

### Log to File
```bash
# TCP with JSON format for detailed logging
python kismet_realtime_export.py --export-type tcp --data-format json > kismet_log.json
```

### Real-time Dashboard
```bash
# UDP with simple format for fast dashboard updates
python kismet_realtime_export.py --export-type udp --data-format simple --update-rate 1
```

### SIEM Integration
```bash
# TCP with CSV format for security monitoring
python kismet_realtime_export.py --export-type tcp --data-format csv --server-host siem.company.com --server-port 514
```

## Troubleshooting

### Connection Issues
- Verify the target server is listening on the specified port
- Check firewall rules between Kismet client and target server
- For TCP: Monitor logs for connection/reconnection messages
- For UDP: No connection errors will be shown (fire-and-forget)

### Data Format Issues
- JSON: Full device data, larger messages
- CSV: Compact but limited fields
- Simple: Minimal data, fastest processing

### Performance Tuning
- Use UDP for high-frequency updates (--update-rate 1)
- Use TCP for guaranteed delivery of critical data
- Choose simple format for minimal bandwidth usage
- Adjust --update-rate based on your monitoring needs

## Security Considerations

- **Network Security**: Ensure secure network between Kismet and target server
- **Authentication**: Consider implementing authentication in your receiving server
- **Encryption**: Use VPN or SSH tunneling for sensitive data transmission
- **Access Control**: Restrict access to the target server port

## Future Enhancements

The TCP/UDP export system is designed to be extensible. Future versions may include:
- TLS/SSL encryption support
- Authentication mechanisms
- Compression options
- Batch transmission modes
- Custom field selection

---

For more examples and advanced usage, see `examples/tcp_udp_export_examples.sh`.
