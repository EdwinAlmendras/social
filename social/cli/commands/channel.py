"""Channel command for CLI - Get channel information from video or channel URLs."""
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from datetime import datetime

from social.config import Config
from social.services.channel_info_service import ChannelInfoService
from social.logger import logger

app = typer.Typer()
console = Console()


@app.command()
def info(
    url: str = typer.Argument(..., help="URL of a video or channel to get channel information from"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Get channel information from a video or channel URL."""
    try:
        config = Config()
        service = ChannelInfoService(config)
        
        console.print(f"[cyan]Extracting channel information from:[/cyan] {url}\n")
        
        channel_info = service.get_channel_info(url)
        
        if not channel_info:
            console.print("[red]Error:[/red] Could not extract channel information")
            raise typer.Exit(1)
        
        if json_output:
            import json
            console.print(json.dumps(channel_info, indent=2, default=str, ensure_ascii=False))
        else:
            # Display formatted channel info
            table = Table(title="Channel Information", show_header=True, header_style="bold cyan")
            table.add_column("Property", style="cyan", no_wrap=True)
            table.add_column("Value", style="white")
            
            # Basic channel information
            if channel_info.get('channel'):
                table.add_row("Channel Name", channel_info['channel'])
            if channel_info.get('channel_id'):
                table.add_row("Channel ID", channel_info['channel_id'])
            if channel_info.get('channel_url'):
                table.add_row("Channel URL", channel_info['channel_url'])
            if channel_info.get('uploader'):
                table.add_row("Uploader", channel_info['uploader'])
            if channel_info.get('uploader_id'):
                table.add_row("Uploader ID", channel_info['uploader_id'])
            if channel_info.get('uploader_url'):
                table.add_row("Uploader URL", channel_info['uploader_url'])
            
            # Statistics
            if channel_info.get('channel_follower_count'):
                table.add_row("Followers", f"{channel_info['channel_follower_count']:,}")
            
            # TikTok-specific stats
            if channel_info.get('following_count'):
                table.add_row("Following", f"{channel_info['following_count']:,}")
            if channel_info.get('heart_count'):
                table.add_row("Hearts/Likes", f"{channel_info['heart_count']:,}")
            if channel_info.get('video_count'):
                table.add_row("Videos", f"{channel_info['video_count']:,}")
            if channel_info.get('digg_count'):
                table.add_row("Diggs", f"{channel_info['digg_count']:,}")
            if channel_info.get('friend_count'):
                table.add_row("Friends", f"{channel_info['friend_count']:,}")
            
            # Location and dates
            if channel_info.get('location'):
                table.add_row("Location", channel_info['location'])
            if channel_info.get('channel_created'):
                created = channel_info['channel_created']
                if isinstance(created, (int, float)) and created > 0:
                    try:
                        created_date = datetime.fromtimestamp(created)
                        table.add_row("Channel Created", created_date.strftime("%Y-%m-%d %H:%M:%S"))
                    except (ValueError, OSError):
                        table.add_row("Channel Created", str(created))
                elif created:
                    table.add_row("Channel Created", str(created))
            
            # Avatar and description
            if channel_info.get('avatar'):
                table.add_row("Avatar", channel_info['avatar'][:80] + "..." if len(channel_info['avatar']) > 80 else channel_info['avatar'])
            if channel_info.get('avatar_medium'):
                table.add_row("Avatar (Medium)", channel_info['avatar_medium'][:80] + "..." if len(channel_info['avatar_medium']) > 80 else channel_info['avatar_medium'])
            if channel_info.get('avatar_thumb'):
                table.add_row("Avatar (Thumb)", channel_info['avatar_thumb'][:80] + "..." if len(channel_info['avatar_thumb']) > 80 else channel_info['avatar_thumb'])
            if channel_info.get('description'):
                desc = channel_info['description']
                # Truncate long descriptions
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                table.add_row("Description", desc)
            if channel_info.get('verified') is not None:
                verified_icon = "✓" if channel_info['verified'] else "✗"
                table.add_row("Verified", f"{verified_icon} {channel_info['verified']}")
            if channel_info.get('unique_id'):
                table.add_row("Unique ID", channel_info['unique_id'])
            
            console.print(table)
            
            # Show summary
            console.print(f"\n[dim]Channel information extracted successfully[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Channel info extraction error: {e}")
        raise typer.Exit(1)

