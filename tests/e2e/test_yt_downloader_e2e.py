"""Tests end-to-end para YT_Downloader con integración real."""
import pytest
import os
from pathlib import Path
import time

from social.services.YT_Downloader import YT_Downloader
from social.config import Config


# Marcar todos los tests de este módulo como e2e
pytestmark = pytest.mark.e2e

# Helper para verificar si existen cookies
def _cookies_exist(platform_name='youtube'):
    """Verifica si existen cookies para una plataforma."""
    cookies_dir = Path(os.getenv("COOKIES_DIR", ".config/cookies")).expanduser()
    return cookies_dir.joinpath(f"{platform_name}.txt").exists()


class TestYT_DownloaderE2E:
    """Tests E2E para YT_Downloader con descargas reales."""
    
    @pytest.fixture
    def real_config(self, tmp_path):
        """Crea una configuración real para tests E2E."""
        config = Config()
        # Usar directorio temporal para descargas
        config.DOWNLOADS_DIR = tmp_path / 'downloads'
        config.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        return config
    
    @pytest.fixture
    def downloader(self, real_config):
        """Crea una instancia real de YT_Downloader."""
        return YT_Downloader(real_config)
    
    @pytest.mark.skipif(
        not _cookies_exist('youtube'),
        reason="YouTube cookies not found; skipping real download test"
    )
    def test_download_youtube_video_real(self, downloader, real_config):
        """Test E2E: Descarga real de un video corto de YouTube con cookies."""
        # Usar un video de prueba corto y público
        # Este es un video de prueba de YouTube (Big Buck Bunny trailer)
        test_url = "https://www.youtube.com/watch?v=hPrGVYk2JdQ"
        
        # Realizar la descarga
        downloader.download(test_url)
        
        # Verificar que se descargó algo en el directorio de YouTube
        youtube_dir = real_config.DOWNLOADS_DIR / 'youtube'
        assert youtube_dir.exists(), "El directorio de YouTube no fue creado"
        
        # Verificar que hay archivos descargados
        downloaded_files = list(youtube_dir.glob('*'))
        assert len(downloaded_files) > 0, "No se descargó ningún archivo"
        
        # Verificar que al menos un archivo tiene tamaño > 0
        has_content = any(f.stat().st_size > 0 for f in downloaded_files if f.is_file())
        assert has_content, "Los archivos descargados están vacíos"
    
    def test_download_with_info_extraction(self, downloader, real_config):
        """Test E2E: Verifica que se puede extraer información sin descargar."""
        test_url = "https://www.youtube.com/watch?v=hPrGVYk2JdQ"
        
        # Extraer solo información
        from yt_dlp import YoutubeDL
        
        platform = downloader.platforms['youtube']
        opts = platform.get_ydl_opts()
        opts['skip_download'] = True  # Solo extraer info
        
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
        
        # Verificar que se extrajo información
        assert info is not None
        assert 'title' in info
        assert 'extractor' in info
        assert info['extractor'].lower() == 'youtube'
    
    @pytest.mark.skipif(
        not _cookies_exist('youtube'),
        reason="YouTube cookies not found; skipping real download test"
    )
    def test_download_with_custom_format(self, downloader, real_config):
        """Test E2E: Descarga con formato personalizado."""
        test_url = "https://www.youtube.com/watch?v=hPrGVYk2JdQ"
        
        # Modificar el formato de la plataforma YouTube
        youtube_platform = downloader.platforms['youtube']
        youtube_platform.format = 'worst'  # Descargar la peor calidad para ser más rápido
        
        # Realizar la descarga
        downloader.download(test_url, platform=youtube_platform)
        
        # Verificar que se descargó
        youtube_dir = real_config.DOWNLOADS_DIR / 'youtube'
        downloaded_files = list(youtube_dir.glob('*'))
        assert len(downloaded_files) > 0
    
    @pytest.mark.slow
    @pytest.mark.skipif(
        not _cookies_exist('youtube'),
        reason="YouTube cookies not found; skipping real download test"
    )
    def test_download_multiple_videos(self, downloader, real_config):
        """Test E2E: Descarga múltiples videos."""
        test_urls = [
            "https://www.youtube.com/watch?v=hPrGVYk2JdQ",
            "https://www.youtube.com/watch?v=9YZWofsXe-w",  # Otro video de prueba
        ]
        
        for url in test_urls:
            try:
                downloader.download(url)
                # Pequeña pausa entre descargas
                time.sleep(1)
            except Exception as e:
                pytest.fail(f"Falló la descarga de {url}: {e}")
        
        # Verificar que se descargaron archivos
        youtube_dir = real_config.DOWNLOADS_DIR / 'youtube'
        downloaded_files = list(youtube_dir.glob('*'))
        assert len(downloaded_files) >= 2, "No se descargaron suficientes archivos"
    
    def test_platform_detection_real(self, downloader):
        """Test E2E: Verifica la detección automática de plataforma."""
        test_url = "https://www.youtube.com/watch?v=hPrGVYk2JdQ"
        
        # Detectar plataforma sin descargar
        from yt_dlp import YoutubeDL
        
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(test_url, download=False)
            extractor = info.get('extractor', '').lower()
        
        # Verificar que se detectó correctamente
        assert 'youtube' in extractor
        
        # Verificar que el downloader puede obtener la plataforma correcta
        platform = downloader._get_platform_for_extractor(extractor)
        assert platform is not None
        assert platform.name == 'youtube'
    
    @pytest.mark.skipif(
        not _cookies_exist('youtube'),
        reason="YouTube cookies not found; skipping real download test"
    )
    def test_download_with_cookies_real(self, downloader, real_config):
        """Test E2E: Verifica que se usan cookies reales si están disponibles."""
        test_url = "https://www.youtube.com/watch?v=hPrGVYk2JdQ"
        
        # Verificar que existen cookies reales
        youtube_platform = downloader.platforms['youtube']
        cookies_path = youtube_platform.get_cookies_path()
        assert cookies_path.exists(), "Las cookies de YouTube deben existir para este test"
        
        # Verificar que las opciones incluyen el archivo de cookies
        opts = youtube_platform.get_ydl_opts()
        assert 'cookiefile' in opts
        assert opts['cookiefile'] == str(cookies_path)
        
        # Realizar descarga con cookies reales
        downloader.download(test_url)
        
        # Verificar que se descargó
        youtube_dir = real_config.DOWNLOADS_DIR / 'youtube'
        downloaded_files = list(youtube_dir.glob('*'))
        assert len(downloaded_files) > 0
    
    def test_download_handles_invalid_url(self, downloader):
        """Test E2E: Verifica el manejo de URLs inválidas."""
        invalid_url = "https://www.youtube.com/watch?v=INVALID_VIDEO_ID_12345"
        
        # Debería lanzar una excepción
        with pytest.raises(Exception):
            downloader.download(invalid_url)
    
    @pytest.mark.skipif(
        not _cookies_exist('youtube'),
        reason="YouTube cookies not found; skipping real download test"
    )
    def test_download_creates_platform_directory(self, downloader, real_config):
        """Test E2E: Verifica que se crea el directorio de la plataforma."""
        test_url = "https://www.youtube.com/watch?v=hPrGVYk2JdQ"
        
        youtube_dir = real_config.DOWNLOADS_DIR / 'youtube'
        
        # Asegurarse de que no existe antes
        if youtube_dir.exists():
            import shutil
            shutil.rmtree(youtube_dir)
        
        # Realizar descarga
        downloader.download(test_url)
        
        # Verificar que se creó el directorio
        assert youtube_dir.exists()
        assert youtube_dir.is_dir()


