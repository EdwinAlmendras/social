"""Upload command for CLI."""
import typer
import asyncio
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from social.config import Config
from social.services.social_flow_service import SocialFlowService
from social.logger import logger

app = typer.Typer()
console = Console()


def _parse_urls(urls_input: str) -> List[str]:
    """
    Parse URLs from a single input string.
    
    Supports:
    - Comma-separated URLs: "url1,url2,url3"
    - File path: "urls.txt"
    
    Args:
        urls_input: String with URLs or file path
        
    Returns:
        List of parsed URLs
    """
    parsed_urls = []
    
    # Check if it's a file
    if Path(urls_input).exists() and Path(urls_input).is_file():
        # Read URLs from file
        with open(urls_input, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parsed_urls.append(line)
    else:
        # Check if it contains commas (multiple URLs)
        if ',' in urls_input:
            parsed_urls.extend([u.strip() for u in urls_input.split(',') if u.strip()])
        else:
            parsed_urls.append(urls_input)
    
    return parsed_urls


@app.callback(invoke_without_command=True)
def upload(
    ctx: typer.Context,
    urls: Optional[str] = typer.Argument(None, help="URLs (comma-separated) or file path with URLs"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Path to Telegram session file"),
    bot_session: Optional[str] = typer.Option(None, "--bot-session", "-b", help="Path to bot session file"),
    skip_errors: bool = typer.Option(True, "--skip-errors", help="Continue on errors"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
    use_channel: bool = typer.Option(False, "--use-channel", "-u", help="Create channel topic and upload all videos there"),
    skip_validation: bool = typer.Option(False, "--skip-validation", help="Skip platform validation (only with --use-channel)"),
    parallel: Optional[int] = typer.Option(None, "--parallel", "-p", help="Max parallel downloads (default: from config or 5)"),
):
    """
    Process and upload videos to Telegram using social flow.
    
    This command downloads videos from the provided URLs and automatically
    uploads them to the configured Telegram channels/topics.
    
    Examples:
    
      # Single URL (standard mode)
      social upload "https://youtube.com/watch?v=VIDEO_ID"
      
      # Multiple URLs (comma-separated - REQUIRED format)
      social upload "URL1,URL2,URL3"
      
      # From file
      social upload urls.txt
      
      # Channel mode: Create topic from first URL and upload all videos there
      social upload "URL1,URL2,URL3" -u
      
      # Channel mode with platform validation skipped
      social upload "URL1,URL2,URL3" -u --skip-validation
      
      # With custom session
      social upload urls.txt --session custom.session
    """
    # If no URLs and no subcommand, show help
    if not urls and ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()
    
    # If there's a subcommand, let it handle
    if ctx.invoked_subcommand is not None:
        return
    
    try:
        # Parse URLs
        parsed_urls = _parse_urls(urls)
        
        if not parsed_urls:
            console.print("[yellow]No URLs provided[/yellow]")
            raise typer.Exit(0)
        
        if not quiet:
            console.print(f"[cyan]Found {len(parsed_urls)} URL(s) to process[/cyan]")
        
        # Initialize config
        config = Config()
        
        # Run async upload (service will be created inside with telegram_client)
        asyncio.run(_run_upload(
            parsed_urls,
            session,
            bot_session,
            skip_errors,
            quiet,
            use_channel,
            skip_validation,
            config,
            parallel
        ))
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"CLI error: {e}")
        raise typer.Exit(1)


async def _run_upload(
    urls: List[str],
    session: Optional[str],
    bot_session: Optional[str],
    skip_errors: bool,
    quiet: bool,
    use_channel: bool,
    skip_validation: bool,
    config: Config,
    parallel: Optional[int] = None
):
    """Run the upload process asynchronously."""
    from telethon import TelegramClient
    from social.cli.upload_strategy import UploadStrategyFactory
    
    # Validate Telegram configuration
    is_valid, error_msg = config.validate_telegram_config()
    if not is_valid:
        console.print(f"[red]Error:[/red] {error_msg}")
        console.print("[yellow]Tip:[/yellow] Set these variables in ~/.config/social/.env")
        raise typer.Exit(1)
    
    # Get session paths using centralized config
    session_file = config.get_telegram_session_file(session)
    bot_session_file = config.get_bot_session_file(bot_session)
    
    if not quiet:
        console.print("[cyan]Connecting to Telegram...[/cyan]")
        console.print(f"[dim]Session file: {session_file}[/dim]")
        console.print(f"[dim]Bot session file: {bot_session_file}[/dim]")
    
    # Create clients using centralized config
    telegram_client = TelegramClient(str(session_file), config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    bot_client = TelegramClient(str(bot_session_file), config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    
    try:
        # Connect clients
        await telegram_client.start()
        await bot_client.start(bot_token=config.BOT_TOKEN)
        
        if not quiet:
            console.print("[green]Connected to Telegram[/green]")
        
        # Initialize service with telegram_client for recovery support
        service = SocialFlowService(config, telegram_client=telegram_client)
        
        # Create upload strategy
        strategy = UploadStrategyFactory.create(
            use_channel_mode=use_channel,
            skip_validation=skip_validation
        )
        
        if not quiet:
            mode = "channel" if use_channel else "standard"
            max_parallel = parallel or config.MAX_PARALLEL_DOWNLOADS
            console.print(f"[cyan]Upload mode: {mode}[/cyan]")
            if len(urls) > 1:
                console.print(f"[cyan]Max parallel downloads: {max_parallel}[/cyan]")
        
        # Execute strategy
        results = await strategy.execute(
            urls=urls,
            service=service,
            telegram_client=telegram_client,
            bot_client=bot_client,
            config=config,
            quiet=quiet,
            max_parallel=parallel
        )
        
        success_count = results['success_count']
        error_count = results['error_count']
        
        # Summary
        if not quiet and len(urls) > 1:
            console.print(f"\n[cyan]Summary:[/cyan]")
            if use_channel:
                console.print(f"  Topic ID: {results.get('topic_id')}")
                console.print(f"  Platform: {results.get('platform')}")
            console.print(f"  [green]✓ Successful:[/green] {success_count}")
            if error_count > 0:
                console.print(f"  [red]✗ Failed:[/red] {error_count}")
        
        if error_count > 0 and not skip_errors:
            raise typer.Exit(1)
    
    finally:
        # Disconnect clients
        await telegram_client.disconnect()
        await bot_client.disconnect()

