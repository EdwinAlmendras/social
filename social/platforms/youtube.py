from social.platforms.base import Platform
from typing import Dict, Any, Optional
from social.core.caption_builder import CaptionBuilder
from yt_dlp import YoutubeDL
from social.logger import get_logger
from social.services.url_id_extractor import URLIDExtractor
import requests

logger = get_logger(__name__)

class YouTubePlatform(Platform):
    """Configuración para YouTube.
    
    yt-dlp detecta automáticamente URLs de YouTube usando el extractor 'youtube'.
    Esta clase solo proporciona configuración específica para YouTube.
    """
    
    # Formato con fallback: intenta el mejor primero, si falla con cookies usa 'best'
    DEFAULT_FORMAT = "bestvideo+bestaudio[acodec^=mp4a]/bestvideo*+bestaudio/best"
    
    def __init__(self, name: str = "youtube", config: dict = None, global_config=None):
        # Sobrescribir formato por defecto para YouTube
        if config is None:
            config = {}
        if 'format' not in config:
            config['format'] = self.DEFAULT_FORMAT
        
        super().__init__(name, config, global_config)
    
    def get_ydl_opts(self):
        """Obtiene opciones específicas de YouTube para yt-dlp."""
        opts = super().get_ydl_opts()
        return opts
    
    def _is_short(self, info_dict: Dict[str, Any]) -> bool:
        """
        Check if the video is a YouTube Short.
        
        Args:
            info_dict: Info dictionary from yt-dlp
            
        Returns:
            True if the video is a Short, False otherwise
        """
        # Check URL for /shorts/ pattern
        original_url = info_dict.get('original_url', '')
        
        if '/shorts/' in original_url:
            return True
        
        return False
    
    def create_caption(self, info_dict: Dict[str, Any]) -> CaptionBuilder:
        """
        Creates a CaptionBuilder for YouTube.
        
        YouTube uses:
        - fulltitle for the title
        - webpage_url for regular videos, original_url for shorts
        - uploader_url for the channel URL
        - channel or uploader for the channel name
        """
        # YouTube: use fulltitle instead of title
        title = info_dict.get('fulltitle') or info_dict.get('title') or ''
        
        # YouTube: use original_url for shorts, webpage_url for regular videos
        is_short = self._is_short(info_dict)
        if is_short:
            video_url = info_dict.get('original_url') or info_dict.get('webpage_url') or ''
        else:
            video_url = info_dict.get('webpage_url') or ''
        
        creation_date = self._parse_creation_date(info_dict)
        
        # YouTube: use uploader_url for channel_url
        channel_name = info_dict.get('channel') or info_dict.get('uploader') or ''
        channel_url = info_dict.get('uploader_url') or ''
        
        # Statistics
        views = info_dict.get('view_count')
        likes = info_dict.get('like_count')
        
        return CaptionBuilder(
            title=title,
            video_url=video_url,
            creation_date=creation_date,
            channel_name=channel_name,
            channel_url=channel_url,
            likes=likes,
            views=views
        )
    
    def get_channel_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract channel information from YouTube video or channel URL using YouTube Data API v3.
        
        Args:
            url: URL of a YouTube video or channel
            
        Returns:
            Dictionary with harmonized channel information (snake_case)
        """
        try:
            # Check if API key is available
            if not self.global_config.YOUTUBE_API_KEY:
                logger.error("YOUTUBE_API_KEY not set in .env, cannot extract channel info")
                return None
            
            # Step 1: Get channel ID from URL
            channel_id = self._get_channel_id_from_url(url)
            
            if not channel_id:
                logger.error(f"Could not extract channel ID from URL: {url}")
                return None
            
            logger.debug(f"Getting channel info for channel ID: {channel_id}")
            
            # Step 2: Make direct API call to get full channel info including thumbnails
            api_url = "https://www.googleapis.com/youtube/v3/channels"
            params = {
                'part': 'snippet,statistics,contentDetails,brandingSettings',
                'id': channel_id,
                'key': self.global_config.YOUTUBE_API_KEY
            }
            
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('items'):
                logger.warning(f"No channel data returned for channel ID: {channel_id}")
                return None
            
            # Extract channel info from first item
            channel = data['items'][0]
            snippet = channel.get('snippet', {})
            statistics = channel.get('statistics', {})
            content_details = channel.get('contentDetails', {})
            branding = channel.get('brandingSettings', {}).get('channel', {})
            
            # Get thumbnails (avatar)
            thumbnails = snippet.get('thumbnails', {})
            avatar_url = (
                thumbnails.get('high', {}).get('url') or
                thumbnails.get('medium', {}).get('url') or
                thumbnails.get('default', {}).get('url')
            )
            
            # Get username (customUrl or handle)
            username = snippet.get('customUrl', '')
            
            # Parse creation date (ISO 8601 to Unix timestamp)
            published_at = snippet.get('publishedAt', '')
            channel_created = 0
            if published_at:
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    channel_created = int(dt.timestamp())
                except Exception as e:
                    logger.debug(f"Error parsing publishedAt date: {e}")
            
            # Step 3: Harmonize to snake_case format (matching base Platform format)
            result = {
                'channel': snippet.get('title', ''),
                'channel_id': channel_id,
                'channel_url': f"https://www.youtube.com/channel/{channel_id}",
                'channel_follower_count': int(statistics.get('subscriberCount', 0)),
                'uploader': snippet.get('title', ''),
                'uploader_id': channel_id,
                'uploader_url': f"https://www.youtube.com/{username}",
                'location': snippet.get('country', ''),
                'channel_created': channel_created,
                'avatar': avatar_url,
                'description': snippet.get('description', ''),
            }
            
            # Add YouTube-specific fields
            result['username'] = username  # @username
            result['view_count'] = int(statistics.get('viewCount', 0))
            result['video_count'] = int(statistics.get('videoCount', 0))
            result['playlist_id_uploads'] = content_details.get('relatedPlaylists', {}).get('uploads', '')
            result['playlist_id_likes'] = content_details.get('relatedPlaylists', {}).get('likes', '')
            result['keywords'] = branding.get('keywords', '')
            result['avatar_high'] = thumbnails.get('high', {}).get('url', '')
            result['avatar_medium'] = thumbnails.get('medium', {}).get('url', '')
            result['avatar_default'] = thumbnails.get('default', {}).get('url', '')
            
            print(result)
            logger.info(f"Successfully extracted channel info for: {result.get('channel', 'Unknown')} (@{username})")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making YouTube API request: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error extracting YouTube channel info from {url}: {e}", exc_info=True)
            return None
    
    def _get_channel_id_from_url(self, url: str) -> Optional[str]:
        """
        Get channel ID from a video or channel URL.
        
        Uses URLIDExtractor for video URLs and yt-dlp for channel URLs.
        
        Args:
            url: YouTube video or channel URL
            
        Returns:
            Channel ID or None if not found
        """
        # Try to extract video ID using URLIDExtractor (no HTTP request)
        video_id = URLIDExtractor.extract_id(url)
        
        if video_id:
            # It's a video URL, need to get channel ID from video
            logger.debug(f"Extracted video ID: {video_id}, getting channel ID from video...")
            
            try:
                # Use YouTube API to get channel ID from video ID
                api_url = "https://www.googleapis.com/youtube/v3/videos"
                params = {
                    'part': 'snippet',
                    'id': video_id,
                    'key': self.global_config.YOUTUBE_API_KEY
                }
                
                response = requests.get(api_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if data.get('items'):
                    channel_id = data['items'][0].get('snippet', {}).get('channelId')
                    if channel_id:
                        logger.debug(f"Got channel ID from video: {channel_id}")
                        return channel_id
                
            except Exception as e:
                logger.error(f"Error getting channel ID from video API: {e}")
                return None
        
        # It's not a video URL, try to extract channel ID from channel URL
        logger.debug(f"Not a video URL, attempting to extract channel ID from channel URL: {url}")
        
        try:
            # Use yt-dlp to resolve channel ID from @username or /c/ URLs
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'skip_download': True,
            }
            
            if self.cookies.exists():
                ydl_opts['cookiefile'] = str(self.cookies)
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                channel_id = info.get('channel_id') or info.get('uploader_id') or info.get('id')
                
                if channel_id:
                    logger.debug(f"Resolved channel ID via yt-dlp: {channel_id}")
                    return channel_id
                else:
                    logger.warning(f"Could not resolve channel ID from: {url}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error resolving channel ID from {url}: {e}")
            return None

