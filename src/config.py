"""Configuration and credential management for liquidity management system."""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from pydantic import BaseSettings, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ChainConfig(BaseSettings):
    """Configuration for a blockchain network."""
    rpc_url: str
    chain_id: int
    name: str
    explorer_url: Optional[str] = None
    
    class Config:
        env_prefix = ""


class Settings(BaseSettings):
    """Application settings with secure credential management."""
    
    # Encryption key for credentials
    encryption_key: Optional[str] = Field(None, env="ENCRYPTION_KEY")
    
    # Ethereum configuration
    ethereum_rpc_url: str = Field(..., env="ETHEREUM_RPC_URL")
    ethereum_private_key: Optional[str] = Field(None, env="ETHEREUM_PRIVATE_KEY")
    
    # Arbitrum configuration
    arbitrum_rpc_url: str = Field(..., env="ARBITRUM_RPC_URL")
    arbitrum_private_key: Optional[str] = Field(None, env="ARBITRUM_PRIVATE_KEY")
    
    # API Keys
    etherscan_api_key: Optional[str] = Field(None, env="ETHERSCAN_API_KEY")
    arbiscan_api_key: Optional[str] = Field(None, env="ARBISCAN_API_KEY")
    
    # Uniswap V3 contract addresses
    uniswap_v3_nft_manager_address: str = "0xC36442b4a4522E871399CD717aBDD847Ab11FE88"
    uniswap_v3_factory_address: str = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @validator("encryption_key", pre=True, always=True)
    def generate_encryption_key(cls, v):
        """Generate encryption key if not provided."""
        if not v:
            return Fernet.generate_key().decode()
        return v


class CredentialManager:
    """Manages secure storage and retrieval of credentials."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize credential manager with encryption key."""
        self.config_dir = Path.home() / ".liquidity_manager"
        self.config_dir.mkdir(exist_ok=True)
        self.credentials_file = self.config_dir / "credentials.json"
        
        # Use provided key or generate new one
        if encryption_key:
            self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        else:
            key = Fernet.generate_key()
            self.cipher = Fernet(key)
            self._save_key(key)
    
    def _save_key(self, key: bytes):
        """Save encryption key to secure location."""
        key_file = self.config_dir / ".key"
        key_file.write_bytes(key)
        # Set restrictive permissions (owner read/write only)
        os.chmod(key_file, 0o600)
    
    def _load_key(self) -> bytes:
        """Load encryption key from secure location."""
        key_file = self.config_dir / ".key"
        if key_file.exists():
            return key_file.read_bytes()
        raise ValueError("Encryption key not found. Initialize CredentialManager first.")
    
    def save_credential(self, key: str, value: str):
        """Save an encrypted credential."""
        credentials = self._load_credentials()
        encrypted_value = self.cipher.encrypt(value.encode()).decode()
        credentials[key] = encrypted_value
        self._save_credentials(credentials)
    
    def get_credential(self, key: str) -> Optional[str]:
        """Retrieve and decrypt a credential."""
        credentials = self._load_credentials()
        if key in credentials:
            encrypted_value = credentials[key]
            return self.cipher.decrypt(encrypted_value.encode()).decode()
        return None
    
    def _load_credentials(self) -> Dict[str, Any]:
        """Load credentials from file."""
        if self.credentials_file.exists():
            with open(self.credentials_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_credentials(self, credentials: Dict[str, Any]):
        """Save credentials to file with restrictive permissions."""
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        os.chmod(self.credentials_file, 0o600)
    
    def list_credentials(self) -> list:
        """List all stored credential keys (not values)."""
        return list(self._load_credentials().keys())
    
    def delete_credential(self, key: str) -> bool:
        """Delete a stored credential."""
        credentials = self._load_credentials()
        if key in credentials:
            del credentials[key]
            self._save_credentials(credentials)
            return True
        return False


# Chain configurations
CHAIN_CONFIGS = {
    "ethereum": ChainConfig(
        rpc_url=os.getenv("ETHEREUM_RPC_URL", ""),
        chain_id=1,
        name="Ethereum Mainnet",
        explorer_url="https://etherscan.io"
    ),
    "arbitrum": ChainConfig(
        rpc_url=os.getenv("ARBITRUM_RPC_URL", ""),
        chain_id=42161,
        name="Arbitrum One",
        explorer_url="https://arbiscan.io"
    )
}

# Initialize settings
settings = Settings()

