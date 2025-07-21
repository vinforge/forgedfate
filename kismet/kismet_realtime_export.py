#!/usr/bin/env python3
"""
Kismet Real-Time Data Export Client
Connects to Kismet WebSocket endpoints and exports device data to external systems
"""

import asyncio
import websockets
import json
import argparse
import logging
import time
import socket
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import signal
import sys

# Database adapters
try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    INFLUXDB_AVAILABLE = True
except ImportError:
    INFLUXDB_AVAILABLE = False

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

class KismetExportClient:
    """Main client for connecting to Kismet and exporting data"""
    
    def __init__(self, kismet_host: str = "localhost", kismet_port: int = 2501,
                 update_rate: int = 5, export_type: str = "console"):
        self.kismet_host = kismet_host
        self.kismet_port = kismet_port
        self.update_rate = update_rate
        self.export_type = export_type
        self.running = False
        self.websocket = None
        self.exporter = None
        
        # Statistics
        self.stats = {
            'devices_processed': 0,
            'alerts_processed': 0,
            'start_time': None,
            'last_update': None
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    async def connect_and_monitor(self):
        """Connect to Kismet WebSocket and start monitoring"""
        uri = f"ws://{self.kismet_host}:{self.kismet_port}/devices/monitor"
        
        try:
            self.logger.info(f"Connecting to Kismet at {uri}")
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                self.running = True
                self.stats['start_time'] = time.time()
                
                # Configure device monitoring
                monitor_config = {
                    "monitor": "*",  # Monitor all devices
                    "rate": self.update_rate,
                    "request": 1,
                    "format": "json",
                    "fields": [
                        "kismet.device.base.macaddr",
                        "kismet.device.base.name",
                        "kismet.device.base.username",
                        "kismet.device.base.phyname",
                        "kismet.device.base.signal",
                        "kismet.device.base.location",
                        "kismet.device.base.last_time",
                        "kismet.device.base.first_time",
                        "kismet.device.base.packets.total",
                        "kismet.device.base.packets.tx",
                        "kismet.device.base.packets.rx",
                        "kismet.device.base.datasize",
                        "kismet.device.base.channel",
                        "kismet.device.base.frequency",
                        "kismet.device.base.manuf"
                    ]
                }
                
                await websocket.send(json.dumps(monitor_config))
                self.logger.info(f"Started monitoring devices with {self.update_rate}s update rate")
                
                # Process incoming messages
                async for message in websocket:
                    if not self.running:
                        break
                        
                    try:
                        device_data = json.loads(message)
                        await self.process_device_update(device_data)
                        
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse JSON message: {e}")
                    except Exception as e:
                        self.logger.error(f"Error processing device update: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket connection closed")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            
    async def connect_event_bus(self):
        """Connect to Kismet event bus for alerts and system events"""
        uri = f"ws://{self.kismet_host}:{self.kismet_port}/eventbus/events"
        
        try:
            self.logger.info(f"Connecting to Kismet event bus at {uri}")
            async with websockets.connect(uri) as websocket:
                
                async for message in websocket:
                    if not self.running:
                        break
                        
                    try:
                        event_data = json.loads(message)
                        await self.process_event(event_data)
                        
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse event JSON: {e}")
                    except Exception as e:
                        self.logger.error(f"Error processing event: {e}")
                        
        except Exception as e:
            self.logger.error(f"Event bus connection error: {e}")
            
    async def process_device_update(self, device_data: Dict[str, Any]):
        """Process a device update message"""
        self.stats['devices_processed'] += 1
        self.stats['last_update'] = time.time()
        
        # Extract key device information
        device_info = self.extract_device_info(device_data)
        
        # Export to configured destination
        if self.exporter:
            await self.exporter.export_device(device_info)
            
    async def process_event(self, event_data: Dict[str, Any]):
        """Process an event bus message"""
        self.stats['alerts_processed'] += 1
        
        if self.exporter:
            await self.exporter.export_event(event_data)
            
    def extract_device_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize device information"""
        device_info = {
            'timestamp': datetime.now().isoformat(),
            'mac_addr': raw_data.get('kismet.device.base.macaddr', ''),
            'name': raw_data.get('kismet.device.base.name', ''),
            'username': raw_data.get('kismet.device.base.username', ''),
            'phy_type': raw_data.get('kismet.device.base.phyname', ''),
            'manufacturer': raw_data.get('kismet.device.base.manuf', ''),
            'first_seen': raw_data.get('kismet.device.base.first_time', 0),
            'last_seen': raw_data.get('kismet.device.base.last_time', 0),
            'channel': raw_data.get('kismet.device.base.channel', ''),
            'frequency': raw_data.get('kismet.device.base.frequency', 0),
            'total_packets': raw_data.get('kismet.device.base.packets.total', 0),
            'tx_packets': raw_data.get('kismet.device.base.packets.tx', 0),
            'rx_packets': raw_data.get('kismet.device.base.packets.rx', 0),
            'data_size': raw_data.get('kismet.device.base.datasize', 0)
        }
        
        # Extract signal information
        signal_data = raw_data.get('kismet.device.base.signal', {})
        if signal_data:
            device_info.update({
                'signal_dbm': signal_data.get('kismet.common.signal.last_signal', 0),
                'noise_dbm': signal_data.get('kismet.common.signal.last_noise', 0),
                'snr_db': signal_data.get('kismet.common.signal.last_snr', 0)
            })
            
        # Extract location information
        location_data = raw_data.get('kismet.device.base.location', {})
        if location_data:
            device_info.update({
                'latitude': location_data.get('kismet.common.location.avg_lat', 0),
                'longitude': location_data.get('kismet.common.location.avg_lon', 0),
                'altitude': location_data.get('kismet.common.location.avg_alt', 0)
            })
            
        return device_info
        
    def print_stats(self):
        """Print current statistics"""
        if self.stats['start_time']:
            runtime = time.time() - self.stats['start_time']
            rate = self.stats['devices_processed'] / runtime if runtime > 0 else 0
            
            print(f"\n=== Kismet Export Statistics ===")
            print(f"Runtime: {runtime:.1f} seconds")
            print(f"Devices processed: {self.stats['devices_processed']}")
            print(f"Alerts processed: {self.stats['alerts_processed']}")
            print(f"Processing rate: {rate:.2f} devices/second")
            print(f"Last update: {datetime.fromtimestamp(self.stats['last_update']) if self.stats['last_update'] else 'Never'}")
            
    async def stop(self):
        """Stop the export client"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
        if self.exporter:
            await self.exporter.close()
        self.print_stats()


class ConsoleExporter:
    """Export device data to console (for testing/debugging)"""
    
    def __init__(self):
        self.device_count = 0
        
    async def export_device(self, device_info: Dict[str, Any]):
        """Export device to console"""
        self.device_count += 1
        print(f"[{self.device_count}] Device: {device_info['mac_addr']} "
              f"({device_info['name'] or 'Unknown'}) - "
              f"PHY: {device_info['phy_type']} - "
              f"Signal: {device_info['signal_dbm']}dBm - "
              f"Packets: {device_info['total_packets']}")
              
    async def export_event(self, event_data: Dict[str, Any]):
        """Export event to console"""
        print(f"Event: {json.dumps(event_data, indent=2)}")
        
    async def close(self):
        """Close exporter"""
        pass


class PostgreSQLExporter:
    """Export device data to PostgreSQL database"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn = None
        
    async def connect(self):
        """Connect to PostgreSQL"""
        if not POSTGRES_AVAILABLE:
            raise ImportError("asyncpg not available. Install with: pip install asyncpg")
            
        self.conn = await asyncpg.connect(self.connection_string)
        
        # Create table if it doesn't exist
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS kismet_devices (
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
            )
        """)
        
    async def export_device(self, device_info: Dict[str, Any]):
        """Export device to PostgreSQL"""
        if not self.conn:
            await self.connect()
            
        await self.conn.execute("""
            INSERT INTO kismet_devices (
                mac_addr, name, username, phy_type, manufacturer,
                first_seen, last_seen, channel, frequency,
                total_packets, tx_packets, rx_packets, data_size,
                signal_dbm, noise_dbm, snr_db,
                latitude, longitude, altitude, last_updated
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, NOW())
            ON CONFLICT (mac_addr) DO UPDATE SET
                name = EXCLUDED.name,
                username = EXCLUDED.username,
                last_seen = EXCLUDED.last_seen,
                channel = EXCLUDED.channel,
                frequency = EXCLUDED.frequency,
                total_packets = EXCLUDED.total_packets,
                tx_packets = EXCLUDED.tx_packets,
                rx_packets = EXCLUDED.rx_packets,
                data_size = EXCLUDED.data_size,
                signal_dbm = EXCLUDED.signal_dbm,
                noise_dbm = EXCLUDED.noise_dbm,
                snr_db = EXCLUDED.snr_db,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                altitude = EXCLUDED.altitude,
                last_updated = NOW()
        """, device_info['mac_addr'], device_info['name'], device_info['username'],
             device_info['phy_type'], device_info['manufacturer'],
             device_info['first_seen'], device_info['last_seen'],
             device_info['channel'], device_info['frequency'],
             device_info['total_packets'], device_info['tx_packets'], device_info['rx_packets'],
             device_info['data_size'], device_info['signal_dbm'], device_info['noise_dbm'],
             device_info['snr_db'], device_info['latitude'], device_info['longitude'],
             device_info['altitude'])
             
    async def export_event(self, event_data: Dict[str, Any]):
        """Export event to PostgreSQL (could create events table)"""
        pass
        
    async def close(self):
        """Close PostgreSQL connection"""
        if self.conn:
            await self.conn.close()


