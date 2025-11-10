"""Facade service for channel-related operations."""
from typing import Dict, Any, Optional
from telethon import TelegramClient

from social.services.channel_info_service import ChannelInfoService
from social.services.telegram_topic_service import TelegramTopicService
from social.core.caption_builder import ChannelCaptionBuilder
from social.config import Config
from social.logger import get_logger

logger = get_logger(__name__)


class ChannelOperationsService:
    """
    Facade for channel operations.
    
    Coordinates between channel info extraction, topic creation,
    and intro message sending.
    """
    
    def __init__(self, config: Config, telegram_client: TelegramClient):
        """
        Initialize the channel operations service.
        
        Args:
            config: Config instance
            telegram_client: Connected Telegram client
        """
        self.channel_info_service = ChannelInfoService(config)
        self.topic_service = TelegramTopicService(telegram_client)
    
    async def setup_channel_topic(
        self,
        url: str,
        entity_id: int
    ) -> Dict[str, Any]:
        """
        Setup a new channel topic: extract info, create topic, send intro.
        
        Args:
            url: URL to extract channel info from (video or channel URL)
            entity_id: Telegram group ID where to create the topic
            
        Returns:
            Dictionary with:
                - topic_id: Created topic ID
                - channel_info: Extracted channel information
                - platform: Detected platform name
                
        Raises:
            ValueError: If channel info extraction fails
            Exception: If topic creation or intro message fails
        """
        logger.info(f"Setting up channel topic for URL: {url}")
        
        # Step 1: Extract channel info
        logger.debug("Step 1: Extracting channel info")
        channel_info = self.channel_info_service.get_channel_info(url)
        
        if not channel_info:
            error_msg = f"Failed to extract channel info from URL: {url}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        channel_name = channel_info.get('channel', 'Unknown Channel')
        platform = channel_info.get('platform', 'unknown')
        
        logger.info(f"Channel info extracted: {channel_name} ({platform})")
        logger.debug(f"Channel ID: {channel_info.get('channel_id')}")
        
        # Step 2: Create topic
        logger.debug(f"Step 2: Creating topic '{channel_name}'")
        topic_id = await self.topic_service.create_topic(
            entity_id=entity_id,
            topic_name=channel_name
        )
        
        # Step 3: Build channel caption
        logger.debug("Step 3: Building channel caption")
        caption = self._build_channel_caption(channel_info)
        
        # Step 4: Send intro message with avatar
        logger.debug("Step 4: Sending intro message")
        avatar_url = channel_info.get('avatar')
        
        await self.topic_service.send_intro_message(
            entity_id=entity_id,
            topic_id=topic_id,
            caption=caption,
            avatar_url=avatar_url
        )
        
        logger.info(f"Channel topic setup complete. Topic ID: {topic_id}")
        
        return {
            'topic_id': topic_id,
            'channel_info': channel_info,
            'platform': platform
        }
    
    def _build_channel_caption(self, channel_info: Dict[str, Any]) -> str:
        """
        Build a caption for channel intro message.
        
        Args:
            channel_info: Channel information dictionary
            
        Returns:
            Formatted caption string
        """
        caption_builder = ChannelCaptionBuilder(
            channel_name=channel_info.get('channel', 'Unknown'),
            channel_url=channel_info.get('channel_url', ''),
            username=channel_info.get('username'),
            uploader_url=channel_info.get('uploader_url'),
            channel_follower_count=channel_info.get('channel_follower_count'),
            video_count=channel_info.get('video_count'),
            view_count=channel_info.get('view_count'),
            location=channel_info.get('location'),
            channel_created=channel_info.get('channel_created'),
            description=channel_info.get('description'),
            avatar=channel_info.get('avatar')
        )
        
        return caption_builder.build_caption()

