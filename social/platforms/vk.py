from social.platforms.base import Platform
from typing import Dict, Any
from social.core.caption_builder import CaptionBuilder

class VKPlatform(Platform):
    """Configuración para VK (VKontakte).
    
    yt-dlp detecta automáticamente URLs de VK usando el extractor 'vk'.
    Esta clase solo proporciona configuración específica para VK.
    """
    DEFAULT_CONCURRENT_FRAGMENTS = 10
    
    def __init__(self, name: str = "vk", config: dict = None, global_config=None):
        super().__init__(name, config, global_config)
    
    def create_caption(self, info_dict: Dict[str, Any]) -> CaptionBuilder:
        """
        Creates a CaptionBuilder for VK.
        
        VK uses:
        - title for the title
        - webpage_url for the video URL
        - uploader_id to construct channel URL (negative = club, positive = user)
        - uploader for the channel name
        """
        title = info_dict.get('title') or ''
        video_url = info_dict.get('webpage_url') or ''
        creation_date = self._parse_creation_date(info_dict)
        
        # VK: use uploader for channel name
        channel_name = info_dict.get('uploader') or ''
        
        # VK: construct channel URL from uploader_id or extract from video id
        # If uploader_id is negative, it's a club (group/community)
        # If positive, it's a user ID
        # Format: "-232630765_456239063" -> first part is channel ID
        channel_url = ''
        uploader_id = info_dict.get('uploader_id')
        
        # If uploader_id is not available, try to extract from video id
        if not uploader_id:
            video_id = info_dict.get('id') or info_dict.get('display_id') or ''
            if '_' in str(video_id):
                # Extract first part before underscore
                uploader_id = str(video_id).split('_')[0]
        
        if uploader_id:
            # Remove negative sign if present
            id_str = str(uploader_id).lstrip('-')
            if str(uploader_id).startswith('-'):
                # It's a club
                channel_url = f"https://vk.com/club{id_str}"
            else:
                # It's a user
                channel_url = f"https://vk.com/id{id_str}"
        
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

