"""Uniswap V3 position tracker and analyzer."""
import math
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass

from web3 import Web3
from .web3_manager import Web3Manager
from .contracts.uniswap_v3_abis import (
    POSITION_MANAGER_ABI, POOL_ABI, FACTORY_ABI, ERC20_ABI
)
from .config import settings


@dataclass
class TokenInfo:
    """Information about a token."""
    address: str
    symbol: str
    name: str
    decimals: int


@dataclass
class PositionInfo:
    """Information about a Uniswap V3 position."""
    token_id: int
    pool_address: str
    token0: TokenInfo
    token1: TokenInfo
    fee_tier: int
    tick_lower: int
    tick_upper: int
    liquidity: int
    tokens_owed0: Decimal
    tokens_owed1: Decimal
    fee_growth_inside0_last: int
    fee_growth_inside1_last: int
    chain: str


@dataclass
class PositionValue:
    """Value and amounts in a position."""
    amount0: Decimal
    amount1: Decimal
    unclaimed_fees0: Decimal
    unclaimed_fees1: Decimal
    price_token0_usd: Optional[float] = None
    price_token1_usd: Optional[float] = None
    total_value_usd: Optional[float] = None


class UniswapV3Tracker:
    """Tracks and analyzes Uniswap V3 positions."""
    
    def __init__(self, web3_manager: Web3Manager):
        """Initialize the tracker with a Web3Manager."""
        self.web3_manager = web3_manager
        self.position_manager_address = Web3.to_checksum_address(
            settings.uniswap_v3_nft_manager_address
        )
        self.factory_address = Web3.to_checksum_address(
            settings.uniswap_v3_factory_address
        )
    
    def get_positions(self, chain: str, address: Optional[str] = None) -> List[PositionInfo]:
        """Get all Uniswap V3 positions for an address."""
        w3 = self.web3_manager.connect(chain)
        
        # Get address if not provided
        if not address:
            account = self.web3_manager.get_account(chain)
            if not account:
                raise ValueError(f"No account configured for {chain}")
            address = account.address
        
        address = Web3.to_checksum_address(address)
        
        # Get position manager contract
        position_manager = self.web3_manager.get_contract(
            chain, self.position_manager_address, POSITION_MANAGER_ABI
        )
        
        # Get number of positions
        balance = position_manager.functions.balanceOf(address).call()
        
        positions = []
        for i in range(balance):
            # Get token ID
            token_id = position_manager.functions.tokenOfOwnerByIndex(address, i).call()
            
            # Get position details
            position_data = position_manager.functions.positions(token_id).call()
            
            # Get token information
            token0_info = self._get_token_info(chain, position_data[2])
            token1_info = self._get_token_info(chain, position_data[3])
            
            # Get pool address
            factory = self.web3_manager.get_contract(
                chain, self.factory_address, FACTORY_ABI
            )
            pool_address = factory.functions.getPool(
                position_data[2], position_data[3], position_data[4]
            ).call()
            
            position = PositionInfo(
                token_id=token_id,
                pool_address=pool_address,
                token0=token0_info,
                token1=token1_info,
                fee_tier=position_data[4],
                tick_lower=position_data[5],
                tick_upper=position_data[6],
                liquidity=position_data[7],
                fee_growth_inside0_last=position_data[8],
                fee_growth_inside1_last=position_data[9],
                tokens_owed0=Decimal(position_data[10]),
                tokens_owed1=Decimal(position_data[11]),
                chain=chain
            )
            
            positions.append(position)
        
        return positions
    
    def _get_token_info(self, chain: str, token_address: str) -> TokenInfo:
        """Get token information."""
        token_contract = self.web3_manager.get_contract(
            chain, token_address, ERC20_ABI
        )
        
        try:
            symbol = token_contract.functions.symbol().call()
        except:
            symbol = "UNKNOWN"
        
        try:
            name = token_contract.functions.name().call()
        except:
            name = "Unknown Token"
        
        try:
            decimals = token_contract.functions.decimals().call()
        except:
            decimals = 18
        
        return TokenInfo(
            address=token_address,
            symbol=symbol,
            name=name,
            decimals=decimals
        )
    
    def calculate_position_amounts(self, position: PositionInfo) -> PositionValue:
        """Calculate current token amounts in a position."""
        if position.liquidity == 0:
            return PositionValue(
                amount0=Decimal(0),
                amount1=Decimal(0),
                unclaimed_fees0=position.tokens_owed0,
                unclaimed_fees1=position.tokens_owed1
            )
        
        # Get pool contract
        pool = self.web3_manager.get_contract(
            position.chain, position.pool_address, POOL_ABI
        )
        
        # Get current pool state
        slot0 = pool.functions.slot0().call()
        sqrt_price_x96 = slot0[0]
        current_tick = slot0[1]
        
        # Calculate amounts
        amounts = self._calculate_position_amounts_from_liquidity(
            position.liquidity,
            sqrt_price_x96,
            position.tick_lower,
            position.tick_upper,
            position.token0.decimals,
            position.token1.decimals
        )
        
        return PositionValue(
            amount0=amounts[0],
            amount1=amounts[1],
            unclaimed_fees0=Decimal(position.tokens_owed0) / Decimal(10 ** position.token0.decimals),
            unclaimed_fees1=Decimal(position.tokens_owed1) / Decimal(10 ** position.token1.decimals)
        )
    
    def _calculate_position_amounts_from_liquidity(
        self,
        liquidity: int,
        sqrt_price_x96: int,
        tick_lower: int,
        tick_upper: int,
        decimals0: int,
        decimals1: int
    ) -> Tuple[Decimal, Decimal]:
        """Calculate token amounts from liquidity and price."""
        # Convert ticks to sqrt prices
        sqrt_ratio_a = self._get_sqrt_ratio_at_tick(tick_lower)
        sqrt_ratio_b = self._get_sqrt_ratio_at_tick(tick_upper)
        
        # Current price is below range
        if sqrt_price_x96 <= sqrt_ratio_a:
            amount0 = self._get_amount0_delta(sqrt_ratio_a, sqrt_ratio_b, liquidity)
            amount1 = 0
        # Current price is above range
        elif sqrt_price_x96 >= sqrt_ratio_b:
            amount0 = 0
            amount1 = self._get_amount1_delta(sqrt_ratio_a, sqrt_ratio_b, liquidity)
        # Current price is in range
        else:
            amount0 = self._get_amount0_delta(sqrt_price_x96, sqrt_ratio_b, liquidity)
            amount1 = self._get_amount1_delta(sqrt_ratio_a, sqrt_price_x96, liquidity)
        
        # Convert to decimal with proper decimals
        amount0_decimal = Decimal(amount0) / Decimal(10 ** decimals0)
        amount1_decimal = Decimal(amount1) / Decimal(10 ** decimals1)
        
        return (amount0_decimal, amount1_decimal)
    
    def _get_sqrt_ratio_at_tick(self, tick: int) -> int:
        """Get sqrt price from tick."""
        return int(math.sqrt(1.0001 ** tick) * (2 ** 96))
    
    def _get_amount0_delta(self, sqrt_ratio_a: int, sqrt_ratio_b: int, liquidity: int) -> int:
        """Calculate amount0 delta."""
        if sqrt_ratio_a > sqrt_ratio_b:
            sqrt_ratio_a, sqrt_ratio_b = sqrt_ratio_b, sqrt_ratio_a
        
        numerator = liquidity * 2 ** 96 * (sqrt_ratio_b - sqrt_ratio_a)
        denominator = sqrt_ratio_b * sqrt_ratio_a
        
        return numerator // denominator
    
    def _get_amount1_delta(self, sqrt_ratio_a: int, sqrt_ratio_b: int, liquidity: int) -> int:
        """Calculate amount1 delta."""
        if sqrt_ratio_a > sqrt_ratio_b:
            sqrt_ratio_a, sqrt_ratio_b = sqrt_ratio_b, sqrt_ratio_a
        
        return liquidity * (sqrt_ratio_b - sqrt_ratio_a) // 2 ** 96
    
    def get_pool_price(self, chain: str, pool_address: str) -> Tuple[float, float]:
        """Get current price from pool (price of token0 in terms of token1 and vice versa)."""
        pool = self.web3_manager.get_contract(chain, pool_address, POOL_ABI)
        
        # Get pool info
        token0_address = pool.functions.token0().call()
        token1_address = pool.functions.token1().call()
        
        token0_info = self._get_token_info(chain, token0_address)
        token1_info = self._get_token_info(chain, token1_address)
        
        # Get current price
        slot0 = pool.functions.slot0().call()
        sqrt_price_x96 = slot0[0]
        
        # Calculate prices
        price_0_1 = (sqrt_price_x96 / 2**96) ** 2 * (10 ** token0_info.decimals) / (10 ** token1_info.decimals)
        price_1_0 = 1 / price_0_1 if price_0_1 > 0 else 0
        
        return (price_0_1, price_1_0)

