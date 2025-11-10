from .youtube import YouTubePlatform
from .vk import VKPlatform
from .rutube import RutubePlatform
from .tiktok import TikTokPlatform
from .base import Platform
from social.config import Config
from social.logger import get_logger

logger = get_logger(__name__)

# Mapeo de nombres de extractores de yt-dlp a clases de plataforma
# Los nombres deben coincidir con el IE_NAME del extractor de yt-dlp
EXTRACTOR_TO_PLATFORM = {
    'youtube': YouTubePlatform,
    'vk': VKPlatform,
    'rutube': RutubePlatform,
    'tiktok': TikTokPlatform,
}

# Para cualquier extractor sin clase específica, usamos Platform genérico
DEFAULT_PLATFORM_CLASS = Platform


def load_platforms(config: Config) -> dict:
    """
    Carga todas las plataformas configuradas.
    
    Las plataformas se cargan desde platforms.json si existe,
    o con configuración por defecto de las clases.
    
    Args:
        config: Instancia de Config
        
    Returns:
        dict con instancias de plataformas cargadas {extractor_name: Platform}
    """
    # Cargar configuración desde platforms.json si existe
    platforms_config = config.load_platforms_config()
    
    platforms = {}
    for extractor_name, platform_class in EXTRACTOR_TO_PLATFORM.items():
        try:
            # Obtener configuración específica para esta plataforma si existe
            platform_config = platforms_config.get(extractor_name, None)
            
            # Instanciar plataforma con configuración (None = usa valores por defecto)
            platform = platform_class(
                name=extractor_name,
                config=platform_config,
                global_config=config
            )
            platforms[extractor_name] = platform
            logger.info(f"Plataforma cargada: {extractor_name}")
        except Exception as e:
            logger.error(f"Error al cargar plataforma {extractor_name}: {e}")
    
    return platforms


__all__ = [
    'Platform',
    'YouTubePlatform',
    'VKPlatform',
    'RutubePlatform',
    'TikTokPlatform',
    'EXTRACTOR_TO_PLATFORM',
    'DEFAULT_PLATFORM_CLASS',
    'load_platforms',
]
