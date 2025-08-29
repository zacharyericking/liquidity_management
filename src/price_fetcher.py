"""Token price fetching functionality."""
import requests
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
import json
from time import time, sleep

from web3 import Web3
from .web3_manager import Web3Manager
from .contracts.uniswap_v3_abis import POOL_ABI, FACTORY_ABI, ERC20_ABI


class PriceFetcher:
    """Fetches token prices from various sources."""
    
    # Common token addresses (checksummed)
    COMMON_TOKENS = {
        "ethereum": {
            "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
            "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        },
        "arbitrum": {
            "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
            "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
            "WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
            "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548",
        }
    }
    
    # CoinGecko token IDs mapping
    COINGECKO_IDS = {
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": "ethereum",
        "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1": "ethereum",
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": "usd-coin",
        "0xaf88d065e77c8cC2239327C5EDb3A432268e5831": "usd-coin",
        "0xdAC17F958D2ee523a2206206994597C13D831ec7": "tether",
        "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9": "tether",
        "0x6B175474E89094C44Da98b954EedeAC495271d0F": "dai",
        "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1": "dai",
        "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599": "wrapped-bitcoin",
        "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f": "wrapped-bitcoin",
        "0x912CE59144191C1204E64559FE8253a0e49E6548": "arbitrum",
    }
    
    def __init__(self, web3_manager: Web3Manager):
        """Initialize price fetcher."""
        self.web3_manager = web3_manager
        self._price_cache: Dict[str, Tuple[float, float]] = {}  # token_address -> (price, timestamp)
        self._cache_duration = 300  # 5 minutes
    
    def get_token_price_usd(self, chain: str, token_address: str) -> Optional[float]:
        """Get token price in USD from various sources."""
        token_address = Web3.to_checksum_address(token_address)
        
        # Check cache
        cached_price = self._get_cached_price(token_address)
        if cached_price is not None:
            return cached_price
        
        # Try CoinGecko first
        price = self._get_coingecko_price(token_address)
        if price:
            self._cache_price(token_address, price)
            return price
        
        # Try to calculate via Uniswap pools
        price = self._get_uniswap_price(chain, token_address)
        if price:
            self._cache_price(token_address, price)
            return price
        
        return None
    
    def _get_cached_price(self, token_address: str) -> Optional[float]:
        """Get price from cache if still valid."""
        if token_address in self._price_cache:
            price, timestamp = self._price_cache[token_address]
            if time() - timestamp < self._cache_duration:
                return price
        return None
    
    def _cache_price(self, token_address: str, price: float):
        """Cache a price with timestamp."""
        self._price_cache[token_address] = (price, time())
    
    def _get_coingecko_price(self, token_address: str) -> Optional[float]:
        """Get price from CoinGecko API."""
        if token_address not in self.COINGECKO_IDS:
            return None
        
        coin_id = self.COINGECKO_IDS[token_address]
        
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if coin_id in data and 'usd' in data[coin_id]:
                return float(data[coin_id]['usd'])
        except Exception as e:
            print(f"CoinGecko API error: {e}")
        
        return None
    
    def _get_uniswap_price(self, chain: str, token_address: str) -> Optional[float]:
        """Get price from Uniswap pools."""
        token_address = Web3.to_checksum_address(token_address)
        
        # Check if token is a stablecoin
        stablecoins = [
            self.COMMON_TOKENS[chain].get("USDC"),
            self.COMMON_TOKENS[chain].get("USDT"),
            self.COMMON_TOKENS[chain].get("DAI")
        ]
        
        if token_address in stablecoins:
            return 1.0
        
        # Try to find price through WETH
        weth_address = self.COMMON_TOKENS[chain]["WETH"]
        if token_address == weth_address:
            # Get ETH price from USDC pool
            return self._get_eth_price(chain)
        
        # Get price through WETH
        weth_price = self._get_pool_price_for_tokens(
            chain, token_address, weth_address, [3000, 10000, 500]  # Common fee tiers
        )
        
        if weth_price:
            eth_usd_price = self._get_eth_price(chain)
            if eth_usd_price:
                return weth_price * eth_usd_price
        
        # Try direct stablecoin pairs
        for stable in stablecoins:
            if stable:
                price = self._get_pool_price_for_tokens(
                    chain, token_address, stable, [3000, 10000, 500, 100]
                )
                if price:
                    return price
        
        return None
    
    def _get_eth_price(self, chain: str) -> Optional[float]:
        """Get ETH price in USD from WETH/USDC pool."""
        weth_address = self.COMMON_TOKENS[chain]["WETH"]
        usdc_address = self.COMMON_TOKENS[chain]["USDC"]
        
        price = self._get_pool_price_for_tokens(
            chain, weth_address, usdc_address, [3000, 500]
        )
        
        return price
    
    def _get_pool_price_for_tokens(
        self, 
        chain: str, 
        token0: str, 
        token1: str, 
        fee_tiers: List[int]
    ) -> Optional[float]:
        """Get price from Uniswap pool for token pair."""
        factory = self.web3_manager.get_contract(
            chain, 
            Web3.to_checksum_address("0x1F98431c8aD98523631AE4a59f267346ea31F984"),
            FACTORY_ABI
        )
        
        token0 = Web3.to_checksum_address(token0)
        token1 = Web3.to_checksum_address(token1)
        
        for fee in fee_tiers:
            try:
                pool_address = factory.functions.getPool(token0, token1, fee).call()
                
                if pool_address != "0x0000000000000000000000000000000000000000":
                    pool = self.web3_manager.get_contract(chain, pool_address, POOL_ABI)
                    
                    # Get tokens order in pool
                    pool_token0 = pool.functions.token0().call()
                    pool_token1 = pool.functions.token1().call()
                    
                    # Get decimals
                    token0_contract = self.web3_manager.get_contract(chain, pool_token0, ERC20_ABI)
                    token1_contract = self.web3_manager.get_contract(chain, pool_token1, ERC20_ABI)
                    
                    decimals0 = token0_contract.functions.decimals().call()
                    decimals1 = token1_contract.functions.decimals().call()
                    
                    # Get price
                    slot0 = pool.functions.slot0().call()
                    sqrt_price_x96 = slot0[0]
                    
                    # Calculate price
                    price = (sqrt_price_x96 / 2**96) ** 2
                    price = price * (10 ** decimals0) / (10 ** decimals1)
                    
                    # Return price of token0 in terms of token1
                    if pool_token0.lower() == token0.lower():
                        return float(price)
                    else:
                        return float(1 / price) if price > 0 else None
                        
            except Exception as e:
                continue
        
        return None
    
    def get_multiple_prices(self, chain: str, token_addresses: List[str]) -> Dict[str, Optional[float]]:
        """Get prices for multiple tokens efficiently."""
        prices = {}
        
        for address in token_addresses:
            prices[address] = self.get_token_price_usd(chain, address)
            # Rate limit to avoid hitting API limits
            sleep(0.1)
        
        return prices

