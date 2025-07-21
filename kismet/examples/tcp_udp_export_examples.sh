#!/bin/bash
# Kismet TCP/UDP Export Examples
# These examples show how to send Kismet data to configurable servers

echo "=== Kismet TCP/UDP Export Examples ==="
echo ""

echo "1. TCP Export to 172.18.18.20:8685 (JSON format - default)"
echo "python kismet_realtime_export.py --export-type tcp --server-host 172.18.18.20 --server-port 8685"
echo ""

echo "2. UDP Export to 172.18.18.20:8685 (JSON format)"
echo "python kismet_realtime_export.py --export-type udp --server-host 172.18.18.20 --server-port 8685"
echo ""

echo "3. TCP Export with CSV format"
echo "python kismet_realtime_export.py --export-type tcp --server-host 172.18.18.20 --server-port 8685 --data-format csv"
echo ""

echo "4. UDP Export with simple format"
echo "python kismet_realtime_export.py --export-type udp --server-host 172.18.18.20 --server-port 8685 --data-format simple"
echo ""

echo "5. TCP Export to different server/port"
echo "python kismet_realtime_export.py --export-type tcp --server-host 192.168.1.100 --server-port 9999"
echo ""

echo "6. TCP Export with custom Kismet server and update rate"
echo "python kismet_realtime_export.py --export-type tcp --kismet-host 192.168.1.50 --kismet-port 2501 --update-rate 2 --server-host 172.18.18.20 --server-port 8685"
echo ""

echo "=== Data Format Examples ==="
echo ""
echo "JSON Format (default):"
echo '{"type": "device", "data": {...}, "sequence": 1, "timestamp": 1642781234.567}'
echo ""
echo "CSV Format:"
echo "DEVICE,AA:BB:CC:DD:EE:FF,IEEE802.11,-45,1234,2024-01-21T12:34:56"
echo ""
echo "Simple Format:"
echo "DEVICE|AA:BB:CC:DD:EE:FF|IEEE802.11|-45|1234"
echo ""

echo "=== Configuration Notes ==="
echo "- Default server: 172.18.18.20:8685 (configurable)"
echo "- Server/port can be changed via --server-host and --server-port"
echo "- No hardcoded values - all configurable via command line"
echo "- TCP provides reliable delivery, UDP is faster but may lose packets"
echo "- JSON format includes full device data, CSV/simple are compact"
echo ""

echo "To run an example, copy and paste one of the commands above."
