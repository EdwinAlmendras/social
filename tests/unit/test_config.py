"""Tests para social.config.Config."""
import json
import pytest
from pathlib import Path

from social.config import Config


class TestConfig:
    """Tests para la clase Config."""
    
    def test_config_init_defaults(self, temp_dir, monkeypatch):
        """Test que Config se inicializa con valores por defecto."""
        monkeypatch.delenv('CONFIG_DIR', raising=False)
        monkeypatch.delenv('COOKIES_DIR', raising=False)
        monkeypatch.delenv('DOWNLOADS_DIR', raising=False)
        monkeypatch.delenv('ENTITIES_FILE', raising=False)
        monkeypatch.delenv('PLATFORMS_FILE', raising=False)
        # Mock Path.home()
        import pathlib
        original_home = pathlib.Path.home
        monkeypatch.setattr(pathlib.Path, 'home', classmethod(lambda cls: temp_dir))
        
        config = Config()
        
        assert config.CONFIG_DIR == temp_dir / '.config' / 'social'
        assert config.COOKIES_DIR == config.CONFIG_DIR / 'cookies'
        assert config.ENTITIES_FILE == config.CONFIG_DIR / 'entities.json'
        assert config.PLATFORMS_FILE == config.CONFIG_DIR / 'platforms.json'
        assert config.DOWNLOADS_DIR == Path.cwd() / 'downloads'
    
    def test_config_init_from_env(self, temp_dir, monkeypatch):
        """Test que Config lee variables de entorno."""
        monkeypatch.setenv('CONFIG_DIR', str(temp_dir / 'custom_config'))
        monkeypatch.setenv('COOKIES_DIR', str(temp_dir / 'custom_cookies'))
        monkeypatch.setenv('DOWNLOADS_DIR', str(temp_dir / 'custom_downloads'))
        
        config = Config()
        
        assert config.CONFIG_DIR == temp_dir / 'custom_config'
        assert config.COOKIES_DIR == temp_dir / 'custom_cookies'
        assert config.DOWNLOADS_DIR == temp_dir / 'custom_downloads'
    
    def test_load_platforms_config_file_exists(self, config, platforms_json_file):
        """Test que load_platforms_config carga el archivo si existe."""
        platforms_config = config.load_platforms_config()
        
        assert isinstance(platforms_config, dict)
        assert 'youtube' in platforms_config
        assert 'vk' in platforms_config
        assert platforms_config['youtube']['format'] == 'bestvideo+bestaudio/best'
    
    def test_load_platforms_config_file_not_exists(self, config):
        """Test que load_platforms_config retorna {} si el archivo no existe."""
        platforms_config = config.load_platforms_config()
        
        assert platforms_config == {}
    
    def test_load_platforms_config_invalid_json(self, config, temp_dir):
        """Test que load_platforms_config maneja JSON inválido."""
        # Crear archivo con JSON inválido
        config.PLATFORMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        config.PLATFORMS_FILE.write_text('{ invalid json }')
        
        platforms_config = config.load_platforms_config()
        
        assert platforms_config == {}
    
    def test_load_entities_file_exists(self, config, temp_dir):
        """Test que load_entities carga el archivo si existe."""
        entities_data = {'entity1': {'name': 'test'}}
        config.ENTITIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(config.ENTITIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(entities_data, f)
        
        config.load_entities()
        
        assert hasattr(config, 'ENTITIES')
        assert config.ENTITIES == entities_data
    
    def test_load_entities_file_not_exists(self, config):
        """Test que load_entities crea dict vacío si el archivo no existe."""
        config.load_entities()
        
        assert hasattr(config, 'ENTITIES')
        assert config.ENTITIES == {}
    
    def test_config_creates_directories(self, temp_dir, monkeypatch):
        """Test que Config crea los directorios necesarios."""
        config_dir = temp_dir / 'test_config'
        cookies_dir = temp_dir / 'test_cookies'
        downloads_dir = temp_dir / 'test_downloads'
        
        monkeypatch.setenv('CONFIG_DIR', str(config_dir))
        monkeypatch.setenv('COOKIES_DIR', str(cookies_dir))
        monkeypatch.setenv('DOWNLOADS_DIR', str(downloads_dir))
        
        config = Config()
        
        assert config_dir.exists()
        assert cookies_dir.exists()
        assert downloads_dir.exists()

