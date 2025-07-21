#!/usr/bin/env python3
"""
Kismet Elasticsearch Export Client with Offline Support
Connects to Kismet WebSocket endpoints and exports device data to Elasticsearch
Supports offline mode with local storage and store-and-forward capability
"""

import asyncio
import websockets
import json
import argparse
import logging
import time
import os
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import signal
import sys
from pathlib import Path

# Elasticsearch client
try:
    from elasticsearch import Elasticsearch, helpers
    from elasticsearch.exceptions import ConnectionError, RequestError
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False

class OfflineStorage:
    """Local SQLite storage for offline data buffering"""
    
    def __init__(self, db_path: str = "kismet_offline_buffer.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for offline storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables for buffering data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                mac_addr TEXT NOT NULL,
                data JSON NOT NULL,
                synced INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT,
                data JSON NOT NULL,
                synced INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_synced ON device_buffer(synced)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_synced ON event_buffer(synced)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_timestamp ON device_buffer(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_timestamp ON event_buffer(timestamp)")
        
        conn.commit()
        conn.close()
        
    def store_device(self, device_data: Dict[str, Any]) -> bool:
        """Store device data locally"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO device_buffer (timestamp, mac_addr, data)
                VALUES (?, ?, ?)
            """, (
                device_data['timestamp'],
                device_data['mac_addr'],
                json.dumps(device_data)
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Failed to store device data locally: {e}")
            return False
            
    def store_event(self, event_data: Dict[str, Any]) -> bool:
        """Store event data locally"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO event_buffer (timestamp, event_type, data)
                VALUES (?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                event_data.get('event_type', 'unknown'),
                json.dumps(event_data)
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Failed to store event data locally: {e}")
            return False
            
    def get_unsynced_devices(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get unsynced device records"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, data FROM device_buffer 
                WHERE synced = 0 
                ORDER BY created_at ASC 
                LIMIT ?
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                record_id, data_json = row
                data = json.loads(data_json)
                data['_buffer_id'] = record_id
                results.append(data)
                
            conn.close()
            return results
        except Exception as e:
            logging.error(f"Failed to get unsynced devices: {e}")
            return []
            
    def get_unsynced_events(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get unsynced event records"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, data FROM event_buffer 
                WHERE synced = 0 
                ORDER BY created_at ASC 
                LIMIT ?
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                record_id, data_json = row
                data = json.loads(data_json)
                data['_buffer_id'] = record_id
                results.append(data)
                
            conn.close()
            return results
        except Exception as e:
            logging.error(f"Failed to get unsynced events: {e}")
            return []
            
    def mark_synced(self, table: str, record_ids: List[int]) -> bool:
        """Mark records as synced"""
        if not record_ids:
            return True
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            placeholders = ','.join(['?' for _ in record_ids])
            cursor.execute(f"""
                UPDATE {table} SET synced = 1 
                WHERE id IN ({placeholders})
            """, record_ids)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Failed to mark records as synced: {e}")
            return False
            
    def get_stats(self) -> Dict[str, int]:
        """Get buffer statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM device_buffer WHERE synced = 0")
            unsynced_devices = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM event_buffer WHERE synced = 0")
            unsynced_events = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM device_buffer")
            total_devices = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM event_buffer")
            total_events = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'unsynced_devices': unsynced_devices,
                'unsynced_events': unsynced_events,
                'total_devices': total_devices,
                'total_events': total_events
            }
        except Exception as e:
            logging.error(f"Failed to get buffer stats: {e}")
            return {}
            
    def cleanup_old_synced(self, days: int = 7) -> int:
        """Clean up old synced records"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                DELETE FROM device_buffer 
                WHERE synced = 1 AND created_at < ?
            """, (cutoff_date.isoformat(),))
            
            device_deleted = cursor.rowcount
            
            cursor.execute("""
                DELETE FROM event_buffer 
                WHERE synced = 1 AND created_at < ?
            """, (cutoff_date.isoformat(),))
            
            event_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return device_deleted + event_deleted
        except Exception as e:
            logging.error(f"Failed to cleanup old records: {e}")
            return 0


class ElasticsearchExporter:
    """Export device data to Elasticsearch with offline support"""
    
    def __init__(self, hosts: List[str], index_prefix: str = "kismet", 
                 username: str = None, password: str = None, 
                 api_key: str = None, offline_mode: bool = False,
                 offline_storage: OfflineStorage = None):
        
        if not ELASTICSEARCH_AVAILABLE:
            raise ImportError("elasticsearch not available. Install with: pip install elasticsearch")
            
        self.hosts = hosts
        self.index_prefix = index_prefix
        self.offline_mode = offline_mode
        self.offline_storage = offline_storage or OfflineStorage()
        self.es_client = None
        self.connected = False
        
        # Setup Elasticsearch client
        if not offline_mode:
            self._setup_elasticsearch_client(username, password, api_key)
            
        # Background sync thread
        self.sync_thread = None
        self.sync_running = False
        
    def _setup_elasticsearch_client(self, username: str = None, password: str = None, api_key: str = None):
        """Setup Elasticsearch client with authentication"""
        try:
            client_config = {
                'hosts': self.hosts,
                'timeout': 30,
                'max_retries': 3,
                'retry_on_timeout': True
            }
            
            if api_key:
                client_config['api_key'] = api_key
            elif username and password:
                client_config['basic_auth'] = (username, password)
                
            self.es_client = Elasticsearch(**client_config)
            
            # Test connection
            if self.es_client.ping():
                self.connected = True
                logging.info(f"Connected to Elasticsearch at {self.hosts}")
                self._setup_index_templates()
            else:
                logging.warning("Failed to connect to Elasticsearch")
                self.connected = False
                
        except Exception as e:
            logging.error(f"Failed to setup Elasticsearch client: {e}")
            self.connected = False
            
    def _setup_index_templates(self):
        """Setup Elasticsearch index templates for optimal storage"""
        device_template = {
            "index_patterns": [f"{self.index_prefix}-devices-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "refresh_interval": "30s"
                },
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "mac_addr": {"type": "keyword"},
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "phy_type": {"type": "keyword"},
                        "manufacturer": {"type": "keyword"},
                        "signal_dbm": {"type": "integer"},
                        "location": {"type": "geo_point"},
                        "first_seen": {"type": "date", "format": "epoch_second"},
                        "last_seen": {"type": "date", "format": "epoch_second"},
                        "total_packets": {"type": "long"},
                        "frequency": {"type": "long"}
                    }
                }
            }
        }
        
        event_template = {
            "index_patterns": [f"{self.index_prefix}-events-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "refresh_interval": "30s"
                },
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "event_type": {"type": "keyword"},
                        "device_mac": {"type": "keyword"},
                        "event_data": {"type": "object", "enabled": False}
                    }
                }
            }
        }
        
        try:
            self.es_client.indices.put_index_template(
                name=f"{self.index_prefix}-devices-template",
                body=device_template
            )
            
            self.es_client.indices.put_index_template(
                name=f"{self.index_prefix}-events-template", 
                body=event_template
            )
            
            logging.info("Elasticsearch index templates created")
        except Exception as e:
            logging.error(f"Failed to create index templates: {e}")
            
    def start_background_sync(self, interval: int = 60):
        """Start background sync thread for offline data"""
        if self.sync_thread and self.sync_running:
            return
            
        self.sync_running = True
        self.sync_thread = threading.Thread(target=self._background_sync_worker, args=(interval,))
        self.sync_thread.daemon = True
        self.sync_thread.start()
        logging.info(f"Started background sync thread (interval: {interval}s)")
        
    def _background_sync_worker(self, interval: int):
        """Background worker to sync offline data"""
        while self.sync_running:
            try:
                if not self.offline_mode and not self.connected:
                    # Try to reconnect
                    self._setup_elasticsearch_client()
                    
                if self.connected:
                    synced = self.sync_offline_data()
                    if synced > 0:
                        logging.info(f"Background sync: {synced} records synced")
                        
                time.sleep(interval)
            except Exception as e:
                logging.error(f"Background sync error: {e}")
                time.sleep(interval)
                
    def sync_offline_data(self, batch_size: int = 1000) -> int:
        """Sync offline data to Elasticsearch"""
        if not self.connected:
            return 0
            
        total_synced = 0
        
        try:
            # Sync devices
            devices = self.offline_storage.get_unsynced_devices(batch_size)
            if devices:
                device_docs = []
                device_ids = []
                
                for device in devices:
                    doc = self._prepare_device_doc(device)
                    device_docs.append(doc)
                    device_ids.append(device['_buffer_id'])
                    
                if self._bulk_index(device_docs):
                    self.offline_storage.mark_synced('device_buffer', device_ids)
                    total_synced += len(device_docs)
                    
            # Sync events
            events = self.offline_storage.get_unsynced_events(batch_size)
            if events:
                event_docs = []
                event_ids = []
                
                for event in events:
                    doc = self._prepare_event_doc(event)
                    event_docs.append(doc)
                    event_ids.append(event['_buffer_id'])
                    
                if self._bulk_index(event_docs):
                    self.offline_storage.mark_synced('event_buffer', event_ids)
                    total_synced += len(event_docs)
                    
        except Exception as e:
            logging.error(f"Failed to sync offline data: {e}")
            
        return total_synced
        
    def _prepare_device_doc(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare device document for Elasticsearch"""
        doc = {
            '_index': f"{self.index_prefix}-devices-{datetime.now().strftime('%Y.%m')}",
            '_id': f"{device_data['mac_addr']}-{int(time.time())}",
            '_source': device_data.copy()
        }
        
        # Remove buffer-specific fields
        doc['_source'].pop('_buffer_id', None)
        
        # Add geo_point for location if available
        if device_data.get('latitude') and device_data.get('longitude'):
            doc['_source']['location'] = {
                'lat': device_data['latitude'],
                'lon': device_data['longitude']
            }
            
        return doc
        
    def _prepare_event_doc(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare event document for Elasticsearch"""
        doc = {
            '_index': f"{self.index_prefix}-events-{datetime.now().strftime('%Y.%m')}",
            '_source': event_data.copy()
        }
        
        # Remove buffer-specific fields
        doc['_source'].pop('_buffer_id', None)
        
        return doc
        
    def _bulk_index(self, docs: List[Dict[str, Any]]) -> bool:
        """Bulk index documents to Elasticsearch"""
        try:
            response = helpers.bulk(self.es_client, docs, refresh=False)
            return True
        except Exception as e:
            logging.error(f"Bulk index failed: {e}")
            return False
            
    async def export_device(self, device_info: Dict[str, Any]):
        """Export device to Elasticsearch (online) or local storage (offline)"""
        if self.offline_mode or not self.connected:
            # Store locally
            self.offline_storage.store_device(device_info)
        else:
            # Try to send to Elasticsearch directly
            try:
                doc = self._prepare_device_doc(device_info)
                self.es_client.index(
                    index=doc['_index'],
                    id=doc.get('_id'),
                    body=doc['_source']
                )
            except Exception as e:
                logging.error(f"Failed to export device to Elasticsearch: {e}")
                # Fallback to local storage
                self.offline_storage.store_device(device_info)
                
    async def export_event(self, event_data: Dict[str, Any]):
        """Export event to Elasticsearch (online) or local storage (offline)"""
        if self.offline_mode or not self.connected:
            # Store locally
            self.offline_storage.store_event(event_data)
        else:
            # Try to send to Elasticsearch directly
            try:
                doc = self._prepare_event_doc(event_data)
                self.es_client.index(
                    index=doc['_index'],
                    body=doc['_source']
                )
            except Exception as e:
                logging.error(f"Failed to export event to Elasticsearch: {e}")
                # Fallback to local storage
                self.offline_storage.store_event(event_data)
                
    def get_status(self) -> Dict[str, Any]:
        """Get exporter status"""
        status = {
            'connected': self.connected,
            'offline_mode': self.offline_mode,
            'hosts': self.hosts
        }
        
        # Add buffer stats
        buffer_stats = self.offline_storage.get_stats()
        status.update(buffer_stats)
        
        return status
        
    async def close(self):
        """Close exporter and cleanup"""
        self.sync_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
            
        if self.es_client:
            self.es_client.close()


class KismetElasticsearchClient:
    """Main client for Kismet to Elasticsearch export"""
    
    def __init__(self, kismet_host: str = "localhost", kismet_port: int = 2501,
                 update_rate: int = 5, elasticsearch_hosts: List[str] = None,
                 offline_mode: bool = False):
        self.kismet_host = kismet_host
        self.kismet_port = kismet_port
        self.update_rate = update_rate
        self.elasticsearch_hosts = elasticsearch_hosts or ["http://localhost:9200"]
        self.offline_mode = offline_mode
        self.running = False
        self.websocket = None
        self.exporter = None
        
        # Statistics
        self.stats = {
            'devices_processed': 0,
            'events_processed': 0,
            'start_time': None,
            'last_update': None,
            'sync_count': 0
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self, es_username: str = None, es_password: str = None, 
                        es_api_key: str = None, index_prefix: str = "kismet"):
        """Initialize the Elasticsearch exporter"""
        offline_storage = OfflineStorage()
        
        self.exporter = ElasticsearchExporter(
            hosts=self.elasticsearch_hosts,
            index_prefix=index_prefix,
            username=es_username,
            password=es_password,
            api_key=es_api_key,
            offline_mode=self.offline_mode,
            offline_storage=offline_storage
        )
        
        # Start background sync if not in offline mode
        if not self.offline_mode:
            self.exporter.start_background_sync(interval=60)
            
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
                    "monitor": "*",
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
            
    async def process_device_update(self, device_data: Dict[str, Any]):
        """Process a device update message"""
        self.stats['devices_processed'] += 1
        self.stats['last_update'] = time.time()
        
        # Extract and normalize device information
        device_info = self.extract_device_info(device_data)
        
        # Export to Elasticsearch
        if self.exporter:
            await self.exporter.export_device(device_info)
            
    def extract_device_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize device information"""
        device_info = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
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
            
            print(f"\n=== Kismet Elasticsearch Export Statistics ===")
            print(f"Runtime: {runtime:.1f} seconds")
            print(f"Devices processed: {self.stats['devices_processed']}")
            print(f"Events processed: {self.stats['events_processed']}")
            print(f"Processing rate: {rate:.2f} devices/second")
            print(f"Last update: {datetime.fromtimestamp(self.stats['last_update']) if self.stats['last_update'] else 'Never'}")
            
            if self.exporter:
                status = self.exporter.get_status()
                print(f"Elasticsearch connected: {status['connected']}")
                print(f"Offline mode: {status['offline_mode']}")
                print(f"Unsynced devices: {status.get('unsynced_devices', 0)}")
                print(f"Unsynced events: {status.get('unsynced_events', 0)}")
                
    async def sync_offline_data(self):
        """Manually trigger sync of offline data"""
        if self.exporter:
            synced = self.exporter.sync_offline_data()
            self.stats['sync_count'] += synced
            self.logger.info(f"Manual sync: {synced} records synced")
            return synced
        return 0
        
    async def stop(self):
        """Stop the export client"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
        if self.exporter:
            await self.exporter.close()
        self.print_stats()


async def main():
    parser = argparse.ArgumentParser(description="Kismet Elasticsearch Export Client")
    parser.add_argument("--kismet-host", default="localhost", help="Kismet server hostname")
    parser.add_argument("--kismet-port", type=int, default=2501, help="Kismet server port")
    parser.add_argument("--update-rate", type=int, default=5, help="Update rate in seconds")
    
    # Elasticsearch options
    parser.add_argument("--es-hosts", nargs='+', default=["http://localhost:9200"], 
                       help="Elasticsearch hosts")
    parser.add_argument("--es-username", help="Elasticsearch username")
    parser.add_argument("--es-password", help="Elasticsearch password")
    parser.add_argument("--es-api-key", help="Elasticsearch API key")
    parser.add_argument("--index-prefix", default="kismet", help="Elasticsearch index prefix")
    
    # Offline mode options
    parser.add_argument("--offline", action="store_true", help="Run in offline mode (local storage only)")
    parser.add_argument("--sync-only", action="store_true", help="Only sync offline data, don't monitor")
    parser.add_argument("--buffer-db", default="kismet_offline_buffer.db", help="Offline buffer database path")
    
    args = parser.parse_args()
    
    # Create export client
    client = KismetElasticsearchClient(
        kismet_host=args.kismet_host,
        kismet_port=args.kismet_port,
        update_rate=args.update_rate,
        elasticsearch_hosts=args.es_hosts,
        offline_mode=args.offline
    )
    
    # Initialize exporter
    await client.initialize(
        es_username=args.es_username,
        es_password=args.es_password,
        es_api_key=args.es_api_key,
        index_prefix=args.index_prefix
    )
    
    # Handle sync-only mode
    if args.sync_only:
        print("Running in sync-only mode...")
        synced = await client.sync_offline_data()
        print(f"Synced {synced} records")
        return
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        asyncio.create_task(client.stop())
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start monitoring
    try:
        await client.connect_and_monitor()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
