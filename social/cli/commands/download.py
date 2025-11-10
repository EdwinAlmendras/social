"""Download command for CLI."""
import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console

from social.config import Config
from social.services.YT_Downloader import YT_Downloader
from social.logger import logger

app = typer.Typer()
console = Console()


def _parse_urls(urls: List[str]) -> List[str]:
    """Parse URLs from arguments, handling comma-separated values and files."""
    parsed_urls = []
    
    for url_arg in urls:
        # Check if it's a file
        if Path(url_arg).exists() and Path(url_arg).is_file():
            # Read URLs from file
            with open(url_arg, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parsed_urls.append(line)
        else:
            # Check if it contains commas (multiple URLs)
            if ',' in url_arg:
                parsed_urls.extend([u.strip() for u in url_arg.split(',') if u.strip()])
            else:
                parsed_urls.append(url_arg)
    
    return parsed_urls


@app.callback(invoke_without_command=True)
def download(
    ctx: typer.Context,
    urls: List[str] = typer.Argument(None, help="URLs to download (comma-separated, or path to file with URLs)"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Force specific platform (youtube, vk, rutube)"),
    format: Optional[str] = typer.Option(None, "--format", "-f", help="Video format (e.g., 'best', 'worst', 'bestvideo+bestaudio')"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Custom output directory"),
    cookies: Optional[str] = typer.Option(None, "--cookies", "-c", help="Path to cookies file"),
    metadata: bool = typer.Option(False, "--metadata", "-m", help="Save video metadata as JSON"),
    thumbnail: bool = typer.Option(False, "--thumbnail", "-t", help="Download video thumbnail"),
    skip_errors: bool = typer.Option(True, "--skip-errors", help="Continue on errors"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
):
    """
    Download videos from URLs.
    
    Examples:
    
      # Single URL
      social download "https://youtube.com/watch?v=VIDEO_ID"
      
      # Multiple URLs (comma-separated)
      social download "URL1,URL2,URL3"
      
      # Multiple URLs (space-separated)
      social download URL1 URL2 URL3
      
      # From file
      social download urls.txt
      
      # With options
      social download URL --format best --metadata --thumbnail
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
        
        # Initialize config
        config = Config()
        
        # Override output directory if specified
        if output_dir:
            config.DOWNLOADS_DIR = Path(output_dir)
            config.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize downloader
        downloader = YT_Downloader(config)
        
        # Get platform if specified
        platform_obj = None
        if platform:
            platform_lower = platform.lower()
            if platform_lower in downloader.platforms:
                platform_obj = downloader.platforms[platform_lower]
                
                # Apply custom format if specified
                if format:
                    platform_obj.format = format
                
                # Apply custom cookies if specified
                if cookies:
                    platform_obj.cookies = Path(cookies)
                
                # Apply extra options
                if metadata or thumbnail:
                    platform_obj.extra_opts = platform_obj.extra_opts or {}
                    if metadata:
                        platform_obj.extra_opts['writeinfojson'] = True
                    if thumbnail:
                        platform_obj.extra_opts['writethumbnail'] = True
            else:
                console.print(f"[red]Error:[/red] Unknown platform '{platform}'")
                console.print(f"Available platforms: {', '.join(downloader.platforms.keys())}")
                raise typer.Exit(1)
        
        # Download statistics
        success_count = 0
        error_count = 0
        
        # Download each URL
        for i, url in enumerate(parsed_urls, 1):
            if not quiet and len(parsed_urls) > 1:
                console.print(f"\n[cyan][{i}/{len(parsed_urls)}] Downloading:[/cyan] {url}")
            
            try:
                downloader.download(url, platform=platform_obj)
                success_count += 1
                
                if not quiet and len(parsed_urls) > 1:
                    console.print(f"[green]✓ Success[/green]")
            
            except Exception as e:
                error_count += 1
                if not quiet:
                    console.print(f"[red]✗ Failed:[/red] {str(e)}")
                logger.error(f"Download failed for {url}: {e}")
                
                if not skip_errors:
                    raise typer.Exit(1)
        
        # Summary
        if not quiet and len(parsed_urls) > 1:
            console.print(f"\n[cyan]Summary:[/cyan]")
            console.print(f"  [green]✓ Successful:[/green] {success_count}")
            if error_count > 0:
                console.print(f"  [red]✗ Failed:[/red] {error_count}")
        
        if error_count > 0 and not skip_errors:
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"CLI error: {e}")
        raise typer.Exit(1)
