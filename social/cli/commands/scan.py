import asyncio
import typer
from rich.console import Console
from social.config import Config
from social.services.telegram_message_scanner import TelegramMessageScanner
from social.services.social_flow_service import SocialFlowService
from social.services.url_id_extractor import URLIDExtractor
from social.services.video_database import VideoDatabaseService
from social.logger import logger
from telethon import TelegramClient

console = Console()


def scan(
    group_id: int = typer.Argument(..., help="Telegram group ID"),
    limit: int = typer.Option(100, "--limit", "-l", help="Max messages to scan"),
    skip_duplicates: bool = typer.Option(True, "--skip-duplicates/--no-skip-duplicates", help="Skip duplicate videos"),
):
    """Scan Telegram group for video URLs and process them."""
    asyncio.run(_run_scan(group_id, limit, skip_duplicates))


async def _run_scan(group_id: int, limit: int, skip_duplicates: bool):
    config = Config()
    
    is_valid, error_msg = config.validate_telegram_config()
    if not is_valid:
        console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(1)
    
    session_file = config.get_telegram_session_file(None)
    bot_session_file = config.get_bot_session_file(None)
    
    telegram_client = TelegramClient(
        str(session_file),
        config.TELEGRAM_API_ID,
        config.TELEGRAM_API_HASH
    )
    
    bot_client = TelegramClient(
        str(bot_session_file),
        config.TELEGRAM_API_ID,
        config.TELEGRAM_API_HASH
    )
    
    await telegram_client.start()
    await bot_client.start(bot_token=config.BOT_TOKEN)
    
    try:
        scanner = TelegramMessageScanner(telegram_client)
        
        config.load_entities()
        entities = getattr(config, 'ENTITIES', {})
        
        db_services = {}
        if skip_duplicates:
            try:
                console.print("Loading databases for all platforms...")
                for platform_name, platform_config in entities.items():
                    db_group_id = platform_config.get('group_id')
                    db_msg_id = platform_config.get('db_id')
                    
                    if db_group_id and db_msg_id:
                        try:
                            db_service = VideoDatabaseService(
                                client=telegram_client,
                                db_entity_id=db_group_id,
                                db_message_id=db_msg_id
                            )
                            await db_service.load()
                            db_services[platform_name] = db_service
                            console.print(f"  {platform_name}: {len(db_service.video_ids)} IDs")
                        except Exception as e:
                            console.print(f"  Warning: Could not load {platform_name} database: {e}")
            except Exception as e:
                console.print(f"Warning: Could not load databases: {e}")
        
        console.print(f"Scanning group {group_id}...")
        messages = await scanner.scan_group(group_id, limit)
        
        console.print(f"Found {len(messages)} messages with URLs")
        
        processed = 0
        skipped = 0
        failed = 0
        
        for msg in messages:
            for url in msg['urls']:
                video_id = URLIDExtractor.extract_id(url)
                
                if not video_id:
                    console.print(f"Skip: no ID - {url}")
                    continue
                
                platform = URLIDExtractor.detect_platform(url)
                if not platform:
                    console.print(f"Skip: unknown platform - {url}")
                    continue
                
                platform_config = entities.get(platform.lower(), {})
                entity_id = platform_config.get('group_id')
                topic_id = platform_config.get('topic_id')
                
                if not entity_id:
                    console.print(f"Skip: no config for {platform} - {video_id}")
                    continue
                
                # Get db_service for this platform
                db_service = db_services.get(platform.lower())
                
                # Create SocialFlowService with db_service for duplicate checking
                social_flow = SocialFlowService(
                    config, 
                    telegram_client=telegram_client,
                    db_service=db_service
                )
                
                console.print(f"Processing: {url}")
                try:
                    result = await social_flow.process_video(
                        url,
                        telegram_client=telegram_client,
                        bot_client=bot_client,
                        entity_id=entity_id,
                        topic_id=topic_id
                    )
                    if result.get('success'):
                        processed += 1
                        console.print(f"OK: {video_id}")
                        if db_service:
                            db_service.add_id(video_id)
                    elif result.get('duplicate'):
                        skipped += 1
                        console.print(f"Skip: duplicate - {video_id}")
                    else:
                        failed += 1
                        console.print(f"FAIL: {video_id}")
                except Exception as e:
                    failed += 1
                    console.print(f"ERROR: {e}")
        
        for platform, db_service in db_services.items():
            if processed > 0:
                console.print(f"Saving {platform} database...")
                await db_service.save(new_ids_count=processed)
        
        console.print(f"\nDone: {processed} processed, {skipped} skipped, {failed} failed")
        
    finally:
        await telegram_client.disconnect()
        await bot_client.disconnect()