class InfluxDBExporter:
    """Export device data to InfluxDB (time series database)"""
    
    def __init__(self, url: str, token: str, org: str, bucket: str):
        if not INFLUXDB_AVAILABLE:
            raise ImportError("influxdb-client not available. Install with: pip install influxdb-client")
            
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = bucket
        
    async def export_device(self, device_info: Dict[str, Any]):
        """Export device to InfluxDB"""
        point = Point("device_metrics") \
            .tag("mac_addr", device_info['mac_addr']) \
            .tag("phy_type", device_info['phy_type']) \
            .tag("manufacturer", device_info['manufacturer']) \
            .field("signal_dbm", device_info['signal_dbm']) \
            .field("noise_dbm", device_info['noise_dbm']) \
            .field("snr_db", device_info['snr_db']) \
            .field("total_packets", device_info['total_packets']) \
            .field("tx_packets", device_info['tx_packets']) \
            .field("rx_packets", device_info['rx_packets']) \
            .field("data_size", device_info['data_size']) \
            .field("frequency", device_info['frequency']) \
            .field("latitude", device_info['latitude']) \
            .field("longitude", device_info['longitude']) \
            .time(int(device_info['last_seen'] * 1000000000))  # Convert to nanoseconds
            
        self.write_api.write(bucket=self.bucket, record=point)
        
    async def export_event(self, event_data: Dict[str, Any]):
        """Export event to InfluxDB"""
        point = Point("kismet_events") \
            .field("event_data", json.dumps(event_data)) \
            .time(int(time.time() * 1000000000))
            
        self.write_api.write(bucket=self.bucket, record=point)
        
    async def close(self):
        """Close InfluxDB connection"""
        self.client.close()


