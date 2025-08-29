# Uniswap V3 Liquidity Management Tool

A Python command-line tool for managing Uniswap V3 liquidity positions on Ethereum and Arbitrum blockchains. This tool provides secure credential storage, position tracking, and real-time price monitoring for your DeFi investments.

## Features

### 🔐 Secure Credential Storage
- **Encrypted Storage**: Private keys are encrypted using Fernet symmetric encryption
- **Secure File System**: Credentials stored with restrictive permissions (0600)
- **Key Management**: Separate storage of encryption keys and encrypted data
- **CLI Interface**: Easy-to-use commands for credential management
- **Multi-Account Support**: Store different keys for Ethereum and Arbitrum

### 📊 Position Tracking  
- **NFT Position Discovery**: Automatically finds all your Uniswap V3 liquidity NFTs
- **Token Amount Calculation**: Calculates current token amounts based on pool state
- **Fee Tracking**: Shows unclaimed fees for each position
- **Range Analysis**: Displays price ranges and whether positions are in/out of range
- **Multi-Chain Support**: Works seamlessly across Ethereum and Arbitrum

### 💰 Price Monitoring
- **Multiple Data Sources**:
  - CoinGecko API for major tokens
  - Direct Uniswap V3 pool queries for any token
- **Smart Price Routing**: Automatically finds best price path through WETH/stablecoin pools
- **Price Caching**: Reduces API calls and improves performance
- **USD Valuation**: Converts all positions to USD values for portfolio tracking

### Additional Features
- ⛓️ **Multi-Chain Support**: Works with Ethereum mainnet and Arbitrum
- 🎨 **Beautiful CLI**: Rich terminal interface with tables and colors  
- 🔍 **Detailed Analytics**: View position values, unclaimed fees, and total portfolio value
- ⚡ **Gas Price Monitoring**: Check current gas prices on both chains

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install from source

```bash
# Clone the repository
git clone https://github.com/zacharyking/liquidity_management.git
cd liquidity_management

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Configuration

### 1. Set up environment variables

Copy the example configuration and edit it:

```bash
cp env.example .env
```

Edit `.env` with your configuration:

```env
# Blockchain RPC URLs (required)
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_API_KEY

# Private keys can be set here or via CLI (recommended)
# ETHEREUM_PRIVATE_KEY=0x...
# ARBITRUM_PRIVATE_KEY=0x...

# Optional: API keys for enhanced features
ETHERSCAN_API_KEY=your_etherscan_api_key
ARBISCAN_API_KEY=your_arbiscan_api_key
```

### 2. Store credentials securely

```bash
# Set private key for Ethereum
liquidity credentials set --chain ethereum

# Set private key for Arbitrum
liquidity credentials set --chain arbitrum

# List stored credentials
liquidity credentials list

# Delete a credential
liquidity credentials delete --key ethereum_private_key
```

## Usage

### Check Connection Status

```bash
liquidity status
```

### View Your Positions

```bash
# List all positions on Ethereum
liquidity positions list --chain ethereum

# List positions with current USD prices
liquidity positions list --chain ethereum --show-prices

# Check positions for a specific address
liquidity positions list --chain arbitrum --address 0x...
```

### Check Token Prices

```bash
# Get price by symbol (for common tokens)
liquidity prices get --chain ethereum --token WETH
liquidity prices get --chain arbitrum --token ARB

# Get price by address
liquidity prices get --chain ethereum --token 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
```

### Check Balances

```bash
# Check ETH balance on Ethereum
liquidity balance --chain ethereum

