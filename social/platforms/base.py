from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from social.config import Config
from social.logger import get_logger
from social.core.caption_builder import CaptionBuilder

logger = get_logger(__name__)

class Platform:
    """Clase base para configuración de plataformas de video.
    
    Esta es una capa de configuración que permite definir opciones específicas
    por plataforma. yt-dlp ya maneja la detección y extracción de URLs automáticamente.
    """
    
    DEFAULT_FORMAT = "best"

    def __init__(self, name: str, config: dict = None, global_config: Config = None):
        """
        Inicializa una instancia de plataforma.
        
        Args:
            name: Nombre de la plataforma (ej: 'youtube')
            config: Diccionario de configuración específica de la plataforma
            global_config: Instancia de Config global
        """
        self.name = name
        self.global_config = global_config
        config = config or {}
        
        # Selección de formato
        self.format = config.get("format", self.DEFAULT_FORMAT)
        
        # Archivo de cookies
        cookie_file = config.get("cookies", f"{self.name}.txt")
        if self.global_config:
            self.cookies = self.global_config.COOKIES_DIR / cookie_file
        else:
            self.cookies = Path(cookie_file)
        
        # Directorio de descarga
        download_dir = config.get("download_dir")
        if download_dir:
            self.download_dir = Path(download_dir)
        elif self.global_config:
            self.download_dir = self.global_config.DOWNLOADS_DIR / self.name
        else:
            self.download_dir = Path("downloads") / self.name
        
        self.download_dir = Path(self.download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Opciones adicionales específicas de la plataforma
        self.extra_opts = config.get("extra_opts", {})

    def get_ydl_opts(self) -> Dict[str, Any]:
        """
        Obtiene las opciones de yt-dlp para esta plataforma.
        
        Returns:
            Diccionario de opciones de yt-dlp
        """
        opts = {
            'format': self.format,
            'outtmpl': str(self.download_dir / '%(id)s.%(ext)s'),
            'merge_output_format': 'mp4',
        }
        
        # Agregar cookies si el archivo existe
        if self.cookies.exists():
            opts['cookiefile'] = str(self.cookies)
            logger.debug(f"Usando archivo de cookies: {self.cookies}")
        else:
            logger.debug(f"Archivo de cookies no encontrado: {self.cookies}")
        
        # Combinar con opciones adicionales (extra_opts tienen prioridad)
        opts.update(self.extra_opts)
        
        return opts
    
    def get_download_dir(self) -> Path:
        """Obtiene el directorio de descarga para esta plataforma."""
        return self.download_dir
    
    def get_cookies_path(self) -> Path:
        """Obtiene la ruta del archivo de cookies para esta plataforma."""
        return self.cookies
    
    def create_caption(self, info_dict: Dict[str, Any]) -> CaptionBuilder:
        """
        Creates a CaptionBuilder from yt-dlp info_dict.
        
        This method should be overridden by each platform to correctly map
        platform-specific fields.
        
        Args:
            info_dict: Dictionary with information extracted by yt-dlp
            
        Returns:
            CaptionBuilder instance with mapped fields
        """
        # Base implementation using common fields
        title = info_dict.get('title') or ''
        video_url = info_dict.get('webpage_url') or ''
        
        # Parse creation date
        creation_date = self._parse_creation_date(info_dict)
        
        # Try to get channel info (prefer channel over uploader)
        channel_name = info_dict.get('channel') or info_dict.get('uploader') or ''
        channel_url = info_dict.get('uploader_url') or info_dict.get('channel_url') or ''
        
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
    
    def _parse_creation_date(self, info_dict: Dict[str, Any]) -> datetime:
        """
        Parses the creation date from info_dict.
        
        Tries to use timestamp, upload_date, or release_date.
        """
        # Try timestamp first
        timestamp = info_dict.get('timestamp')
        if timestamp:
            try:
                return datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError, OSError):
                pass
        
        # Try upload_date (format YYYYMMDD)
        upload_date = info_dict.get('upload_date')
        if upload_date:
            try:
                return datetime.strptime(upload_date, '%Y%m%d')
            except (ValueError, TypeError):
                pass
        
        # Try release_date
        release_date = info_dict.get('release_date')
        if release_date:
            try:
                return datetime.strptime(release_date, '%Y%m%d')
            except (ValueError, TypeError):
                pass
        
        # If no date found, use current date
        logger.warning(f"Could not get creation date for {info_dict.get('id', 'unknown')}, using current date")
        return datetime.now()
    
    def get_channel_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract channel information from a video or channel URL.
        
        Each platform should implement this method to extract channel info
        using platform-specific methods (yt-dlp, HTML parsing, etc.).
        
        Args:
            url: URL of a video or channel
            
        Returns:
            Dictionary with harmonized channel information (snake_case).
            Required fields:
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
            
            Platforms may include additional platform-specific fields
            (e.g., TikTok: following_count, heart_count, video_count, etc.)
            
        Raises:
            NotImplementedError: If platform doesn't implement this method
        """
        raise NotImplementedError(f"Platform {self.name} must implement get_channel_info")

