#!/bin/bash

# Kismet Real-Time Export Setup Script
# This script helps set up the complete export infrastructure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Kismet Real-Time Export Setup ==="
echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo ""
echo "Checking prerequisites..."

if ! command_exists docker; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi
echo "✅ Docker found"

if ! command_exists docker-compose; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
echo "✅ Docker Compose found"

if ! command_exists python3; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi
echo "✅ Python 3 found"

# Copy necessary files to examples directory
echo ""
echo "Setting up files..."

# Copy the main export script
if [ -f "$PROJECT_ROOT/kismet_realtime_export.py" ]; then
    cp "$PROJECT_ROOT/kismet_realtime_export.py" "$SCRIPT_DIR/"
    echo "✅ Copied kismet_realtime_export.py"
else
    echo "❌ kismet_realtime_export.py not found in project root"
    exit 1
fi

# Make scripts executable
chmod +x "$SCRIPT_DIR/docker_entrypoint.sh"
chmod +x "$SCRIPT_DIR/setup.sh"

echo "✅ Made scripts executable"

# Create Grafana provisioning directories
mkdir -p "$SCRIPT_DIR/grafana/provisioning/datasources"
mkdir -p "$SCRIPT_DIR/grafana/provisioning/dashboards"

# Create Grafana datasource configuration
cat > "$SCRIPT_DIR/grafana/provisioning/datasources/datasources.yml" << 'EOF'
apiVersion: 1

datasources:
  - name: InfluxDB
    type: influxdb
    access: proxy
    url: http://influxdb:8086
    jsonData:
      version: Flux
      organization: kismet-org
      defaultBucket: kismet-data
    secureJsonData:
      token: kismet-admin-token

  - name: PostgreSQL
    type: postgres
    access: proxy
    url: postgres:5432
    database: kismet_db
    user: kismet
    secureJsonData:
      password: kismet_password
EOF

echo "✅ Created Grafana datasource configuration"

# Function to show usage
show_usage() {
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     - Start all services with Docker Compose"
    echo "  stop      - Stop all services"
    echo "  logs      - Show logs from all services"
    echo "  status    - Show status of all services"
    echo "  test      - Test connection to Kismet server"
    echo "  clean     - Clean up Docker containers and volumes"
    echo "  install   - Install Python dependencies locally"
    echo ""
}

# Handle command line arguments
case "${1:-setup}" in
    start)
        echo ""
        echo "Starting Kismet export infrastructure..."
        cd "$SCRIPT_DIR"
        docker-compose up -d
        echo ""
        echo "✅ Services started!"
        echo ""
        echo "Access points:"
        echo "  - Grafana: http://localhost:3000 (admin/admin)"
        echo "  - InfluxDB: http://localhost:8086"
        echo "  - PostgreSQL: localhost:5432 (kismet/kismet_password)"
        echo "  - MQTT: localhost:1883"
        echo ""
        echo "To view logs: $0 logs"
        echo "To stop services: $0 stop"
        ;;
    
    stop)
        echo ""
        echo "Stopping services..."
        cd "$SCRIPT_DIR"
        docker-compose down
        echo "✅ Services stopped"
        ;;
    
    logs)
        cd "$SCRIPT_DIR"
        docker-compose logs -f
        ;;
    
    status)
        cd "$SCRIPT_DIR"
        docker-compose ps
        ;;
    
    test)
        echo ""
        echo "Testing connection to Kismet server..."
        cd "$PROJECT_ROOT"
        python3 kismet_realtime_export.py --kismet-host localhost --export-type console --update-rate 1 &
        TEST_PID=$!
        sleep 10
        kill $TEST_PID 2>/dev/null || true
        echo "✅ Test completed (check output above for connection status)"
        ;;
    
    clean)
        echo ""
        echo "Cleaning up Docker containers and volumes..."
        cd "$SCRIPT_DIR"
        docker-compose down -v --remove-orphans
        docker system prune -f
        echo "✅ Cleanup completed"
        ;;
    
    install)
        echo ""
        echo "Installing Python dependencies..."
        pip3 install -r "$SCRIPT_DIR/requirements.txt"
        echo "✅ Dependencies installed"
        ;;
    
    setup|*)
        echo "✅ Setup completed successfully!"
        echo ""
        echo "Next steps:"
        echo "1. Make sure Kismet is running on your system"
        echo "2. Run: $0 start    (to start the export infrastructure)"
        echo "3. Run: $0 test     (to test the connection)"
        echo ""
        echo "For standalone usage:"
        echo "  $0 install  (install Python dependencies)"
        echo "  python3 kismet_realtime_export.py --help"
        echo ""
        show_usage
        ;;
esac
