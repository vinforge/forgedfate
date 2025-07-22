#!/usr/bin/env python3
"""
ForgedFate Encryption Setup Script
Sets up secure configuration storage and encryption for sensitive data
"""

import os
import sys
import json
import getpass
import hashlib
import secrets
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class SecureStateManager:
    def __init__(self, config_dir=None):
        self.config_dir = Path(config_dir or os.path.expanduser("~/.forgedfate"))
        self.config_dir.mkdir(exist_ok=True, mode=0o700)
        
        self.key_file = self.config_dir / "master.key"
        self.config_file = self.config_dir / "secure_config.enc"
        self.salt_file = self.config_dir / "salt.bin"
        
        self._master_key = None
        self._fernet = None
    
    def setup_master_password(self, password=None):
        """Set up master password and encryption key"""
        if password is None:
            password = getpass.getpass("Enter master password for ForgedFate: ")
            confirm = getpass.getpass("Confirm master password: ")
            
            if password != confirm:
                raise ValueError("Passwords do not match")
        
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Generate salt
        salt = secrets.token_bytes(32)
        with open(self.salt_file, 'wb') as f:
            f.write(salt)
        os.chmod(self.salt_file, 0o600)
        
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Store encrypted key
        self._master_key = key
        self._fernet = Fernet(key)
        
        # Create initial secure config
        initial_config = {
            "version": "1.0",
            "created": str(Path.ctime(Path.now())),
            "forgedfate": {
                "encryption_enabled": True,
                "secure_storage": True
            }
        }
        
        self.save_secure_config(initial_config)
        print("✅ Master password and encryption setup complete")
        return True
    
    def load_master_key(self, password):
        """Load master key using password"""
        if not self.salt_file.exists():
            raise FileNotFoundError("Salt file not found. Run setup first.")
        
        with open(self.salt_file, 'rb') as f:
            salt = f.read()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        self._master_key = key
        self._fernet = Fernet(key)
        
        # Test decryption
        try:
            self.load_secure_config()
            return True
        except Exception:
            raise ValueError("Invalid password")
    
    def save_secure_config(self, config):
        """Save encrypted configuration"""
        if self._fernet is None:
            raise RuntimeError("Encryption not initialized")
        
        config_json = json.dumps(config, indent=2)
        encrypted_data = self._fernet.encrypt(config_json.encode())
        
        with open(self.config_file, 'wb') as f:
            f.write(encrypted_data)
        os.chmod(self.config_file, 0o600)
    
    def load_secure_config(self):
        """Load encrypted configuration"""
        if self._fernet is None:
            raise RuntimeError("Encryption not initialized")
        
        if not self.config_file.exists():
            return {}
        
        with open(self.config_file, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = self._fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())
    
    def is_setup(self):
        """Check if encryption is already set up"""
        return self.salt_file.exists() and self.config_file.exists()
    
    def encrypt_string(self, plaintext):
        """Encrypt a string"""
        if self._fernet is None:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt_string(self, ciphertext):
        """Decrypt a string"""
        if self._fernet is None:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.decrypt(ciphertext.encode()).decode()

def setup_secure_enclave():
    """Set up secure enclave for ForgedFate"""
    print("🔐 ForgedFate Encryption Setup")
    print("=" * 40)
    
    try:
        # Check for required dependencies
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            print("❌ Missing required dependency: cryptography")
            print("Install with: pip install cryptography")
            return False
        
        manager = SecureStateManager()
        
        if manager.is_setup():
            print("⚠️  Encryption is already set up.")
            choice = input("Do you want to reset it? (y/N): ").lower()
            if choice != 'y':
                print("Setup cancelled.")
                return True
        
        print("\n📝 Setting up master password...")
        print("This password will be used to encrypt sensitive ForgedFate data.")
        print("Make sure to remember it - it cannot be recovered!")
        
        manager.setup_master_password()
        
        print("\n✅ Encryption setup completed successfully!")
        print(f"📁 Configuration stored in: {manager.config_dir}")
        print("\n🔒 Your ForgedFate data is now encrypted and secure.")
        
        return True
        
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Encryption setup failed: {e}")
        return False

def main():
    print("Setting up secure enclave ...")
    
    if not setup_secure_enclave():
        sys.exit(1)
    
    print("\n🎉 ForgedFate encryption setup complete!")
    print("\nNext steps:")
    print("1. Start ForgedFate: sudo kismet")
    print("2. Access web interface: http://localhost:2501")
    print("3. Your sensitive data will be automatically encrypted")

if __name__ == "__main__":
    main()
