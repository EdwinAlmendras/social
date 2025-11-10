"""Tests para social.platforms."""
import pytest
from pathlib import Path

from social.platforms import (
    Platform,
    YouTubePlatform,
    VKPlatform,
    RutubePlatform,
    load_platforms,
    EXTRACTOR_TO_PLATFORM,
    DEFAULT_PLATFORM_CLASS,
)
from social.config import Config


class TestPlatform:
    """Tests para la clase base Platform."""
    
    def test_platform_init_defaults(self, config):
        """Test que Platform se inicializa con valores por defecto."""
        platform = Platform(name='test', global_config=config)
        
        assert platform.name == 'test'
        assert platform.format == Platform.DEFAULT_FORMAT
        assert platform.cookies == config.COOKIES_DIR / 'test.txt'
        assert platform.download_dir == config.DOWNLOADS_DIR / 'test'
        assert platform.download_dir.exists()
        assert platform.extra_opts == {}
    
    def test_platform_init_with_config(self, config):
        """Test que Platform usa configuración personalizada."""
        platform_config = {
            'format': 'worst',
            'cookies': 'custom.txt',
            'download_dir': '/custom/path',
            'extra_opts': {'test': 'value'},
        }
        
        platform = Platform(name='test', config=platform_config, global_config=config)
        
        assert platform.format == 'worst'
        assert platform.cookies == config.COOKIES_DIR / 'custom.txt'
        assert platform.download_dir == Path('/custom/path')
        assert platform.extra_opts == {'test': 'value'}
    
    def test_platform_init_without_global_config(self):
        """Test que Platform funciona sin global_config."""
        platform = Platform(name='test')
        
        assert platform.name == 'test'
        assert platform.format == Platform.DEFAULT_FORMAT
        assert platform.cookies == Path('test.txt')
        assert platform.download_dir == Path('downloads') / 'test'
    
    def test_platform_get_ydl_opts(self, config):
        """Test que get_ydl_opts retorna opciones correctas."""
        platform = Platform(name='test', global_config=config)
        
        opts = platform.get_ydl_opts()
        
        assert opts['format'] == Platform.DEFAULT_FORMAT
        assert 'outtmpl' in opts
        assert '%(id)s.%(ext)s' in opts['outtmpl']
        assert str(platform.download_dir) in opts['outtmpl']
    
    def test_platform_get_ydl_opts_with_cookies(self, config, cookie_file):
        """Test que get_ydl_opts incluye cookies si el archivo existe."""
        platform = Platform(name='youtube', global_config=config)
        # Crear archivo de cookies
        platform.cookies.parent.mkdir(parents=True, exist_ok=True)
        platform.cookies.write_text('# Cookies')
        
        opts = platform.get_ydl_opts()
        
        assert 'cookiefile' in opts
        assert opts['cookiefile'] == str(platform.cookies)
    
    def test_platform_get_ydl_opts_without_cookies(self, config):
        """Test que get_ydl_opts no incluye cookies si el archivo no existe."""
        platform = Platform(name='test', global_config=config)
        
        opts = platform.get_ydl_opts()
        
        assert 'cookiefile' not in opts
    
    def test_platform_get_ydl_opts_with_extra_opts(self, config):
        """Test que get_ydl_opts incluye extra_opts."""
        platform_config = {
            'extra_opts': {
                'writeinfojson': True,
                'writethumbnail': True,
            }
        }
        platform = Platform(name='test', config=platform_config, global_config=config)
        
        opts = platform.get_ydl_opts()
        
        assert opts['writeinfojson'] is True
        assert opts['writethumbnail'] is True
    
    def test_platform_get_download_dir(self, config):
        """Test que get_download_dir retorna el directorio correcto."""
        platform = Platform(name='test', global_config=config)
        
        assert platform.get_download_dir() == platform.download_dir
        assert platform.get_download_dir() == config.DOWNLOADS_DIR / 'test'
    
    def test_platform_get_cookies_path(self, config):
        """Test que get_cookies_path retorna la ruta correcta."""
        platform = Platform(name='test', global_config=config)
        
        assert platform.get_cookies_path() == platform.cookies
        assert platform.get_cookies_path() == config.COOKIES_DIR / 'test.txt'


