"""Tests para social.services.YT_Downloader."""
import pytest
from pathlib import Path

from social.services.YT_Downloader import YT_Downloader
from social.platforms.base import Platform
from social.config import Config


class TestYT_Downloader:
    """Tests para YT_Downloader."""
    
    def test_yt_downloader_init(self, config):
        """Test que YT_Downloader se inicializa correctamente."""
        downloader = YT_Downloader(config)
        
        assert downloader.config == config
        assert isinstance(downloader.platforms, dict)
        assert 'youtube' in downloader.platforms
        assert 'vk' in downloader.platforms
        assert 'rutube' in downloader.platforms
    
    def test_get_platform_for_extractor_existing(self, config):
        """Test que _get_platform_for_extractor encuentra plataformas existentes."""
        downloader = YT_Downloader(config)
        
        platform = downloader._get_platform_for_extractor('youtube')
        
        assert platform is not None
        assert platform.name == 'youtube'
        assert isinstance(platform, Platform)
    
    def test_get_platform_for_extractor_with_plugin_suffix(self, config):
        """Test que _get_platform_for_extractor maneja sufijos de plugin."""
        downloader = YT_Downloader(config)
        
        platform = downloader._get_platform_for_extractor('youtube+plugin')
        
        assert platform is not None
        assert platform.name == 'youtube'
    
    def test_get_platform_for_extractor_unknown(self, config):
        """Test que _get_platform_for_extractor usa plataforma genérica para extractores desconocidos."""
        downloader = YT_Downloader(config)
        
        platform = downloader._get_platform_for_extractor('unknown_extractor')
        
        assert platform is not None
        assert platform.name == 'default'
        assert 'default' in downloader.platforms
    
    def test_get_platform_for_extractor_case_insensitive(self, config):
        """Test que _get_platform_for_extractor es case insensitive."""
        downloader = YT_Downloader(config)
        
        platform = downloader._get_platform_for_extractor('YOUTUBE')
        
        assert platform is not None
        assert platform.name == 'youtube'
    
    def test_download_with_platform_detection(self, config, monkeypatch):
        """Test que download detecta automáticamente la plataforma."""
        from unittest.mock import MagicMock
        
        # Mock de YoutubeDL con context manager
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = [
            {'extractor': 'youtube', 'title': 'Test Video'},  # Para detectar
            {'extractor': 'youtube', 'title': 'Test Video'},  # Para descargar
        ]
        mock_ydl_class = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_class.return_value.__exit__.return_value = None
        
        monkeypatch.setattr('social.services.YT_Downloader.YoutubeDL', mock_ydl_class)
        
        downloader = YT_Downloader(config)
        downloader.download('https://youtube.com/watch?v=test')
        
        # Verificar que se llamó extract_info dos veces (detección + descarga)
        assert mock_ydl_instance.extract_info.call_count == 2
    
    def test_download_with_explicit_platform(self, config, monkeypatch):
        """Test que download usa una plataforma explícita si se proporciona."""
        from unittest.mock import MagicMock
        
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {'extractor': 'youtube', 'title': 'Test Video'}
        mock_ydl_class = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_class.return_value.__exit__.return_value = None
        
        monkeypatch.setattr('social.services.YT_Downloader.YoutubeDL', mock_ydl_class)
        
        downloader = YT_Downloader(config)
        platform = downloader.platforms['youtube']
        
        downloader.download('https://youtube.com/watch?v=test', platform=platform)
        
        # Verificar que se llamó extract_info solo una vez (sin detección)
        assert mock_ydl_instance.extract_info.call_count == 1
    
    def test_download_uses_platform_opts(self, config, monkeypatch):
        """Test que download usa las opciones de la plataforma."""
        from unittest.mock import MagicMock
        
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = [
            {'extractor': 'youtube', 'title': 'Test Video'},  # Para detección
            {'extractor': 'youtube', 'title': 'Test Video'},  # Para descarga
        ]
        mock_ydl_class = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_class.return_value.__exit__.return_value = None
        
        monkeypatch.setattr('social.services.YT_Downloader.YoutubeDL', mock_ydl_class)
        
        downloader = YT_Downloader(config)
        downloader.download('https://youtube.com/watch?v=test')
        
        # Verificar que YoutubeDL se inicializó con las opciones correctas
        assert mock_ydl_class.call_count >= 1
        # Verificar que al menos una llamada tuvo opciones
        calls_with_opts = [call for call in mock_ydl_class.call_args_list if call[0] or call[1]]
        assert len(calls_with_opts) > 0
    
    def test_download_handles_extraction_error(self, config, monkeypatch):
        """Test que download maneja errores de extracción."""
        from unittest.mock import MagicMock
        
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = Exception("Extraction failed")
        mock_ydl_class = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_class.return_value.__exit__.return_value = None
        
        monkeypatch.setattr('social.services.YT_Downloader.YoutubeDL', mock_ydl_class)
        
        downloader = YT_Downloader(config)
        
        with pytest.raises(Exception, match="Extraction failed"):
            downloader.download('https://invalid-url.com')
    
    def test_download_logs_info(self, config, monkeypatch):
        """Test que download registra información útil."""
        from unittest.mock import MagicMock
        
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = [
            {'extractor': 'youtube', 'title': 'Test Video'},  # Para detección
            {'extractor': 'youtube', 'title': 'Test Video'},  # Para descarga
        ]
        mock_ydl_class = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_class.return_value.__exit__.return_value = None
        
        mock_logger = MagicMock()
        monkeypatch.setattr('social.services.YT_Downloader.YoutubeDL', mock_ydl_class)
        monkeypatch.setattr('social.services.YT_Downloader.logger', mock_logger)
        
        downloader = YT_Downloader(config)
        downloader.download('https://youtube.com/watch?v=test')
        
        # Verificar que se registró información
        assert mock_logger.info.called
        # debug puede no llamarse si no hay configuración específica

