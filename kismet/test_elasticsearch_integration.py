#!/usr/bin/env python3
"""
Test script for Kismet Elasticsearch integration
Tests offline storage, data processing, and sync functionality
"""

import asyncio
import json
import sqlite3
import tempfile
import os
from datetime import datetime, timezone
from kismet_elasticsearch_export import OfflineStorage, ElasticsearchExporter, KismetElasticsearchClient

def test_offline_storage():
    """Test offline storage functionality"""
    print("Testing offline storage...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        storage = OfflineStorage(db_path)
        
        # Test device storage
        device_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mac_addr': 'aa:bb:cc:dd:ee:ff',
            'name': 'Test Device',
            'phy_type': 'IEEE802.11',
            'manufacturer': 'Apple',
            'signal_dbm': -45,
            'total_packets': 100
        }
        
        assert storage.store_device(device_data), "Failed to store device"
        print("✅ Device storage: OK")
        
        # Test event storage
        event_data = {
            'event_type': 'NEWDEVICE',
            'device_mac': 'aa:bb:cc:dd:ee:ff',
            'event_data': {'test': 'data'}
        }
        
        assert storage.store_event(event_data), "Failed to store event"
        print("✅ Event storage: OK")
        
        # Test retrieval
        devices = storage.get_unsynced_devices()
        assert len(devices) == 1, f"Expected 1 device, got {len(devices)}"
        assert devices[0]['mac_addr'] == 'aa:bb:cc:dd:ee:ff', "MAC address mismatch"
        print("✅ Device retrieval: OK")
        
        events = storage.get_unsynced_events()
        assert len(events) == 1, f"Expected 1 event, got {len(events)}"
        print("✅ Event retrieval: OK")
        
        # Test stats
        stats = storage.get_stats()
        assert stats['unsynced_devices'] == 1, "Incorrect unsynced device count"
        assert stats['unsynced_events'] == 1, "Incorrect unsynced event count"
        print("✅ Statistics: OK")
        
        # Test marking as synced
        device_ids = [devices[0]['_buffer_id']]
        assert storage.mark_synced('device_buffer', device_ids), "Failed to mark as synced"
        
        stats = storage.get_stats()
        assert stats['unsynced_devices'] == 0, "Device not marked as synced"
        print("✅ Sync marking: OK")
        
        print("✅ Offline storage tests passed!")
        
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_data_extraction():
    """Test device data extraction from Kismet format"""
    print("\nTesting data extraction...")
    
    # Mock Kismet device data
    kismet_data = {
        'kismet.device.base.macaddr': 'aa:bb:cc:dd:ee:ff',
        'kismet.device.base.name': 'iPhone',
        'kismet.device.base.phyname': 'IEEE802.11',
        'kismet.device.base.manuf': 'Apple',
        'kismet.device.base.packets.total': 150,
        'kismet.device.base.signal': {
            'kismet.common.signal.last_signal': -42,
            'kismet.common.signal.last_noise': -95,
            'kismet.common.signal.last_snr': 53
        },
        'kismet.device.base.location': {
            'kismet.common.location.avg_lat': 40.7128,
            'kismet.common.location.avg_lon': -74.0060,
            'kismet.common.location.avg_alt': 10.5
        }
    }
    
    client = KismetElasticsearchClient(offline_mode=True)
    device_info = client.extract_device_info(kismet_data)
    
    # Verify extraction
    assert device_info['mac_addr'] == 'aa:bb:cc:dd:ee:ff', "MAC address extraction failed"
    assert device_info['name'] == 'iPhone', "Name extraction failed"
    assert device_info['phy_type'] == 'IEEE802.11', "PHY type extraction failed"
    assert device_info['manufacturer'] == 'Apple', "Manufacturer extraction failed"
    assert device_info['total_packets'] == 150, "Packet count extraction failed"
    assert device_info['signal_dbm'] == -42, "Signal strength extraction failed"
    assert device_info['latitude'] == 40.7128, "Latitude extraction failed"
    assert device_info['longitude'] == -74.0060, "Longitude extraction failed"
    
    print("✅ Data extraction tests passed!")

