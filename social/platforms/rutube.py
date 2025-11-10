from social.platforms.base import Platform

class RutubePlatform(Platform):
    """Configuración para Rutube.
    
    yt-dlp detecta automáticamente URLs de Rutube usando el extractor 'rutube'.
    Esta clase solo proporciona configuración específica para Rutube.
    """
    
    def __init__(self, name: str = "rutube", config: dict = None, global_config=None):
        super().__init__(name, config, global_config)

