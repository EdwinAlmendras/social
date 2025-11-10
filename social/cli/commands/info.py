"""Info command for CLI - Get video information without downloading."""
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from yt_dlp import YoutubeDL

from social.config import Config
from social.services.YT_Downloader import YT_Downloader
from social.logger import logger

app = typer.Typer()
console = Console()


@app.command()
def url(
    url: str = typer.Argument(..., help="URL to get information from"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Force specific platform"),
):
    """Get information about a video without downloading it."""
    try:
        config = Config()
        downloader = YT_Downloader(config)
        
        # Get platform
        platform_obj = None
        if platform:
            platform_lower = platform.lower()
            if platform_lower in downloader.platforms:
                platform_obj = downloader.platforms[platform_lower]
            else:
                console.print(f"[red]Error:[/red] Unknown platform '{platform}'")
                raise typer.Exit(1)
        
        # Extract info without downloading
        if not platform_obj:
            # Auto-detect platform
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                extractor = info.get('extractor', '').lower()
                platform_obj = downloader._get_platform_for_extractor(extractor)
        
        opts = platform_obj.get_ydl_opts()
        opts['skip_download'] = True
        opts['quiet'] = True
        
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        if json_output:
            import json
            console.print(json.dumps(info, indent=2, default=str))
        else:
            # Display formatted info
            table = Table(title=f"Video Information", show_header=True)
            table.add_column("Property", style="cyan", no_wrap=True)
            table.add_column("Value", style="white")
            
            # Key information
            fields = [
                ("Title", info.get('title', 'N/A')),
                ("Uploader", info.get('uploader', 'N/A')),
                ("Duration", f"{info.get('duration', 0)} seconds"),
                ("Views", f"{info.get('view_count', 0):,}"),
                ("Upload Date", info.get('upload_date', 'N/A')),
                ("Platform", info.get('extractor', 'N/A')),
                ("Video ID", info.get('id', 'N/A')),
                ("URL", info.get('webpage_url', url)),
            ]
            
            for field, value in fields:
                table.add_row(field, str(value))
            
            console.print(table)
            
            # Formats available
            if 'formats' in info and info['formats']:
                console.print(f"\n[cyan]Available formats:[/cyan] {len(info['formats'])}")
                
                format_table = Table(show_header=True)
                format_table.add_column("Format ID", style="cyan")
                format_table.add_column("Extension", style="yellow")
                format_table.add_column("Resolution", style="green")
                format_table.add_column("Note", style="white")
                
                # Show ALL formats, not just first 10
                for fmt in info['formats']:
                    format_table.add_row(
                        str(fmt.get('format_id', 'N/A')),
                        fmt.get('ext', 'N/A'),
                        fmt.get('resolution', 'N/A'),
                        fmt.get('format_note', 'N/A')
                    )
                
                console.print(format_table)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Info extraction error: {e}")
        raise typer.Exit(1)


@app.command()
def formats(
    url: str = typer.Argument(..., help="URL to list available formats"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Force specific platform"),
):
    """List all available formats for a video."""
    try:
        config = Config()
        downloader = YT_Downloader(config)
        
        platform_obj = None
        if platform:
            platform_lower = platform.lower()
            if platform_lower in downloader.platforms:
                platform_obj = downloader.platforms[platform_lower]
        
        if not platform_obj:
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                extractor = info.get('extractor', '').lower()
                platform_obj = downloader._get_platform_for_extractor(extractor)
        
        opts = platform_obj.get_ydl_opts()
        opts['skip_download'] = True
        opts['quiet'] = True
        
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        console.print(f"\n[cyan]Available formats for:[/cyan] {info.get('title', 'Unknown')}\n")
        
        table = Table(show_header=True)
        table.add_column("Format ID", style="cyan", no_wrap=True)
        table.add_column("Extension", style="yellow")
        table.add_column("Resolution", style="green")
        table.add_column("FPS", style="blue")
        table.add_column("Codec", style="magenta")
        table.add_column("Size", style="white")
        table.add_column("Note", style="dim")
        
        for fmt in info.get('formats', []):
            filesize = fmt.get('filesize') or fmt.get('filesize_approx', 0)
            size_mb = f"{filesize / (1024*1024):.1f} MB" if filesize else "N/A"
            
            table.add_row(
                str(fmt.get('format_id', 'N/A')),
                fmt.get('ext', 'N/A'),
                fmt.get('resolution', 'N/A'),
                str(fmt.get('fps', 'N/A')),
                fmt.get('vcodec', 'N/A')[:20],
                size_mb,
                fmt.get('format_note', '')[:30]
            )
        
        console.print(table)
        console.print(f"\n[dim]Total formats: {len(info.get('formats', []))}[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Format listing error: {e}")
        raise typer.Exit(1)