async def test_offline_mode():
    """Test offline mode functionality"""
    print("\nTesting offline mode...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create client in offline mode
        client = KismetElasticsearchClient(offline_mode=True)
        
        # Initialize with custom database path
        storage = OfflineStorage(db_path)
        exporter = ElasticsearchExporter(
            hosts=["http://localhost:9200"],
            offline_mode=True,
            offline_storage=storage
        )
        client.exporter = exporter
        
        # Test device processing
        device_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mac_addr': 'bb:cc:dd:ee:ff:aa',
            'name': 'Test Device 2',
            'phy_type': 'Bluetooth',
            'signal_dbm': -55
        }
        
        await client.exporter.export_device(device_data)
        
        # Verify storage
        stats = storage.get_stats()
        assert stats['unsynced_devices'] >= 1, "Device not stored in offline mode"
        
        print("✅ Offline mode tests passed!")
        
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_elasticsearch_document_preparation():
    """Test Elasticsearch document preparation"""
    print("\nTesting Elasticsearch document preparation...")
    
    try:
        # Create exporter (offline mode to avoid connection)
        exporter = ElasticsearchExporter(
            hosts=["http://localhost:9200"],
            offline_mode=True
        )
        
        device_data = {
            'timestamp': '2025-01-21T16:30:45.123Z',
            'mac_addr': 'cc:dd:ee:ff:aa:bb',
            'name': 'Test Device 3',
            'phy_type': 'IEEE802.11',
            'manufacturer': 'Samsung',
            'signal_dbm': -38,
            'latitude': 37.7749,
            'longitude': -122.4194,
            '_buffer_id': 123
        }
        
        doc = exporter._prepare_device_doc(device_data)
        
        # Verify document structure
        assert '_index' in doc, "Missing _index field"
        assert '_id' in doc, "Missing _id field"
        assert '_source' in doc, "Missing _source field"
        assert doc['_index'].startswith('kismet-devices-'), "Incorrect index pattern"
        assert '_buffer_id' not in doc['_source'], "Buffer ID not removed"
        assert 'location' in doc['_source'], "Location geo_point not added"
        assert doc['_source']['location']['lat'] == 37.7749, "Incorrect latitude in geo_point"
        assert doc['_source']['location']['lon'] == -122.4194, "Incorrect longitude in geo_point"
        
        print("✅ Document preparation tests passed!")
        
    except ImportError:
        print("⚠️  Elasticsearch not available, skipping document preparation tests")

def test_buffer_management():
    """Test buffer management and cleanup"""
    print("\nTesting buffer management...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        storage = OfflineStorage(db_path)
        
        # Add multiple devices
        for i in range(5):
            device_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'mac_addr': f'aa:bb:cc:dd:ee:{i:02x}',
                'name': f'Test Device {i}',
                'phy_type': 'IEEE802.11',
                'signal_dbm': -40 - i
            }
            storage.store_device(device_data)
        
        # Verify count
        stats = storage.get_stats()
        assert stats['unsynced_devices'] == 5, f"Expected 5 devices, got {stats['unsynced_devices']}"
        
        # Test batch retrieval
        devices = storage.get_unsynced_devices(limit=3)
        assert len(devices) == 3, f"Expected 3 devices, got {len(devices)}"
        
        # Mark some as synced
        device_ids = [d['_buffer_id'] for d in devices]
        storage.mark_synced('device_buffer', device_ids)
        
        stats = storage.get_stats()
        assert stats['unsynced_devices'] == 2, f"Expected 2 unsynced devices, got {stats['unsynced_devices']}"
        
        print("✅ Buffer management tests passed!")
        
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

async def run_all_tests():
    """Run all tests"""
    print("🧪 Starting Kismet Elasticsearch Integration Tests\n")
    
    try:
        test_offline_storage()
        test_data_extraction()
        await test_offline_mode()
        test_elasticsearch_document_preparation()
        test_buffer_management()
        
        print("\n🎉 All tests passed successfully!")
        print("\nNext steps:")
        print("1. Start Kismet: sudo kismet")
        print("2. Test offline mode: python3 kismet_elasticsearch_export.py --offline")
        print("3. Monitor buffer: sqlite3 kismet_offline_buffer.db 'SELECT COUNT(*) FROM device_buffer'")
        print("4. Connect to Elasticsearch when available")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_all_tests())
