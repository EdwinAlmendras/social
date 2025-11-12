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
    
    telegram_client = TelegramClient(
        str(config.session_file),
        config.api_id,
        config.api_hash
    )
    
    await telegram_client.start()
    
    try:
        scanner = TelegramMessageScanner(telegram_client)
        social_flow = SocialFlowService(config, telegram_client=telegram_client)
        
        db_service = None
        if skip_duplicates:
            try:
                config.load_entities()
                entities = getattr(config, 'ENTITIES', {})
                
                first_url = None
                messages = await scanner.scan_group(group_id, limit=10)
                for msg in messages:
                    if msg['urls']:
                        first_url = msg['urls'][0]
                        break
                
                if first_url:
                    platform = URLIDExtractor.detect_platform(first_url)
                    if platform:
                        platform_config = entities.get(platform.lower())
                        if platform_config:
                            db_group_id = platform_config.get('group_id')
                            db_msg_id = platform_config.get('db_id')
                            
                            if db_group_id and db_msg_id:
                                db_service = VideoDatabaseService(
                                    client=telegram_client,
                                    db_entity_id=db_group_id,
                                    db_message_id=db_msg_id
                                )
                                console.print("Loading database...")
                                await db_service.load()
                                console.print(f"Loaded {len(db_service.video_ids)} IDs")
            except Exception as e:
                console.print(f"Warning: Could not load database: {e}")
                db_service = None
        
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
                
                if db_service and db_service.is_duplicate(url):
                    console.print(f"Skip: duplicate - {video_id}")
                    skipped += 1
                    continue
                
                console.print(f"Processing: {url}")
                try:
                    result = await social_flow.process_video(url)
                    if result.get('success'):
                        processed += 1
                        console.print(f"OK: {video_id}")
                        if db_service:
                            db_service.add_id(video_id)
                    else:
                        failed += 1
                        console.print(f"FAIL: {video_id}")
                except Exception as e:
                    failed += 1
                    console.print(f"ERROR: {e}")
        
        if db_service and processed > 0:
            console.print("Saving database...")
            await db_service.save(new_ids_count=processed)
        
        console.print(f"\nDone: {processed} processed, {skipped} skipped, {failed} failed")
        
    finally:
        await telegram_client.disconnect()

