"""Fixtures compartidas para los tests."""
import json
import tempfile
from pathlib import Path
import pytest

from social.config import Config


def pytest_configure(config):
    """Configurar markers personalizados para pytest."""
    config.addinivalue_line("markers", "e2e: marca tests end-to-end que requieren conexión real")
    config.addinivalue_line("markers", "slow: marca tests que tardan más tiempo en ejecutarse")
    config.addinivalue_line("markers", "unit: marca tests unitarios")
    config.addinivalue_line("markers", "integration: marca tests de integración")


@pytest.fixture
def temp_dir():
    """Crea un directorio temporal para tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config(temp_dir, monkeypatch):
    """Crea una instancia de Config con directorios temporales."""
    # Configurar variables de entorno temporales
    monkeypatch.setenv('CONFIG_DIR', str(temp_dir / 'config'))
    monkeypatch.setenv('COOKIES_DIR', str(temp_dir / 'cookies'))
    monkeypatch.setenv('DOWNLOADS_DIR', str(temp_dir / 'downloads'))
    
    config = Config()
    # Sobrescribir paths para usar el directorio temporal
    config.CONFIG_DIR = temp_dir / 'config'
    config.COOKIES_DIR = temp_dir / 'cookies'
    config.DOWNLOADS_DIR = temp_dir / 'downloads'
    config.ENTITIES_FILE = temp_dir / 'config' / 'entities.json'
    config.PLATFORMS_FILE = temp_dir / 'config' / 'platforms.json'
    
    # Crear directorios
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config.COOKIES_DIR.mkdir(parents=True, exist_ok=True)
    config.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    return config


@pytest.fixture
def platforms_json_file(temp_dir, config):
    """Crea un archivo platforms.json de ejemplo."""
    platforms_config = {
        'youtube': {
            'format': 'bestvideo+bestaudio/best',
            'cookies': 'youtube.txt',
            'extra_opts': {
                'writeinfojson': True,
            }
        },
        'vk': {
            'format': 'best',
            'download_dir': str(temp_dir / 'custom_vk'),
        }
    }
    
    config.PLATFORMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.PLATFORMS_FILE, 'w', encoding='utf-8') as f:
        json.dump(platforms_config, f)
    
    return config.PLATFORMS_FILE


@pytest.fixture
def cookie_file(temp_dir, config):
    """Crea un archivo de cookies de ejemplo."""
    cookie_path = config.COOKIES_DIR / 'youtube.txt'
    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    cookie_path.write_text('# Netscape HTTP Cookie File\n')
    return cookie_path