# Check ETH balance on Arbitrum
liquidity balance --chain arbitrum
```

## Security

### Credential Storage

- Private keys are encrypted using the Fernet encryption scheme
- Credentials are stored in `~/.liquidity_manager/credentials.json`
- Files are created with restrictive permissions (owner read/write only)
- Encryption keys are stored separately from encrypted data

### Best Practices

1. **Never share your private keys or encryption keys**
2. **Use a dedicated wallet for DeFi interactions**
3. **Keep your `.env` file secure and never commit it to version control**
4. **Regularly backup your credentials and encryption keys**
5. **Use hardware wallets when possible for additional security**

## Examples

### Basic Usage Example

```python
from src.config import CredentialManager, settings
from src.web3_manager import Web3Manager
from src.uniswap_v3 import UniswapV3Tracker
from src.price_fetcher import PriceFetcher

# Initialize components
cred_manager = CredentialManager(settings.encryption_key)
web3_manager = Web3Manager(cred_manager)
tracker = UniswapV3Tracker(web3_manager)

# Get all positions on Ethereum
positions = tracker.get_positions("ethereum")

for position in positions:
    amounts = tracker.calculate_position_amounts(position)
    print(f"Position {position.token_id}:")
    print(f"  {amounts.amount0:.6f} {position.token0.symbol}")
    print(f"  {amounts.amount1:.6f} {position.token1.symbol}")
```

See the `examples/` directory for more detailed examples:
- `basic_usage.py` - Demonstrates all core functionality
- `advanced_usage.py` - Shows portfolio analysis and monitoring features

## Architecture

### Project Structure

```
liquidity_management/
├── src/
│   ├── __init__.py
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration and credential management
│   ├── web3_manager.py     # Web3 connection management
│   ├── uniswap_v3.py       # Uniswap V3 position tracking
│   ├── price_fetcher.py    # Token price fetching
│   └── contracts/
│       ├── __init__.py
│       └── uniswap_v3_abis.py  # Contract ABIs
├── examples/
│   ├── basic_usage.py      # Basic usage examples
│   └── advanced_usage.py   # Advanced usage examples
├── setup.py               # Package setup
├── requirements.txt       # Dependencies
├── env.example           # Example environment configuration
└── README.md             # This file
```

### Key Components

1. **CredentialManager**: Handles secure storage and retrieval of sensitive data
2. **Web3Manager**: Manages connections to multiple blockchain networks
3. **UniswapV3Tracker**: Tracks and analyzes Uniswap V3 positions
4. **PriceFetcher**: Fetches token prices from multiple sources
5. **CLI**: Provides user-friendly command-line interface

## Supported Tokens

The tool has built-in support for common tokens:

### Ethereum
- WETH (Wrapped Ether)
- USDC (USD Coin)
- USDT (Tether)
- DAI (Dai Stablecoin)
- WBTC (Wrapped Bitcoin)

### Arbitrum
- WETH (Wrapped Ether)
- USDC (USD Coin)
- USDT (Tether)
- DAI (Dai Stablecoin)
- WBTC (Wrapped Bitcoin)
- ARB (Arbitrum Token)

## API Requirements

### RPC Providers

You'll need RPC endpoints for Ethereum and Arbitrum. Recommended providers:
- [Alchemy](https://www.alchemy.com/)
- [Infura](https://infura.io/)
- [QuickNode](https://www.quicknode.com/)

### Price Data

Token prices are fetched from:
- CoinGecko API (free tier, no API key required)
- Uniswap V3 pools (on-chain data)

## Troubleshooting

### Connection Issues

If you're having connection issues:
1. Check your RPC URLs are correct
2. Ensure your API keys are valid
3. Verify network connectivity

### Missing Positions

If positions aren't showing:
1. Verify the correct wallet address
2. Ensure you're checking the right chain
3. Confirm the positions are Uniswap V3 (not V2)

### Price Fetching

If prices aren't loading:
1. The token might not be on CoinGecko
2. There might not be sufficient liquidity in Uniswap pools
3. Rate limits might be hit (wait a few minutes)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool interacts with decentralized finance protocols. Always verify transactions and be aware of the risks involved in DeFi. The authors are not responsible for any losses incurred through the use of this tool.
