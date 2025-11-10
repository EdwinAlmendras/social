"""URL ID Extractor - Extract video IDs from URLs without processing them.

This module extracts video IDs from various platform URLs using yt-dlp's extractors,
avoiding the need to make HTTP requests.
"""
from typing import Optional
from yt_dlp.extractor import gen_extractor_classes

from social.logger import get_logger

logger = get_logger(__name__)


class URLIDExtractor:
    """Extract video IDs from platform URLs using yt-dlp extractors."""
    
    @staticmethod
    def extract_id(url: str) -> Optional[str]:
        """
        Extract video ID from any supported platform URL using yt-dlp extractors.
        
        This method uses yt-dlp's URL matching without making any HTTP requests,
        making it very fast and efficient.
        
        Args:
            url: Video URL from any platform
            
        Returns:
            Video ID or None if platform not supported or ID not found
            
        Examples:
            https://www.youtube.com/watch?v=dQw4w9WgXcQ -> dQw4w9WgXcQ
            https://vk.com/video-123456_789012 -> -123456_789012
            https://www.tiktok.com/@user/video/1234567890 -> 1234567890
        """
        try:
            # Iterate through all yt-dlp extractors
            for ie_class in gen_extractor_classes():
                # Check if this extractor can handle the URL
                if ie_class.suitable(url):
                    try:
                        # Use _match_valid_url to extract ID without HTTP request
                        match = ie_class._match_valid_url(url)
                        if match:
                            groupdict = match.groupdict()
                            
                            # Try common ID group names
                            for id_key in ['id', 'videoid', 'video_id', 'v']:
                                if id_key in groupdict and groupdict[id_key] is not None:
                                    video_id = groupdict[id_key]
                                    logger.debug(f"Extracted ID '{video_id}' using {ie_class.IE_NAME} (key: {id_key})")
                                    return video_id
                            
                            # Fallback: get first non-None group
                            groups = match.groups()
                            for group in groups:
                                if group is not None:
                                    video_id = group
                                    logger.debug(f"Extracted ID '{video_id}' from first non-None group using {ie_class.IE_NAME}")
                                    return video_id
                    except Exception as e:
                        logger.debug(f"Could not extract ID using {ie_class.IE_NAME}: {e}")
                        continue
            
            logger.warning(f"Could not extract ID from URL: {url}")
            return None
        
        except Exception as e:
            logger.error(f"Error extracting ID from URL {url}: {e}")
            return None
    
    @staticmethod
    def detect_platform(url: str) -> Optional[str]:
        """
        Detect platform from URL using yt-dlp extractors.
        
        Args:
            url: Video URL
            
        Returns:
            Platform name (extractor IE_NAME) or None
        """
        try:
            for ie_class in gen_extractor_classes():
                if ie_class.suitable(url):
                    platform_name = ie_class.IE_NAME.lower()
                    logger.debug(f"Detected platform: {platform_name}")
                    return platform_name
            
            return None
        except Exception as e:
            logger.error(f"Error detecting platform from URL {url}: {e}")
            return None

