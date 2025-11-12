from social.platforms.base import Platform
from social.core.caption_builder import CaptionBuilder

class RutubePlatform(Platform):
    """Configuración para Rutube.
    
    yt-dlp detecta automáticamente URLs de Rutube usando el extractor 'rutube'.
    Soporta descarga paralela de fragmentos para mejor velocidad.
    """
    
    DEFAULT_CONCURRENT_FRAGMENTS = 20
    
    def __init__(self, name: str = "rutube", config: dict = None, global_config=None):
        super().__init__(name, config, global_config)
        
        # Configurar descarga paralela de fragmentos
        concurrent = config.get("concurrent_fragment_downloads", self.DEFAULT_CONCURRENT_FRAGMENTS) if config else self.DEFAULT_CONCURRENT_FRAGMENTS
        
        if not self.extra_opts:
            self.extra_opts = {}
        
        self.extra_opts['concurrent_fragment_downloads'] = concurrent
    
    def create_caption(self, info_dict):
        """Create caption for Rutube videos, constructing channel URL from uploader_id."""
        title = info_dict.get('title') or ''
        video_url = info_dict.get('webpage_url') or ''
        
        creation_date = self._parse_creation_date(info_dict)
        
        channel_name = info_dict.get('channel') or info_dict.get('uploader') or ''
        channel_url = info_dict.get('channel_url') or info_dict.get('uploader_url')
        
        # Construir URL del canal si no existe usando uploader_id
        if not channel_url:
            uploader_id = info_dict.get('uploader_id')
            if uploader_id:
                channel_url = f"https://rutube.ru/channel/{uploader_id}/"
        
        views = info_dict.get('view_count')
        likes = info_dict.get('like_count')
        
        return CaptionBuilder(
            title=title,
            video_url=video_url,
            creation_date=creation_date,
            channel_name=channel_name,
            channel_url=channel_url or '',
            likes=likes,
            views=views
        )

