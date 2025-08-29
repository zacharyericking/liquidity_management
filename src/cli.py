"""Command-line interface for liquidity management."""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from decimal import Decimal
from typing import Optional

from .config import CredentialManager, settings
from .web3_manager import Web3Manager
from .uniswap_v3 import UniswapV3Tracker
from .price_fetcher import PriceFetcher

console = Console()


@click.group()
@click.pass_context
def cli(ctx):
    """Uniswap V3 Liquidity Management Tool"""
    ctx.ensure_object(dict)
    ctx.obj['credential_manager'] = CredentialManager(settings.encryption_key)
    ctx.obj['web3_manager'] = Web3Manager(ctx.obj['credential_manager'])


@cli.group()
@click.pass_context
def credentials(ctx):
    """Manage blockchain credentials"""
    pass


@credentials.command()
@click.option('--chain', type=click.Choice(['ethereum', 'arbitrum']), required=True)
@click.option('--private-key', prompt=True, hide_input=True)
@click.pass_context
def set(ctx, chain, private_key):
    """Set private key for a blockchain"""
    try:
        web3_manager = ctx.obj['web3_manager']
        account = web3_manager.set_account(chain, private_key, save=True)
        
        console.print(f"[green]✓[/green] Private key saved for {chain}")
        console.print(f"Address: [cyan]{account.address}[/cyan]")
        
        # Show balance
        balance = web3_manager.get_balance(chain, account.address)
        console.print(f"Balance: [yellow]{balance:.4f} ETH[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@credentials.command()
@click.pass_context
def list(ctx):
    """List stored credentials"""
    credential_manager = ctx.obj['credential_manager']
    creds = credential_manager.list_credentials()
    
    if not creds:
        console.print("[yellow]No credentials stored[/yellow]")
        return
    
    table = Table(title="Stored Credentials")
    table.add_column("Key", style="cyan")
    table.add_column("Type", style="green")
    
    for cred in creds:
        if "private_key" in cred:
            cred_type = "Private Key"
        else:
            cred_type = "API Key"
        table.add_row(cred, cred_type)
    
    console.print(table)


@credentials.command()
@click.option('--key', required=True)
@click.pass_context
def delete(ctx, key):
    """Delete a stored credential"""
    credential_manager = ctx.obj['credential_manager']
    
    if Confirm.ask(f"Delete credential '{key}'?"):
        if credential_manager.delete_credential(key):
            console.print(f"[green]✓[/green] Credential '{key}' deleted")
        else:
            console.print(f"[red]Credential '{key}' not found[/red]")


@cli.group()
@click.pass_context
def positions(ctx):
    """Manage Uniswap V3 positions"""
    pass


@positions.command()
@click.option('--chain', type=click.Choice(['ethereum', 'arbitrum']), required=True)
@click.option('--address', help='Address to check (uses configured address if not provided)')
@click.option('--show-prices', is_flag=True, help='Fetch and show current token prices')
@click.pass_context
def list(ctx, chain, address, show_prices):
    """List all Uniswap V3 positions"""
    web3_manager = ctx.obj['web3_manager']
    
    try:
        # Connect to chain
        w3 = web3_manager.connect(chain)
        
        # Get address if not provided
        if not address:
            account = web3_manager.get_account(chain)
            if not account:
                console.print(f"[red]No account configured for {chain}[/red]")
                console.print("Run: liquidity credentials set --chain {chain}")
                return
            address = account.address
        
        console.print(f"[cyan]Fetching positions for {address} on {chain}...[/cyan]")
        
        # Get positions
        tracker = UniswapV3Tracker(web3_manager)
        positions = tracker.get_positions(chain, address)
        
        if not positions:
            console.print("[yellow]No Uniswap V3 positions found[/yellow]")
            return
        
        # Initialize price fetcher if needed
        price_fetcher = PriceFetcher(web3_manager) if show_prices else None
        
        # Display positions
        for i, position in enumerate(positions):
            # Calculate position amounts
            position_value = tracker.calculate_position_amounts(position)
            
            # Create position table
            table = Table(title=f"Position #{i+1} - Token ID: {position.token_id}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")
            
            # Basic info
            table.add_row("Pool", f"{position.token0.symbol}/{position.token1.symbol}")
            table.add_row("Fee Tier", f"{position.fee_tier/10000}%")
            table.add_row("Token 0", f"{position.token0.symbol} ({position.token0.address[:10]}...)")
            table.add_row("Token 1", f"{position.token1.symbol} ({position.token1.address[:10]}...)")
            
            # Price range
            table.add_row("Tick Lower", str(position.tick_lower))
            table.add_row("Tick Upper", str(position.tick_upper))
            
            # Amounts
            table.add_row("Amount 0", f"{position_value.amount0:.6f} {position.token0.symbol}")
            table.add_row("Amount 1", f"{position_value.amount1:.6f} {position.token1.symbol}")
            
            # Unclaimed fees
            if position_value.unclaimed_fees0 > 0 or position_value.unclaimed_fees1 > 0:
                table.add_row("Unclaimed Fees 0", f"{position_value.unclaimed_fees0:.6f} {position.token0.symbol}")
                table.add_row("Unclaimed Fees 1", f"{position_value.unclaimed_fees1:.6f} {position.token1.symbol}")
            
            # Prices and total value
            if show_prices and price_fetcher:
                price0 = price_fetcher.get_token_price_usd(chain, position.token0.address)
                price1 = price_fetcher.get_token_price_usd(chain, position.token1.address)
                
                if price0:
                    table.add_row(f"{position.token0.symbol} Price", f"${price0:.2f}")
                if price1:
                    table.add_row(f"{position.token1.symbol} Price", f"${price1:.2f}")
                
                if price0 and price1:
                    total_value = (
                        float(position_value.amount0) * price0 +
                        float(position_value.amount1) * price1 +
                        float(position_value.unclaimed_fees0) * price0 +
                        float(position_value.unclaimed_fees1) * price1
                    )
                    table.add_row("Total Value USD", f"[green]${total_value:,.2f}[/green]")
            
            # Pool contract
            table.add_row("Pool Address", position.pool_address)
            
            console.print(table)
            console.print()
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@cli.group()
@click.pass_context
def prices(ctx):
    """Get token prices"""
    pass


@prices.command()
@click.option('--chain', type=click.Choice(['ethereum', 'arbitrum']), required=True)
@click.option('--token', required=True, help='Token address or symbol (WETH, USDC, etc.)')
@click.pass_context
def get(ctx, chain, token):
    """Get current price for a token"""
    web3_manager = ctx.obj['web3_manager']
    
    try:
        # Connect to chain
        w3 = web3_manager.connect(chain)
        
        # Check if token is a symbol
        from .price_fetcher import PriceFetcher
        common_tokens = PriceFetcher.COMMON_TOKENS.get(chain, {})
        
        if token.upper() in common_tokens:
            token_address = common_tokens[token.upper()]
            token_symbol = token.upper()
        else:
            # Assume it's an address
            token_address = token
            # Get token info
            tracker = UniswapV3Tracker(web3_manager)
            token_info = tracker._get_token_info(chain, token_address)
            token_symbol = token_info.symbol
        
        console.print(f"[cyan]Fetching price for {token_symbol}...[/cyan]")
        
        # Get price
        price_fetcher = PriceFetcher(web3_manager)
        price = price_fetcher.get_token_price_usd(chain, token_address)
        
        if price:
            console.print(f"[green]{token_symbol} Price:[/green] ${price:.4f}")
        else:
            console.print(f"[red]Could not fetch price for {token_symbol}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@cli.command()
@click.option('--chain', type=click.Choice(['ethereum', 'arbitrum']), required=True)
@click.pass_context
def balance(ctx, chain):
    """Check ETH balance"""
    web3_manager = ctx.obj['web3_manager']
    
    try:
        account = web3_manager.get_account(chain)
        if not account:
            console.print(f"[red]No account configured for {chain}[/red]")
            return
        
        balance = web3_manager.get_balance(chain)
        
        table = Table(title=f"{chain.capitalize()} Balance")
        table.add_column("Address", style="cyan")
        table.add_column("Balance", style="green")
        
        table.add_row(account.address, f"{balance:.6f} ETH")
        
        console.print(table)
        
        # Get gas price
        gas_prices = web3_manager.get_gas_price(chain)
        console.print(f"\nGas Prices (Gwei):")
        console.print(f"  Low: {gas_prices['low']:.1f}")
        console.print(f"  Medium: {gas_prices['medium']:.1f}")
        console.print(f"  High: {gas_prices['high']:.1f}")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@cli.command()
@click.pass_context
def status(ctx):
    """Show connection status for all chains"""
    web3_manager = ctx.obj['web3_manager']
    
    table = Table(title="Connection Status")
    table.add_column("Chain", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Account", style="yellow")
    table.add_column("Balance", style="white")
    
    for chain in ['ethereum', 'arbitrum']:
        try:
            w3 = web3_manager.connect(chain)
            status = "[green]Connected[/green]"
            
            account = web3_manager.get_account(chain)
            if account:
                address = f"{account.address[:6]}...{account.address[-4:]}"
                balance = f"{web3_manager.get_balance(chain):.4f} ETH"
            else:
                address = "[red]Not configured[/red]"
                balance = "-"
                
        except Exception as e:
            status = "[red]Failed[/red]"
            address = "-"
            balance = "-"
        
        table.add_row(chain.capitalize(), status, address, balance)
    
    console.print(table)


def main():
    """Main entry point"""
    cli()

