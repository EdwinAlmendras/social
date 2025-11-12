from social.platforms.base import Platform

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

