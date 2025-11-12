"""Database command for CLI."""
import typer
import asyncio
from typing import Optional
from rich.console import Console
from pathlib import Path

from social.config import Config
from social.services.video_database import VideoDatabaseService
from social.logger import logger

app = typer.Typer()
console = Console()


@app.command("sync")
def sync(
    platform: str = typer.Argument(None, help="Platform to sync (youtube, vk, tiktok, rutube) or use --all"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Telegram session file"),
    all_platforms: bool = typer.Option(False, "--all", help="Sync all configured platforms"),
):
    """
    Sync video database by scanning messages for new video IDs.
    
    Example:
        social database sync youtube
        social database sync --all
    """
    if not all_platforms and not platform:
        console.print("[red]Error:[/red] Either specify a platform or use --all")
        raise typer.Exit(1)
    
    asyncio.run(_sync(platform, session, all_platforms))


async def _sync(platform: Optional[str], session_file: Optional[str], all_platforms: bool):
    """Run database sync asynchronously."""
    from telethon import TelegramClient
    
    try:
        # Load config
        config = Config()
        config.load_entities()
        
        # Validate Telegram config
        is_valid, error_msg = config.validate_telegram_config()
        if not is_valid:
            console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)
        
        # Get session file from config
        session_path = config.get_telegram_session_file(session_file)
        
        # Connect to Telegram
        console.print("\n[cyan]Connecting to Telegram...[/cyan]")
        client = TelegramClient(str(session_path), config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
        
        try:
            await client.start()
            console.print("[green]Connected[/green]")
            
            entities = getattr(config, 'ENTITIES', {})
            
            # Get platforms to sync
            if all_platforms:
                platforms_to_sync = list(entities.keys())
                console.print(f"[cyan]Syncing all platforms: {', '.join(platforms_to_sync)}[/cyan]")
            else:
                platforms_to_sync = [platform.lower()]
            
            total_new_ids = 0
            
            for platform_name in platforms_to_sync:
                platform_config = entities.get(platform_name)
                
                if not platform_config:
                    console.print(f"[yellow]Warning: Platform '{platform_name}' not configured, skipping[/yellow]")
                    continue
                
                group_id = platform_config.get('group_id')
                db_id = platform_config.get('db_id')
                
                if not group_id or not db_id:
                    console.print(f"[yellow]Warning: Platform '{platform_name}' missing group_id or db_id, skipping[/yellow]")
                    continue
                
                console.print(f"\n[cyan]Syncing database for platform: {platform_name}[/cyan]")
                console.print(f"  Group ID: {group_id}")
                console.print(f"  DB Message ID: {db_id}")
                
                # Initialize database service
                db_service = VideoDatabaseService(
                    client=client,
                    db_entity_id=group_id,
                    db_message_id=db_id
                )
                
                # Load existing database
                console.print("  [cyan]Loading existing database...[/cyan]")
                loaded = await db_service.load()
                
                if loaded:
                    console.print(f"  [green]Database loaded: {len(db_service.video_ids)} IDs[/green]")
                else:
                    console.print("  [yellow]No existing database found, starting fresh[/yellow]")
                
                # Sync from all messages in group (no topic filter)
                console.print("  [cyan]Syncing new video IDs from all messages...[/cyan]")
                
                new_ids_total = await db_service.sync(group_id, content_topic_id=None)
                
                console.print(f"  [green]Sync complete: {new_ids_total} new IDs[/green]")
                console.print(f"  Total IDs in database: {len(db_service.video_ids)}")
                
                # Save database
                if new_ids_total > 0:
                    console.print("  [cyan]Saving database...[/cyan]")
                    saved = await db_service.save(new_ids_total)
                    
                    if saved:
                        console.print("  [green]Database saved successfully[/green]")
                    else:
                        console.print("  [red]Failed to save database[/red]")
                
                total_new_ids += new_ids_total
            
            console.print(f"\n[green]All syncs complete: {total_new_ids} total new IDs[/green]")
        
        finally:
            await client.disconnect()
    
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {str(e)}")
        logger.error(f"Database sync error: {e}", exc_info=True)
        raise typer.Exit(1)


@app.command("check")
def check(
    url: str = typer.Argument(..., help="URL to check for duplicates"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Platform name (auto-detected if not provided)"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Telegram session file"),
):
    """
    Check if a URL has already been processed.
    
    Example:
        social database check "https://youtube.com/watch?v=VIDEO_ID"
    """
    asyncio.run(_check(url, platform, session))


async def _check(url: str, platform: Optional[str], session_file: Optional[str]):
    """Check if URL is duplicate asynchronously."""
    from telethon import TelegramClient
    from social.services.url_id_extractor import URLIDExtractor
    
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
        
        # Validate Telegram config
        is_valid, error_msg = config.validate_telegram_config()
        if not is_valid:
            console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)
        
        # Get platform configuration
        entities = getattr(config, 'ENTITIES', {})
        platform_config = entities.get(platform.lower())
        
        if not platform_config:
            console.print(f"[red]Error:[/red] Platform '{platform}' not configured")
            raise typer.Exit(1)
        
        group_id = platform_config.get('group_id')
        db_id = platform_config.get('db_id')
        
        # Get session file from config
        session_path = config.get_telegram_session_file(session_file)
        
        # Connect to Telegram
        console.print("\n[cyan]Connecting to Telegram...[/cyan]")
        client = TelegramClient(str(session_path), config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
        
        try:
            await client.start()
            
            # Initialize and load database
            db_service = VideoDatabaseService(
                client=client,
                db_entity_id=group_id,
                db_message_id=db_id
            )
            
            console.print("[cyan]Loading database...[/cyan]")
            await db_service.load()
            console.print(f"  Loaded {len(db_service.video_ids)} video IDs")
            
            # Check if duplicate
            is_duplicate = db_service.is_duplicate(url)
            
            console.print()
            if is_duplicate:
                console.print(f"[red]DUPLICATE[/red] - Video ID '{video_id}' already exists in database")
                raise typer.Exit(1)
            else:
                console.print(f"[green]NOT A DUPLICATE[/green] - Video ID '{video_id}' is new")
        
        finally:
            await client.disconnect()
    
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {str(e)}")
        logger.error(f"Database check error: {e}", exc_info=True)
        raise typer.Exit(1)

