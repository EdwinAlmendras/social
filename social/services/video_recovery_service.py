"""Video Recovery Service."""
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from telethon import TelegramClient

from social.logger import get_logger
from social.config import Config
from social.services.telegram_recovery_bot_client import TelegramRecoveryBotClient
from social.services.recovery_metadata_parser import RecoveryMetadataParser
from social.core.caption_builder import VideoCaptionBuilder

logger = get_logger(__name__)


class VideoRecoveryService:
    """Recover deleted/unavailable videos using @Kyreth_hq_bot."""
    
    def __init__(self, config: Config, telegram_client: TelegramClient):
        self.config = config
        self.bot_client = TelegramRecoveryBotClient(telegram_client)
        self.parser = RecoveryMetadataParser()
    
    async def recover_video(self, video_url: str, download_dir: Optional[Path] = None, error_message: Optional[str] = None) -> Dict[str, Any]:
        """Recover video and rebuild caption."""
        logger.info(f"Recovering: {video_url}")
        
        try:
            if not await self.bot_client.check_bot_available():
                raise ValueError("Bot not available")
            
            if download_dir is None:
                download_dir = self.config.DOWNLOADS_DIR / "recovery"
            
            video_file, raw_caption = await self.bot_client.recover_video(video_url, download_dir)
            
            if not video_file or not video_file.exists():
                raise ValueError("Download failed")
            
            try:
                metadata = self.parser.parse(raw_caption)
                caption = self._rebuild_caption(metadata)
            except Exception as e:
                logger.warning(f"Parse/rebuild failed: {e}, using raw caption")
                caption = raw_caption
                metadata = {}
            
            logger.info(f"Recovery completed: {video_file.name}")
            
            return {
                'success': True,
                'video_path': video_file,
                'caption': caption,
                'metadata': metadata,
                'message': f"Recovered: {video_file.name}"
            }
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}", exc_info=True)
            return {
                'success': False,
                'video_path': None,
                'caption': None,
                'error': str(e)
            }
    
    def _parse_deletion_reason(self, error_message: Optional[str]) -> str:
        """Parse yt-dlp error to short deletion reason."""
        if not error_message:
            return "Video deleted"
        
        error_lower = error_message.lower()
        
        # Error mappings
        if "community guidelines" in error_lower or "violating youtube" in error_lower:
            return "Deleted by YT Community Guidelines violation"
        elif "copyright" in error_lower:
            return "Deleted by copyright claim"
        elif "private" in error_lower:
            return "Video set to private"
        elif "unavailable" in error_lower:
            return "Video unavailable"
        elif "removed" in error_lower:
            return "Video removed by uploader"
        else:
            return "Video deleted"
    
    def _rebuild_caption(self, metadata: Dict[str, Any], error_message: Optional[str] = None) -> str:
        """Rebuild caption using VideoCaptionBuilder."""
        upload_date = metadata.get('upload_date')
        if upload_date:
            upload_date = upload_date.replace(hour=12, minute=0, second=0)
        else:
            upload_date = datetime.now().replace(hour=12, minute=0, second=0)
        
        caption_builder = VideoCaptionBuilder(
            title=metadata.get('title', 'Recovered Video'),
            video_url=metadata.get('video_url', ''),
            creation_date=upload_date,
            channel_name=metadata.get('channel_name', 'Unknown'),
            channel_url=metadata.get('channel_url', ''),
            likes=None,
            views=None
        )
        caption = caption_builder.build_caption()
        
        # Add deletion reason
        deletion_reason = self._parse_deletion_reason(error_message)
        caption += f"\n\n⚠️ {deletion_reason}"
        
        return caption
    
    async def recover_videos_batch(self, video_urls: list[str], download_dir: Optional[Path] = None) -> list[Dict[str, Any]]:
        """Recover multiple videos sequentially."""
        logger.info(f"Batch recovery: {len(video_urls)} videos")
        import asyncio
        results = []
        for i, url in enumerate(video_urls, 1):
            result = await self.recover_video(url, download_dir)
            results.append(result)
            if i < len(video_urls):
                await asyncio.sleep(2)
        
        success = sum(1 for r in results if r['success'])
        logger.info(f"Batch done: {success}/{len(video_urls)} successful")
        return results