@pytest.mark.e2e
@pytest.mark.slow
class TestYT_DownloaderE2EAdvanced:
    """Tests E2E avanzados para YT_Downloader."""
    
    @pytest.mark.skipif(
        not _cookies_exist('youtube'),
        reason="YouTube cookies not found; skipping real download test"
    )
    def test_download_with_metadata(self, tmp_path):
        """Test E2E: Descarga con extracción de metadata."""
        config = Config()
        config.DOWNLOADS_DIR = tmp_path / 'downloads'
        config.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        
        downloader = YT_Downloader(config)
        
        # Configurar para guardar metadata
        youtube_platform = downloader.platforms['youtube']
        youtube_platform.extra_opts = {
            'writeinfojson': True,
            'writethumbnail': False,  # No descargar thumbnail para ser más rápido
        }
        
        test_url = "https://www.youtube.com/watch?v=hPrGVYk2JdQ"
        downloader.download(test_url, platform=youtube_platform)
        
        # Verificar que se creó el archivo .info.json
        youtube_dir = config.DOWNLOADS_DIR / 'youtube'
        info_files = list(youtube_dir.glob('*.info.json'))
        assert len(info_files) > 0, "No se generó archivo de metadata"
    
    @pytest.mark.skipif(
        not _cookies_exist('youtube'),
        reason="YouTube cookies not found; skipping real download test"
    )
    def test_download_respects_platform_config(self, tmp_path):
        """Test E2E: Verifica que se respeta la configuración de plataforma."""
        config = Config()
        config.DOWNLOADS_DIR = tmp_path / 'downloads'
        config.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Crear configuración personalizada
        import json
        config.PLATFORMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        platforms_config = {
            'youtube': {
                'format': 'worst',  # Peor calidad para ser más rápido
                'extra_opts': {
                    'quiet': True,
                }
            }
        }
        with open(config.PLATFORMS_FILE, 'w', encoding='utf-8') as f:
            json.dump(platforms_config, f)
        
        downloader = YT_Downloader(config)
        
        # Verificar que se cargó la configuración
        youtube_platform = downloader.platforms['youtube']
        assert youtube_platform.format == 'worst'
        
        # Realizar descarga
        test_url = "https://www.youtube.com/watch?v=hPrGVYk2JdQ"
        downloader.download(test_url)
        
        # Verificar que se descargó
        youtube_dir = config.DOWNLOADS_DIR / 'youtube'
        downloaded_files = list(youtube_dir.glob('*'))
        assert len(downloaded_files) > 0
