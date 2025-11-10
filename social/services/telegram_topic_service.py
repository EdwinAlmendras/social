"""Service for managing Telegram topics/forums."""
from typing import Optional
from pathlib import Path
import tempfile
import httpx

from telethon import TelegramClient
from telethon.tl.functions.messages import CreateForumTopicRequest
from telethon.tl.types import InputMediaUploadedPhoto

from social.logger import get_logger

logger = get_logger(__name__)


class TelegramTopicService:
    """Service for creating and managing Telegram forum topics."""
    
    def __init__(self, client: TelegramClient):
        """
        Initialize the Telegram topic service.
        
        Args:
            client: Connected Telegram client
        """
        self.client = client
    
    async def create_topic(self, entity_id: int, topic_name: str) -> int:
        """
        Create a new forum topic in a Telegram group.
        
        Args:
            entity_id: Telegram group/channel ID
            topic_name: Name for the new topic
            
        Returns:
            Topic ID (message ID of the topic)
            
        Raises:
            Exception: If topic creation fails
        """
        try:
            logger.info(f"Creating topic '{topic_name}' in entity {entity_id}")
            
            result = await self.client(CreateForumTopicRequest(
                peer=entity_id,
                title=topic_name,
            ))
            
            topic_id = result.updates[0].id
            logger.info(f"Topic created successfully with ID: {topic_id}")
            
            return topic_id
            
        except Exception as e:
            logger.error(f"Failed to create topic '{topic_name}': {e}")
            raise
    
    async def send_intro_message(
        self,
        entity_id: int,
        topic_id: int,
        caption: str,
        avatar_url: Optional[str] = None
    ) -> None:
        """
        Send introduction message to a topic with optional avatar photo.
        
        Args:
            entity_id: Telegram group/channel ID
            topic_id: Topic ID to send message to
            caption: Message caption/text
            avatar_url: Optional URL to channel avatar image
            
        Raises:
            Exception: If sending message fails
        """
        try:
            if avatar_url:
                logger.debug(f"Downloading avatar from: {avatar_url}")
                avatar_data = await self._download_avatar(avatar_url)
                
                if avatar_data:
                    logger.info("Sending intro message with avatar photo")
                    await self.client.send_file(
                        entity_id,
                        avatar_data,
                        caption=caption,
                        reply_to=topic_id
                    )
                    logger.info("Intro message sent successfully")
                else:
                    logger.warning("Avatar download failed, sending text only")
                    await self._send_text_only(entity_id, topic_id, caption)
            else:
                logger.info("No avatar URL provided, sending text only")
                await self._send_text_only(entity_id, topic_id, caption)
                
        except Exception as e:
            logger.error(f"Failed to send intro message: {e}")
            raise
    
    async def _send_text_only(self, entity_id: int, topic_id: int, text: str) -> None:
        """Send text-only message to topic."""
        await self.client.send_message(
            entity_id,
            text,
            reply_to=topic_id
        )
        logger.info("Text-only intro message sent successfully")
    
    async def _download_avatar(self, url: str) -> Optional[Path]:
        """
        Download avatar image from URL to temporary file.
        
        Args:
            url: URL of the avatar image
            
        Returns:
            Path to temporary file or None if download fails
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Save to temporary file
                suffix = Path(url).suffix or '.jpg'
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_file.write(response.content)
                temp_file.close()
                
                logger.debug(f"Avatar downloaded to: {temp_file.name}")
                return Path(temp_file.name)
                
        except Exception as e:
            logger.error(f"Failed to download avatar from {url}: {e}")
            return None

