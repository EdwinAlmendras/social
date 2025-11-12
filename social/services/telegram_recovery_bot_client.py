"""Telegram Recovery Bot Client using Telethon."""
import asyncio
from pathlib import Path
from typing import Optional, Tuple
from telethon import TelegramClient
from telethon.tl.types import Message

from social.logger import get_logger

logger = get_logger(__name__)


class TelegramRecoveryBotClient:
    """Client to interact with @Kyreth_hq_bot for video recovery."""
    
    BOT_USERNAME = "@Kyreth_hq_bot"
    TIMEOUT_SECONDS = 60
    
    def __init__(self, client: TelegramClient):
        self.client = client
    
    async def recover_video(self, video_url: str, download_path: Optional[Path] = None) -> Tuple[Optional[Path], Optional[str]]:
        """Send URL to bot, download video. Returns (video_path, caption)."""
        try:
            async with self.client.conversation(self.BOT_USERNAME, timeout=self.TIMEOUT_SECONDS) as conv:
                await conv.send_message(video_url)
                
                response1: Message = await conv.get_response()
                response_text = response1.text or ""
                
                if "found" not in response_text.lower():
                    raise ValueError(f"Video not found: {response_text}")
                
                logger.info(f"Bot found video: {response_text}")
                
                response2: Message = await conv.get_response()
                
                if not response2.video and not response2.document:
                    raise ValueError("Bot didn't send video file")
                
                caption = response2.text or response2.message or ""
                
                if download_path is None:
                    download_path = Path.cwd() / "downloads" / "recovery"
                
                download_path.mkdir(parents=True, exist_ok=True)
                
                file_path = await response2.download_media(file=str(download_path))
                
                if file_path is None:
                    raise ValueError("Failed to download video")
                
                video_file = Path(file_path)
                logger.info(f"Recovered: {video_file.name}")
                
                return video_file, caption
                
        except asyncio.TimeoutError:
            raise TimeoutError(f"Bot timeout (>{self.TIMEOUT_SECONDS}s)")
        except Exception as e:
            logger.error(f"Recovery error: {e}", exc_info=True)
            raise
    
    async def check_bot_available(self) -> bool:
        """Check if bot is available."""
        try:
            await self.client.get_entity(self.BOT_USERNAME)
            return True
        except Exception:
            return False

