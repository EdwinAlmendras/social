from social.config import Config
from social.logger import get_logger
from social.platforms import load_platforms, DEFAULT_PLATFORM_CLASS
from social.platforms.base import Platform
from yt_dlp import YoutubeDL
from yt_dlp.extractor import gen_extractor_classes
from typing import Optional

logger = get_logger(__name__)

class YT_Downloader:
    def __init__(self, config: Config):
        """
        Inicializa el descargador YT con configuración.
        
        Args:
            config: Instancia de Config con configuraciones de plataformas
        """
        self.config = config
        self.platforms = load_platforms(config)
    
    def _detect_platform_from_url(self, url: str) -> Platform:
        """
        Detecta la plataforma desde una URL sin hacer ningún request HTTP.
        
        Args:
            url: URL del video
            
        Returns:
            Instancia de Platform correspondiente o Platform genérica por defecto
        """
        # Obtener todas las clases de extractores y encontrar el que coincida con la URL
        for ie_class in gen_extractor_classes():
            if ie_class.suitable(url):
                # Usar ie_key() en minúsculas para mapear a la plataforma
                extractor_key = ie_class.ie_key().lower()
                
                # Buscar plataforma específica
                if extractor_key in self.platforms:
                    logger.debug(f"Platform detected from URL: {extractor_key}")
                    return self.platforms[extractor_key]
                
                # Si no se encuentra, usar plataforma genérica
                logger.debug(f"No platform config found for extractor '{extractor_key}', using default")
                break
        
        # Usar plataforma genérica por defecto
        if 'default' not in self.platforms:
            self.platforms['default'] = DEFAULT_PLATFORM_CLASS(
                name="default",
                config={},
                global_config=self.config
            )
        return self.platforms['default']
    
    def _get_platform_for_extractor(self, extractor_name: str) -> Platform:
        """
        Obtiene la plataforma correspondiente a un extractor de yt-dlp.
        
        Args:
            extractor_name: Nombre del extractor (IE_NAME) de yt-dlp
            
        Returns:
            Instancia de Platform o Platform genérica por defecto
        """
        # Limpiar el nombre del extractor (puede tener sufijos como '+plugin')
        base_extractor = extractor_name.split('+')[0].lower()
        
        # Buscar plataforma específica
        if base_extractor in self.platforms:
            return self.platforms[base_extractor]
        
        # Usar plataforma genérica por defecto
        logger.debug(f"No se encontró configuración específica para extractor '{extractor_name}', usando configuración genérica")
        if 'default' not in self.platforms:
            self.platforms['default'] = DEFAULT_PLATFORM_CLASS(
                name="default",
                config={},
                global_config=self.config
            )
        return self.platforms['default']
    
    def download(self, url: str, platform: Optional[Platform] = None, donwload=True):
        """
        Descarga un video desde la URL dada.
        
        Args:
            url: URL del video a descargar
            platform: Instancia de Platform opcional. Si no se proporciona, 
                     se detectará automáticamente desde la URL sin hacer requests.
        """
        logger.info(f"Descargando video desde {url}")
        
        # Si no se proporciona plataforma, detectarla desde la URL (sin requests)
        if platform is None:
            logger.debug("No platform specified, detecting from URL pattern...")
            platform = self._detect_platform_from_url(url)
            logger.info(f"Detected platform: {platform.name}")
        
        ydl_opts = platform.get_ydl_opts()
        
        logger.info(f"Using platform: {platform.name}")
        logger.debug(f"Download directory: {platform.get_download_dir()}")
        logger.debug(f"Format: {platform.format}")
        
        logger.debug(f"YDL opts: {ydl_opts}, download: {donwload}, url: {url}")
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=donwload)
                logger.info(f"Descarga exitosa: {info.get('title', 'Unknown')}")
                return info
        except Exception as e:
            logger.error(f"Error descargando {url}: {e}")
            raise