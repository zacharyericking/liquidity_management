"""Web3 connection manager for Ethereum and Arbitrum networks."""
from typing import Dict, Optional, Any
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount

from .config import CHAIN_CONFIGS, CredentialManager, settings


class Web3Manager:
    """Manages Web3 connections to multiple blockchain networks."""
    
    def __init__(self, credential_manager: Optional[CredentialManager] = None):
        """Initialize Web3Manager with optional credential manager."""
        self.credential_manager = credential_manager or CredentialManager(settings.encryption_key)
        self.connections: Dict[str, Web3] = {}
        self.accounts: Dict[str, LocalAccount] = {}
        
    def connect(self, chain: str) -> Web3:
        """Connect to a blockchain network."""
        if chain not in CHAIN_CONFIGS:
            raise ValueError(f"Unknown chain: {chain}. Available chains: {list(CHAIN_CONFIGS.keys())}")
        
        if chain in self.connections and self.connections[chain].is_connected():
            return self.connections[chain]
        
        config = CHAIN_CONFIGS[chain]
        
        # Create Web3 instance
        if config.rpc_url.startswith("http"):
            w3 = Web3(Web3.HTTPProvider(config.rpc_url))
        elif config.rpc_url.startswith("ws"):
            w3 = Web3(Web3.WebsocketProvider(config.rpc_url))
        else:
            raise ValueError(f"Invalid RPC URL format: {config.rpc_url}")
        
        # Add POA middleware for networks like Arbitrum
        if chain == "arbitrum":
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        if not w3.is_connected():
            raise ConnectionError(f"Failed to connect to {config.name}")
        
        self.connections[chain] = w3
        return w3
    
    def get_account(self, chain: str) -> Optional[LocalAccount]:
        """Get account for a specific chain."""
        if chain in self.accounts:
            return self.accounts[chain]
        
        # Try to load private key from credentials
        private_key = self.credential_manager.get_credential(f"{chain}_private_key")
        
        if not private_key:
            # Try environment variable
            env_key = f"{chain.upper()}_PRIVATE_KEY"
            private_key = getattr(settings, f"{chain}_private_key", None)
        
        if private_key:
            # Ensure private key has 0x prefix
            if not private_key.startswith('0x'):
                private_key = '0x' + private_key
            
            account = Account.from_key(private_key)
            self.accounts[chain] = account
            return account
        
        return None
    
    def set_account(self, chain: str, private_key: str, save: bool = True):
        """Set account for a specific chain."""
        # Ensure private key has 0x prefix
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        # Validate private key
        try:
            account = Account.from_key(private_key)
            self.accounts[chain] = account
            
            if save:
                self.credential_manager.save_credential(f"{chain}_private_key", private_key)
            
            return account
        except Exception as e:
            raise ValueError(f"Invalid private key: {e}")
    
    def get_balance(self, chain: str, address: Optional[str] = None) -> float:
        """Get ETH/native token balance for an address."""
        w3 = self.connect(chain)
        
        if not address:
            account = self.get_account(chain)
            if not account:
                raise ValueError(f"No account configured for {chain}")
            address = account.address
        
        balance_wei = w3.eth.get_balance(address)
        return float(w3.from_wei(balance_wei, 'ether'))
    
    def get_contract(self, chain: str, address: str, abi: list) -> Any:
        """Get a contract instance."""
        w3 = self.connect(chain)
        # Convert address to checksum format
        checksum_address = Web3.to_checksum_address(address)
        return w3.eth.contract(address=checksum_address, abi=abi)
    
    def disconnect(self, chain: Optional[str] = None):
        """Disconnect from blockchain network(s)."""
        if chain:
            if chain in self.connections:
                # Web3py doesn't have explicit disconnect for HTTP providers
                del self.connections[chain]
        else:
            # Disconnect all
            self.connections.clear()
    
    def get_gas_price(self, chain: str) -> Dict[str, float]:
        """Get current gas prices in Gwei."""
        w3 = self.connect(chain)
        gas_price_wei = w3.eth.gas_price
        
        # Try to get priority fee (EIP-1559)
        try:
            latest_block = w3.eth.get_block('latest')
            base_fee = latest_block.get('baseFeePerGas', gas_price_wei)
            
            # Estimate priority fees
            max_priority_fee_low = w3.to_wei(1, 'gwei')
            max_priority_fee_medium = w3.to_wei(2, 'gwei')
            max_priority_fee_high = w3.to_wei(3, 'gwei')
            
            return {
                'low': float(w3.from_wei(base_fee + max_priority_fee_low, 'gwei')),
                'medium': float(w3.from_wei(base_fee + max_priority_fee_medium, 'gwei')),
                'high': float(w3.from_wei(base_fee + max_priority_fee_high, 'gwei')),
                'base_fee': float(w3.from_wei(base_fee, 'gwei'))
            }
        except:
            # Fallback for non-EIP-1559 chains
            gas_price_gwei = float(w3.from_wei(gas_price_wei, 'gwei'))
            return {
                'low': gas_price_gwei * 0.9,
                'medium': gas_price_gwei,
                'high': gas_price_gwei * 1.1,
                'base_fee': gas_price_gwei
            }