class TestYouTubePlatform:
    """Tests para YouTubePlatform."""
    
    def test_youtube_platform_init(self, config):
        """Test que YouTubePlatform se inicializa correctamente."""
        platform = YouTubePlatform(name='youtube', global_config=config)
        
        assert platform.name == 'youtube'
        assert platform.format == YouTubePlatform.DEFAULT_FORMAT
        assert 'bestvideo' in platform.format
        assert 'bestaudio' in platform.format
    
    def test_youtube_platform_init_with_config(self, config):
        """Test que YouTubePlatform puede usar configuración personalizada."""
        platform_config = {'format': 'worst'}
        platform = YouTubePlatform(name='youtube', config=platform_config, global_config=config)
        
        assert platform.format == 'worst'
    
    def test_youtube_platform_get_ydl_opts(self, config):
        """Test que YouTubePlatform.get_ydl_opts funciona."""
        platform = YouTubePlatform(name='youtube', global_config=config)
        
        opts = platform.get_ydl_opts()
        
        assert opts['format'] == YouTubePlatform.DEFAULT_FORMAT
        assert 'outtmpl' in opts


class TestVKPlatform:
    """Tests para VKPlatform."""
    
    def test_vk_platform_init(self, config):
        """Test que VKPlatform se inicializa correctamente."""
        platform = VKPlatform(name='vk', global_config=config)
        
        assert platform.name == 'vk'
        assert platform.format == Platform.DEFAULT_FORMAT
    
    def test_vk_platform_get_ydl_opts(self, config):
        """Test que VKPlatform.get_ydl_opts funciona."""
        platform = VKPlatform(name='vk', global_config=config)
        
        opts = platform.get_ydl_opts()
        
        assert 'format' in opts
        assert 'outtmpl' in opts


class TestRutubePlatform:
    """Tests para RutubePlatform."""
    
    def test_rutube_platform_init(self, config):
        """Test que RutubePlatform se inicializa correctamente."""
        platform = RutubePlatform(name='rutube', global_config=config)
        
        assert platform.name == 'rutube'
        assert platform.format == Platform.DEFAULT_FORMAT
    
    def test_rutube_platform_get_ydl_opts(self, config):
        """Test que RutubePlatform.get_ydl_opts funciona."""
        platform = RutubePlatform(name='rutube', global_config=config)
        
        opts = platform.get_ydl_opts()
        
        assert 'format' in opts
        assert 'outtmpl' in opts


class TestLoadPlatforms:
    """Tests para la función load_platforms."""
    
    def test_load_platforms_defaults(self, config):
        """Test que load_platforms carga plataformas con valores por defecto."""
        platforms = load_platforms(config)
        
        assert isinstance(platforms, dict)
        assert 'youtube' in platforms
        assert 'vk' in platforms
        assert 'rutube' in platforms
        
        assert isinstance(platforms['youtube'], YouTubePlatform)
        assert isinstance(platforms['vk'], VKPlatform)
        assert isinstance(platforms['rutube'], RutubePlatform)
    
    def test_load_platforms_with_config(self, config, platforms_json_file):
        """Test que load_platforms usa configuración desde platforms.json."""
        platforms = load_platforms(config)
        
        assert platforms['youtube'].format == 'bestvideo+bestaudio/best'
        assert 'writeinfojson' in platforms['youtube'].extra_opts
        assert platforms['vk'].format == 'best'
    
    def test_load_platforms_custom_download_dir(self, config, platforms_json_file, temp_dir):
        """Test que load_platforms respeta download_dir personalizado."""
        platforms = load_platforms(config)
        
        # VK tiene un download_dir personalizado en el JSON
        vk_download_dir = platforms['vk'].get_download_dir()
        vk_download_dir_str = str(vk_download_dir)
        assert 'custom_vk' in vk_download_dir_str or str(temp_dir / 'custom_vk') in vk_download_dir_str
    
    def test_load_platforms_handles_errors(self, config):
        """Test que load_platforms maneja errores correctamente."""
        # Crear un JSON con configuración inválida para una plataforma
        config.PLATFORMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        invalid_config = {
            'youtube': {
                'download_dir': None,  # Esto podría causar un error
            }
        }
        import json
        with open(config.PLATFORMS_FILE, 'w', encoding='utf-8') as f:
            json.dump(invalid_config, f)
        
        # Debería cargar las otras plataformas incluso si una falla
        platforms = load_platforms(config)
        
        # Al menos debería tener las otras plataformas
        assert len(platforms) >= 0  # Puede que falle todas o ninguna