class MQTTExporter:
    """Export device data to MQTT broker"""
    
    def __init__(self, broker_host: str, broker_port: int = 1883, 
                 topic_prefix: str = "kismet", username: str = None, password: str = None):
        if not MQTT_AVAILABLE:
            raise ImportError("paho-mqtt not available. Install with: pip install paho-mqtt")
            
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic_prefix = topic_prefix
        self.client = mqtt.Client()
        
        if username and password:
            self.client.username_pw_set(username, password)
            
        self.connected = False
        
    async def connect(self):
        """Connect to MQTT broker"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.connected = True
                print(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            else:
                print(f"Failed to connect to MQTT broker: {rc}")
                
        self.client.on_connect = on_connect
        self.client.connect(self.broker_host, self.broker_port, 60)
        self.client.loop_start()
        
        # Wait for connection
        while not self.connected:
            await asyncio.sleep(0.1)
            
    async def export_device(self, device_info: Dict[str, Any]):
        """Export device to MQTT"""
        if not self.connected:
            await self.connect()
            
        topic = f"{self.topic_prefix}/devices/{device_info['mac_addr'].replace(':', '_')}"
        payload = json.dumps(device_info)
        
        self.client.publish(topic, payload, qos=1)
        
    async def export_event(self, event_data: Dict[str, Any]):
        """Export event to MQTT"""
        if not self.connected:
            await self.connect()
            
        topic = f"{self.topic_prefix}/events"
        payload = json.dumps(event_data)
        
        self.client.publish(topic, payload, qos=1)
        
    async def close(self):
        """Close MQTT connection"""
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()


class TCPExporter:
    """Export device data to TCP server (configurable IP:port)"""
    
    def __init__(self, server_host: str, server_port: int, format_type: str = "json"):
        self.server_host = server_host
        self.server_port = server_port
        self.format_type = format_type
        self.writer = None
        self.reader = None
        self.connected = False
        self.device_count = 0
        self.event_count = 0
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.TCPExporter")
        
    async def connect(self):
        """Connect to TCP server"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.server_host, self.server_port
            )
            self.connected = True
            self.logger.info(f"Connected to TCP server at {self.server_host}:{self.server_port}")
        except Exception as e:
            self.logger.error(f"Failed to connect to TCP server: {e}")
            self.connected = False
            
    async def send_data(self, data: str):
        """Send data to TCP server"""
        if not self.connected:
            await self.connect()
            
        if self.connected and self.writer:
            try:
                # Add newline delimiter for easier parsing on server side
                message = data + "\n"
                self.writer.write(message.encode('utf-8'))
                await self.writer.drain()
            except Exception as e:
                self.logger.error(f"Failed to send data to TCP server: {e}")
                self.connected = False
                
    async def export_device(self, device_info: Dict[str, Any]):
        """Export device to TCP server"""
        self.device_count += 1
        
        if self.format_type == "json":
            # Send as JSON
            data = json.dumps({
                "type": "device",
                "data": device_info,
                "sequence": self.device_count,
                "timestamp": time.time()
            })
        elif self.format_type == "csv":
            # Send as CSV format
            data = f"DEVICE,{device_info['mac_addr']},{device_info['phy_type']},{device_info['signal_dbm']},{device_info['total_packets']},{device_info['timestamp']}"
        else:
            # Send as simple key-value format
            data = f"DEVICE|{device_info['mac_addr']}|{device_info['phy_type']}|{device_info['signal_dbm']}|{device_info['total_packets']}"
            
        await self.send_data(data)
        
    async def export_event(self, event_data: Dict[str, Any]):
        """Export event to TCP server"""
        self.event_count += 1
        
        if self.format_type == "json":
            data = json.dumps({
                "type": "event",
                "data": event_data,
                "sequence": self.event_count,
                "timestamp": time.time()
            })
        else:
            data = f"EVENT|{json.dumps(event_data)}"
            
        await self.send_data(data)
        
    async def close(self):
        """Close TCP connection"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.connected = False
        self.logger.info(f"TCP connection closed. Sent {self.device_count} devices, {self.event_count} events")


class UDPExporter:
    """Export device data to UDP server (configurable IP:port)"""
    
    def __init__(self, server_host: str, server_port: int, format_type: str = "json"):
        self.server_host = server_host
        self.server_port = server_port
        self.format_type = format_type
        self.sock = None
        self.device_count = 0
        self.event_count = 0
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.UDPExporter")
        
    async def connect(self):
        """Setup UDP socket"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.logger.info(f"UDP socket configured for {self.server_host}:{self.server_port}")
        except Exception as e:
            self.logger.error(f"Failed to create UDP socket: {e}")
            
    async def send_data(self, data: str):
        """Send data via UDP"""
        if not self.sock:
            await self.connect()
            
        if self.sock:
            try:
                message = data.encode('utf-8')
                self.sock.sendto(message, (self.server_host, self.server_port))
            except Exception as e:
                self.logger.error(f"Failed to send UDP data: {e}")
                
    async def export_device(self, device_info: Dict[str, Any]):
        """Export device via UDP"""
        self.device_count += 1
        
        if self.format_type == "json":
            # Send as JSON
            data = json.dumps({
                "type": "device",
                "data": device_info,
                "sequence": self.device_count,
                "timestamp": time.time()
            })
        elif self.format_type == "csv":
            # Send as CSV format
            data = f"DEVICE,{device_info['mac_addr']},{device_info['phy_type']},{device_info['signal_dbm']},{device_info['total_packets']},{device_info['timestamp']}"
        else:
            # Send as simple key-value format
            data = f"DEVICE|{device_info['mac_addr']}|{device_info['phy_type']}|{device_info['signal_dbm']}|{device_info['total_packets']}"
            
        await self.send_data(data)
        
    async def export_event(self, event_data: Dict[str, Any]):
        """Export event via UDP"""
        self.event_count += 1
        
        if self.format_type == "json":
            data = json.dumps({
                "type": "event",
                "data": event_data,
                "sequence": self.event_count,
                "timestamp": time.time()
            })
        else:
            data = f"EVENT|{json.dumps(event_data)}"
            
        await self.send_data(data)
        
    async def close(self):
        """Close UDP socket"""
        if self.sock:
            self.sock.close()
        self.logger.info(f"UDP socket closed. Sent {self.device_count} devices, {self.event_count} events")


