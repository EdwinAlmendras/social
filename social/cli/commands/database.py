"""Database command for CLI."""
import typer
import asyncio
from rich.console import Console
from pathlib import Path

from social.config import Config
from social.services.video_database import VideoDatabaseService
from social.logger import logger

app = typer.Typer()
console = Console()


@app.command("sync")
def sync(
    platform: str = typer.Argument(..., help="Platform to sync (youtube, vk, tiktok)"),
    session: str = typer.Option("uploader.session", "--session", "-s", help="Telegram session file"),
):
    """
    Sync video database by scanning messages for new video IDs.
    
    Example:
        social database sync youtube
    """
    asyncio.run(_sync(platform, session))


async def _sync(platform: str, session_file: str):
    """Run database sync asynchronously."""
    from telethon import TelegramClient
    import os
    
    try:
        # Load config
        config = Config()
        config.load_entities()
        
        # Get platform configuration
        entities = getattr(config, 'ENTITIES', {})
        platform_config = entities.get(platform.lower())
        
        if not platform_config:
            console.print(f"[red]Error:[/red] Platform '{platform}' not configured")
            raise typer.Exit(1)
        
        group_id = platform_config.get('group_id')
        db_id = platform_config.get('db_id')
        
        if not group_id or not db_id:
            console.print(f"[red]Error:[/red] Platform configuration missing group_id or db_id")
            raise typer.Exit(1)
        
        console.print(f"[cyan]Syncing database for platform: {platform}[/cyan]")
        console.print(f"  Group ID: {group_id}")
        console.print(f"  DB Message ID: {db_id}")
        
        # Get Telegram credentials
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not api_id or not api_hash:
            console.print("[red]Error:[/red] TELEGRAM_API_ID and TELEGRAM_API_HASH must be set")
            raise typer.Exit(1)
        
        # Connect to Telegram
        console.print("\n[cyan]🔌 Connecting to Telegram...[/cyan]")
        client = TelegramClient(session_file, int(api_id), api_hash)
        
        try:
            await client.start()
            console.print("[green]✓ Connected[/green]")
            
            # Initialize database service
            # db_id is the message ID of the database message
            db_service = VideoDatabaseService(
                client=client,
                db_entity_id=group_id,
                db_message_id=db_id
            )
            
            # Load existing database
            console.print("\n[cyan]📖 Loading existing database...[/cyan]")
            loaded = await db_service.load()
            
            if loaded:
                console.print(f"[green]✓ Database loaded[/green]")
                console.print(f"  Existing IDs: {len(db_service.video_ids)}")
                console.print(f"  Last processed message ID: {db_service.last_processed_msg_id}")
            else:
                console.print("[yellow]⚠ No existing database found, starting fresh[/yellow]")
            
            # Sync from content topic
            console.print("\n[cyan]🔄 Syncing new video IDs...[/cyan]")
            
            # Get content topics (videos and shorts)
            topics = platform_config.get('topics', {})
            videos_topic = topics.get('videos')
            shorts_topic = topics.get('shorts')
            
            new_ids_total = 0
            
            # Sync from videos topic
            if videos_topic:
                console.print(f"  Scanning videos topic ({videos_topic})...")
                new_ids = await db_service.sync(group_id, videos_topic)
                new_ids_total += new_ids
                console.print(f"  Found {new_ids} new IDs in videos")
            
            # Sync from shorts topic
            if shorts_topic and shorts_topic != videos_topic:
                console.print(f"  Scanning shorts topic ({shorts_topic})...")
                new_ids = await db_service.sync(group_id, shorts_topic)
                new_ids_total += new_ids
                console.print(f"  Found {new_ids} new IDs in shorts")
            
            console.print(f"\n[green]✓ Sync complete: {new_ids_total} new IDs[/green]")
            console.print(f"  Total IDs in database: {len(db_service.video_ids)}")
            
            # Save database
            if new_ids_total > 0:
                console.print("\n[cyan]💾 Saving database...[/cyan]")
                saved = await db_service.save(new_ids_total)
                
                if saved:
                    console.print("[green]✓ Database saved successfully[/green]")
                else:
                    console.print("[red]✗ Failed to save database[/red]")
                    raise typer.Exit(1)
            else:
                console.print("\n[yellow]No changes to save[/yellow]")
        
        finally:
            await client.disconnect()
    
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {str(e)}")
        logger.error(f"Database sync error: {e}", exc_info=True)
        raise typer.Exit(1)


@app.command("check")
def check(
    url: str = typer.Argument(..., help="URL to check for duplicates"),
    platform: str = typer.Option(None, "--platform", "-p", help="Platform name (auto-detected if not provided)"),
    session: str = typer.Option("uploader.session", "--session", "-s", help="Telegram session file"),
):
    """
    Check if a URL has already been processed.
    
    Example:
        social database check "https://youtube.com/watch?v=VIDEO_ID"
    """
    asyncio.run(_check(url, platform, session))


async def _check(url: str, platform: str, session_file: str):
    """Check if URL is duplicate asynchronously."""
    from telethon import TelegramClient
    from social.services.url_id_extractor import URLIDExtractor
    import os
    
    try:
        # Extract ID from URL
        video_id = URLIDExtractor.extract_id(url)
        
        if not video_id:
            console.print(f"[red]Error:[/red] Could not extract video ID from URL")
            raise typer.Exit(1)
        
        # Detect platform if not provided
        if not platform:
            platform = URLIDExtractor.detect_platform(url)
            if not platform:
                console.print(f"[red]Error:[/red] Could not detect platform from URL")
                raise typer.Exit(1)
            console.print(f"[cyan]Detected platform: {platform}[/cyan]")
        
        console.print(f"[cyan]Checking URL:[/cyan] {url}")
        console.print(f"[cyan]Video ID:[/cyan] {video_id}")
        
        # Load config
        config = Config()
        config.load_entities()
        
        # Get platform configuration
        entities = getattr(config, 'ENTITIES', {})
        platform_config = entities.get(platform.lower())
        
        if not platform_config:
            console.print(f"[red]Error:[/red] Platform '{platform}' not configured")
            raise typer.Exit(1)
        
        group_id = platform_config.get('group_id')
        db_id = platform_config.get('db_id')
        
        # Get Telegram credentials
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not api_id or not api_hash:
            console.print("[red]Error:[/red] TELEGRAM_API_ID and TELEGRAM_API_HASH must be set")
            raise typer.Exit(1)
        
        # Connect to Telegram
        console.print("\n[cyan]🔌 Connecting to Telegram...[/cyan]")
        client = TelegramClient(session_file, int(api_id), api_hash)
        
        try:
            await client.start()
            
            # Initialize and load database
            db_service = VideoDatabaseService(
                client=client,
                db_entity_id=group_id,
                db_message_id=db_id
            )
            
            console.print("[cyan]📖 Loading database...[/cyan]")
            await db_service.load()
            console.print(f"  Loaded {len(db_service.video_ids)} video IDs")
            
            # Check if duplicate
            is_duplicate = db_service.is_duplicate(url)
            
            console.print()
            if is_duplicate:
                console.print(f"[red]✗ DUPLICATE[/red] - Video ID '{video_id}' already exists in database")
                raise typer.Exit(1)
            else:
                console.print(f"[green]✓ NOT A DUPLICATE[/green] - Video ID '{video_id}' is new")
        
        finally:
            await client.disconnect()
    
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {str(e)}")
        logger.error(f"Database check error: {e}", exc_info=True)
        raise typer.Exit(1)

