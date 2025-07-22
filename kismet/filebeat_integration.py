#!/usr/bin/env python3
"""
ForgedFate Filebeat Integration Tool
Automatically configures Filebeat for Kismet log ingestion to Elasticsearch
"""

import os
import sys
import json
import yaml
import glob
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

class FilebeatKismetIntegrator:
    def __init__(self):
        self.kismet_log_dir = "/opt/kismet/logs"
        self.filebeat_config = "/etc/filebeat/filebeat.yml"
        self.backup_config = f"/etc/filebeat/filebeat.yml.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def find_kismet_logs(self):
        """Discover all Kismet log directories and files"""
        log_patterns = {
            'devices': 'Kismet-*/devices.json',
            'bluetooth': 'Kismet-*/bluetooth.devices.json',
            'wifi': 'Kismet-*/wifi.devices.json',
            'packets': 'Kismet-*/packets.json',
            'alerts': 'Kismet-*/alerts.json'
        }
        
        found_logs = {}
        for log_type, pattern in log_patterns.items():
            full_pattern = os.path.join(self.kismet_log_dir, pattern)
            matches = glob.glob(full_pattern)
            if matches:
                found_logs[log_type] = {
                    'pattern': full_pattern,
                    'files': matches,
                    'latest': max(matches, key=os.path.getctime) if matches else None
                }
        
        return found_logs
    
    def generate_filebeat_config(self, elasticsearch_config, device_name="forgedfate-device"):
        """Generate comprehensive Filebeat configuration for all Kismet log types"""
        
        logs = self.find_kismet_logs()
        
        if not logs:
            print("❌ No Kismet logs found. Make sure Kismet has been run and generated logs.")
            return None
        
        # Base configuration
        config = {
            'filebeat.inputs': [],
            'output.elasticsearch': {
                'hosts': [elasticsearch_config['url']],
                'username': elasticsearch_config.get('username', ''),
                'password': elasticsearch_config.get('password', ''),
                'ssl.verification_mode': elasticsearch_config.get('ssl_verify', 'none')
            },
            'setup.template.settings': {
                'index.number_of_shards': 1,
                'index.number_of_replicas': 0
            },
            'logging.level': 'info',
            'logging.to_files': True,
            'logging.files': {
                'path': '/var/log/filebeat',
                'name': 'filebeat',
                'keepfiles': 7,
                'permissions': '0644'
            }
        }
        
        # Add input for each log type found
        for log_type, log_info in logs.items():
            input_config = {
                'type': 'filestream',
                'id': f'kismet-{log_type}',
                'enabled': True,
                'paths': [log_info['pattern']],
                'parsers': [{'ndjson': {'target': ''}}],
                'fields': {
                    'log_type': f'kismet_{log_type}',
                    'source_device': device_name,
                    'kismet_version': 'forgedfate',
                    'integration_tool': 'filebeat_kismet_integrator'
                },
                'fields_under_root': True,
                'close_inactive': '5m',
                'scan_frequency': '10s'
            }
            
            # Set index pattern based on log type
            if 'index_prefix' in elasticsearch_config:
                input_config['index'] = f"{elasticsearch_config['index_prefix']}-{log_type}"
            else:
                input_config['index'] = f"kismet-{log_type}"
            
            config['filebeat.inputs'].append(input_config)
        
        return config
    
    def backup_existing_config(self):
        """Backup existing Filebeat configuration"""
        if os.path.exists(self.filebeat_config):
            try:
                subprocess.run(['sudo', 'cp', self.filebeat_config, self.backup_config], 
                             check=True, capture_output=True)
                print(f"✅ Backed up existing config to {self.backup_config}")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to backup config: {e}")
                return False
        return True
    
    def write_filebeat_config(self, config):
        """Write the new Filebeat configuration"""
        try:
            # Write to temporary file first
            temp_config = '/tmp/filebeat_kismet.yml'
            with open(temp_config, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            # Move to final location with sudo
            subprocess.run(['sudo', 'mv', temp_config, self.filebeat_config], 
                         check=True, capture_output=True)
            
            # Set proper permissions
            subprocess.run(['sudo', 'chown', 'root:root', self.filebeat_config], 
                         check=True, capture_output=True)
            subprocess.run(['sudo', 'chmod', '600', self.filebeat_config], 
                         check=True, capture_output=True)
            
            print(f"✅ Filebeat configuration written to {self.filebeat_config}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to write Filebeat config: {e}")
            return False
    
    def test_filebeat_config(self):
        """Test the Filebeat configuration"""
        try:
            result = subprocess.run(['sudo', 'filebeat', 'test', 'config'], 
                                  capture_output=True, text=True, check=True)
            print("✅ Filebeat configuration test passed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Filebeat configuration test failed: {e.stderr}")
            return False
    
    def restart_filebeat(self):
        """Restart Filebeat service"""
        try:
            subprocess.run(['sudo', 'systemctl', 'restart', 'filebeat'], 
                         check=True, capture_output=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'filebeat'], 
                         check=True, capture_output=True)
            print("✅ Filebeat service restarted and enabled")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to restart Filebeat: {e}")
            return False
    
    def check_filebeat_status(self):
        """Check Filebeat service status"""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'status', 'filebeat'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Filebeat is running")
                return True
            else:
                print("❌ Filebeat is not running properly")
                print(result.stdout)
                return False
        except Exception as e:
            print(f"❌ Failed to check Filebeat status: {e}")
            return False
    
    def setup_filebeat_integration(self, elasticsearch_config, device_name="forgedfate-device"):
        """Complete Filebeat integration setup"""
        print("🚀 Starting ForgedFate Filebeat Integration Setup...")
        
        # Step 1: Find Kismet logs
        print("\n📁 Discovering Kismet logs...")
        logs = self.find_kismet_logs()
        if not logs:
            print("❌ No Kismet logs found. Please run Kismet first to generate logs.")
            return False
        
        print(f"✅ Found {len(logs)} log types:")
        for log_type, info in logs.items():
            print(f"   - {log_type}: {len(info['files'])} files")
        
        # Step 2: Backup existing config
        print("\n💾 Backing up existing Filebeat configuration...")
        if not self.backup_existing_config():
            return False
        
        # Step 3: Generate new config
        print("\n⚙️ Generating Filebeat configuration...")
        config = self.generate_filebeat_config(elasticsearch_config, device_name)
        if not config:
            return False
        
        # Step 4: Write config
        print("\n📝 Writing Filebeat configuration...")
        if not self.write_filebeat_config(config):
            return False
        
        # Step 5: Test config
        print("\n🧪 Testing Filebeat configuration...")
        if not self.test_filebeat_config():
            return False
        
        # Step 6: Restart service
        print("\n🔄 Restarting Filebeat service...")
        if not self.restart_filebeat():
            return False
        
        # Step 7: Check status
        print("\n✅ Checking Filebeat status...")
        if not self.check_filebeat_status():
            return False
        
        print("\n🎉 ForgedFate Filebeat integration setup complete!")
        print("\n📊 Your Kismet data should now be flowing to Elasticsearch:")
        for log_type in logs.keys():
            index_name = f"kismet-{log_type}"
            print(f"   - {log_type} data → {index_name} index")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='ForgedFate Filebeat Integration Tool')
    parser.add_argument('--elasticsearch-url', required=True, 
                       help='Elasticsearch URL (e.g., https://172.18.18.20:9200)')
    parser.add_argument('--username', help='Elasticsearch username')
    parser.add_argument('--password', help='Elasticsearch password')
    parser.add_argument('--device-name', default='forgedfate-device',
                       help='Device name for log identification')
    parser.add_argument('--index-prefix', default='kismet',
                       help='Index prefix for Elasticsearch indices')
    parser.add_argument('--ssl-verify', default='none', choices=['none', 'certificate'],
                       help='SSL verification mode')
    parser.add_argument('--dry-run', action='store_true',
                       help='Generate config but do not apply it')
    
    args = parser.parse_args()
    
    elasticsearch_config = {
        'url': args.elasticsearch_url,
        'username': args.username,
        'password': args.password,
        'index_prefix': args.index_prefix,
        'ssl_verify': args.ssl_verify
    }
    
    integrator = FilebeatKismetIntegrator()
    
    if args.dry_run:
        print("🔍 Dry run mode - generating configuration only...")
        config = integrator.generate_filebeat_config(elasticsearch_config, args.device_name)
        if config:
            print("\n📋 Generated Filebeat configuration:")
            print(yaml.dump(config, default_flow_style=False, indent=2))
    else:
        success = integrator.setup_filebeat_integration(elasticsearch_config, args.device_name)
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