async def main():
    parser = argparse.ArgumentParser(description="Kismet Real-Time Data Export Client")
    parser.add_argument("--kismet-host", default="localhost", help="Kismet server hostname")
    parser.add_argument("--kismet-port", type=int, default=2501, help="Kismet server port")
    parser.add_argument("--update-rate", type=int, default=5, help="Update rate in seconds")
    parser.add_argument("--export-type", choices=["console", "postgres", "influxdb", "mqtt", "tcp", "udp"], 
                       default="console", help="Export destination type")
    
    # PostgreSQL options
    parser.add_argument("--postgres-conn", help="PostgreSQL connection string")
    
    # InfluxDB options
    parser.add_argument("--influx-url", help="InfluxDB URL")
    parser.add_argument("--influx-token", help="InfluxDB token")
    parser.add_argument("--influx-org", help="InfluxDB organization")
    parser.add_argument("--influx-bucket", help="InfluxDB bucket")
    
    # MQTT options
    parser.add_argument("--mqtt-host", help="MQTT broker hostname")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--mqtt-topic-prefix", default="kismet", help="MQTT topic prefix")
    parser.add_argument("--mqtt-username", help="MQTT username")
    parser.add_argument("--mqtt-password", help="MQTT password")
    
    # TCP/UDP options
    parser.add_argument("--server-host", default="172.18.18.20", help="TCP/UDP server hostname or IP address")
    parser.add_argument("--server-port", type=int, default=8685, help="TCP/UDP server port")
    parser.add_argument("--data-format", choices=["json", "csv", "simple"], default="json", 
                       help="Data format for TCP/UDP export (json, csv, or simple)")
    
    args = parser.parse_args()
    
    # Create export client
    client = KismetExportClient(
        kismet_host=args.kismet_host,
        kismet_port=args.kismet_port,
        update_rate=args.update_rate,
        export_type=args.export_type
    )
    
    # Setup exporter based on type
    if args.export_type == "console":
        client.exporter = ConsoleExporter()
    elif args.export_type == "postgres":
        if not args.postgres_conn:
            print("Error: --postgres-conn required for PostgreSQL export")
            sys.exit(1)
        client.exporter = PostgreSQLExporter(args.postgres_conn)
    elif args.export_type == "influxdb":
        if not all([args.influx_url, args.influx_token, args.influx_org, args.influx_bucket]):
            print("Error: InfluxDB options required for InfluxDB export")
            sys.exit(1)
        client.exporter = InfluxDBExporter(args.influx_url, args.influx_token, 
                                          args.influx_org, args.influx_bucket)
    elif args.export_type == "mqtt":
        if not args.mqtt_host:
            print("Error: --mqtt-host required for MQTT export")
            sys.exit(1)
        client.exporter = MQTTExporter(args.mqtt_host, args.mqtt_port, 
                                      args.mqtt_topic_prefix, args.mqtt_username, args.mqtt_password)
    elif args.export_type == "tcp":
        print(f"Configuring TCP export to {args.server_host}:{args.server_port} (format: {args.data_format})")
        client.exporter = TCPExporter(args.server_host, args.server_port, args.data_format)
    elif args.export_type == "udp":
        print(f"Configuring UDP export to {args.server_host}:{args.server_port} (format: {args.data_format})")
        client.exporter = UDPExporter(args.server_host, args.server_port, args.data_format)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        asyncio.create_task(client.stop())
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start monitoring
    try:
        # Run device monitoring and event bus in parallel
        await asyncio.gather(
            client.connect_and_monitor(),
            client.connect_event_bus()
        )
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
