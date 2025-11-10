"""
Service for extracting channel information from video or channel URLs.
This service delegates to platform-specific implementations.
"""
from typing import Dict, Any, Optional
from social.config import Config
from social.platforms import load_platforms
from social.services.url_id_extractor import URLIDExtractor
from social.logger import get_logger

logger = get_logger(__name__)


class ChannelInfoService:
    """
    Service to extract channel information from video or channel URLs.
    
    This service delegates to platform-specific implementations,
    ensuring each platform handles its own channel info extraction logic.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the channel info service.
        
        Args:
            config: Config instance to load platforms
        """
        self.config = config
        self.platforms = load_platforms(config)
    
    def get_channel_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract channel information from a video or channel URL.
        
        Delegates to the appropriate platform's get_channel_info() method.
        
        Args:
            url: URL of a video or channel
            
        Returns:
            Dictionary with harmonized channel information (snake_case) or None if error
            Keys include:
            - channel: Channel name
            - channel_id: Channel ID
            - channel_url: Channel URL
            - channel_follower_count: Number of followers
            - uploader: Uploader name
            - uploader_id: Uploader ID
            - uploader_url: Uploader URL
            - location: Channel location/country
            - channel_created: Channel creation timestamp
            - avatar: Avatar/profile picture URL
            - description: Channel description
        """
        try:
            # Detect platform from URL
            platform_name = URLIDExtractor.detect_platform(url)
            if not platform_name:
                logger.error(f"Could not detect platform from URL: {url}")
                return None
            
            # Get platform instance
            platform = self.platforms.get(platform_name.lower())
            if not platform:
                logger.warning(f"No platform implementation found for: {platform_name}")
                return None
            
            logger.debug(f"Using platform: {platform_name} to extract channel info")
            
            # Delegate to platform's get_channel_info method
            channel_info = platform.get_channel_info(url)
            
            if channel_info:
                # Add platform name to the result
                channel_info['platform'] = platform_name
                logger.info(f"Successfully extracted channel info for: {channel_info.get('channel', 'Unknown')}")
            else:
                logger.warning(f"Platform {platform_name} returned no channel info")
            
            return channel_info
            
        except Exception as e:
            logger.error(f"Error extracting channel info from {url}: {e}")
            return None

