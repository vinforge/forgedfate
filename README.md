# ForgedFate - Kismet Wireless Network Detector with Enhanced Export Capabilities

[![License](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/gpl-2.0)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

ForgedFate is an enhanced version of the Kismet wireless network detector with powerful real-time data export capabilities and improved security features.

## 🚀 Features

### Core Kismet Capabilities
- **Wireless Network Detection** - Comprehensive 802.11 (WiFi), Bluetooth, and other wireless protocol detection
- **Real-time Monitoring** - Live device tracking and analysis
- **Multi-Protocol Support** - WiFi, Bluetooth, Zigbee, LoRa, and more
- **GPS Integration** - Location-aware wireless monitoring
- **Web Interface** - Modern web-based management and visualization

### Enhanced Export Capabilities
- **🔄 Real-time Data Export** - Stream device data to external systems
- **📊 Multiple Database Support** - PostgreSQL, InfluxDB, Elasticsearch
- **📡 MQTT Integration** - Publish data to MQTT brokers
- **💾 Offline Support** - Local SQLite buffering with store-and-forward
- **🐳 Docker Ready** - Containerized deployment with security updates

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- Git
- Docker (optional, for containerized deployment)

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/vinforge/ForgedFate.git
   cd ForgedFate
   ```

2. **Install Python dependencies:**
   ```bash
   cd kismet
   pip install -r examples/requirements.txt
   ```

3. **Build Kismet (if needed):**
   ```bash
   ./configure
   make
   sudo make install
   ```

### Docker Deployment

1. **Build the export container:**
   ```bash
   cd kismet/examples
   docker build -f Dockerfile.export -t kismet-export .
   ```

2. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

## 🔧 Configuration

### Real-time Export Clients

#### Console Export (Testing)
```bash
python kismet_realtime_export.py --export-type console
```

#### PostgreSQL Export
```bash
python kismet_realtime_export.py \
  --export-type postgres \
  --postgres-conn "postgresql://user:pass@localhost/kismet"
```

#### InfluxDB Export
```bash
python kismet_realtime_export.py \
  --export-type influxdb \
  --influx-url "http://localhost:8086" \
  --influx-token "your-token" \
  --influx-org "your-org" \
  --influx-bucket "kismet"
```

#### MQTT Export
```bash
python kismet_realtime_export.py \
  --export-type mqtt \
  --mqtt-host "localhost" \
  --mqtt-topic-prefix "kismet"
```

### Elasticsearch Export with Offline Support

#### Online Mode
```bash
python kismet_elasticsearch_export.py \
  --es-hosts "http://localhost:9200" \
  --es-username "elastic" \
  --es-password "password"
```

#### Offline Mode (Local Storage)
```bash
python kismet_elasticsearch_export.py --offline
```

#### Sync Offline Data
```bash
python kismet_elasticsearch_export.py --sync-only
```

## 📊 Supported Export Formats

| Export Type | Description | Use Case |
|-------------|-------------|----------|
| **Console** | Terminal output | Testing and debugging |
| **PostgreSQL** | Relational database | Structured data analysis |
| **InfluxDB** | Time-series database | Metrics and monitoring |
| **MQTT** | Message broker | IoT integration |
| **Elasticsearch** | Search and analytics | Log analysis and visualization |

## 🐳 Docker Configuration

The project includes a complete Docker setup with:

- **Security Updates** - Latest Python 3.12-slim base image
- **Non-root Execution** - Runs as unprivileged user
- **Multi-service Support** - PostgreSQL, InfluxDB, MQTT, Elasticsearch
- **Volume Persistence** - Data persistence across container restarts

### Docker Compose Services

```yaml
services:
  kismet-export:     # Main export service
  postgres:          # PostgreSQL database
  influxdb:          # InfluxDB time-series database
  mosquitto:         # MQTT broker
  elasticsearch:     # Elasticsearch search engine
```

## 📁 Project Structure

```
ForgedFate/
├── kismet/                          # Main Kismet source code
│   ├── kismet_realtime_export.py    # Real-time export client
│   ├── kismet_elasticsearch_export.py # Elasticsearch export with offline support
│   ├── examples/                    # Docker and configuration examples
│   │   ├── docker-compose.yml       # Multi-service Docker setup
│   │   ├── Dockerfile.export        # Export service container
│   │   ├── requirements.txt         # Python dependencies
│   │   └── ...                     # Configuration files
│   ├── ELASTICSEARCH_GUIDE.md       # Elasticsearch integration guide
│   ├── README_REALTIME_EXPORT.md    # Real-time export documentation
│   └── DIAGNOSTIC_FIXES.md          # Recent fixes and improvements
└── README.md                        # This file
```

## 🔒 Security Features

- **Updated Base Images** - Latest Python 3.12-slim with security patches
- **Non-root Containers** - All services run as unprivileged users
- **Minimal Attack Surface** - Only necessary packages installed
- **Secure Defaults** - Authentication required for database connections

## 📖 Documentation

- **[Real-time Export Guide](kismet/README_REALTIME_EXPORT.md)** - Detailed export client documentation
- **[Elasticsearch Integration](kismet/ELASTICSEARCH_GUIDE.md)** - Elasticsearch setup and usage
- **[Docker Examples](kismet/examples/EXAMPLES.md)** - Container deployment examples
- **[Diagnostic Fixes](kismet/DIAGNOSTIC_FIXES.md)** - Recent improvements and fixes
- **[Official Kismet Docs](https://www.kismetwireless.net/docs/)** - Complete Kismet documentation

## 🚀 Quick Examples

### Monitor and Export to Multiple Destinations
```bash
# Start Kismet server
sudo kismet

# Export to PostgreSQL in real-time
python kismet_realtime_export.py --export-type postgres \
  --postgres-conn "postgresql://kismet:password@localhost/kismet_db"

# Export to Elasticsearch with offline support
python kismet_elasticsearch_export.py \
  --es-hosts "http://localhost:9200"

# Publish to MQTT for IoT integration
python kismet_realtime_export.py --export-type mqtt \
  --mqtt-host "mqtt.example.com" \
  --mqtt-topic-prefix "wireless/kismet"
```

### Docker Deployment
```bash
# Start all services
cd kismet/examples
docker-compose up -d

# View logs
docker-compose logs -f kismet-export

# Scale export services
docker-compose up -d --scale kismet-export=3
```

## 🛠️ Development

### Dependencies Resolved
All Python import issues have been resolved:
- ✅ `elasticsearch` - Elasticsearch client
- ✅ `asyncpg` - PostgreSQL async driver
- ✅ `influxdb-client` - InfluxDB client
- ✅ `paho-mqtt` - MQTT client
- ✅ `websockets` - WebSocket client
- ✅ `asyncio-mqtt` - Async MQTT support

### Recent Improvements
- Updated Docker base image for security
- Added comprehensive offline support
- Improved error handling and logging
- Enhanced documentation and examples
- Resolved all diagnostic issues

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the GNU General Public License v2.0 - see the [LICENSE](kismet/LICENSE) file for details.

## 🙏 Acknowledgments

- **Kismet Wireless** - Original Kismet project and community
- **Contributors** - All developers who have contributed to this enhanced version
- **Open Source Community** - For the amazing tools and libraries used

## 📞 Support

- **Issues** - Report bugs and request features via GitHub Issues
- **Documentation** - Check the docs directory for detailed guides
- **Community** - Join the Kismet community forums and discussions

---

**ForgedFate** - Enhancing wireless network detection with powerful export capabilities and modern deployment options.
