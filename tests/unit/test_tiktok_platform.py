"""Tests para TikTokPlatform."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import tempfile

from social.platforms.tiktok import TikTokPlatform
from social.config import Config


class TestTikTokPlatform:
    """Tests para TikTokPlatform."""
    
    def test_tiktok_platform_init(self, config):
        """Test que TikTokPlatform se inicializa correctamente."""
        platform = TikTokPlatform(name='tiktok', global_config=config)
        
        assert platform.name == 'tiktok'
        assert platform.format == 'best'
    
    def test_tiktok_parse_channel_info_from_html_real_dump(self, config):
        """
        Test parsing de channel info desde un archivo dump real.
        
        Usa el archivo dump real del directorio raíz para probar el parsing.
        Usa pytest --pdb para debuggear si falla.
        """
        # Buscar archivo dump en el directorio raíz
        dump_files = list(Path('.').glob('*.dump'))
        
        if not dump_files:
            pytest.skip("No dump file found in root directory")
        
        dump_file = dump_files[0]
        print(f"\n=== Using dump file: {dump_file} ===")
        
        platform = TikTokPlatform(name='tiktok', global_config=config)
        
        # Leer el contenido del dump
        with open(dump_file, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        print(f"HTML content length: {len(html_content)} characters")
        
        # Parsear
        result = platform._parse_channel_info_from_html(html_content)
        
        # Verificar que se extrajo información
        assert result is not None, "Should extract channel info from dump file"
        assert 'channel' in result
        assert 'channel_id' in result
        assert 'channel_url' in result
        assert 'channel_follower_count' in result
        
        # Verificar que tiene datos de TikTok
        if result.get('channel'):
            assert len(result['channel']) > 0
        if result.get('unique_id'):
            assert len(result['unique_id']) > 0
        
        # Debug: mostrar resultado completo
        print("\n=== Parsed Channel Info ===")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    def test_tiktok_parse_channel_info_from_html_mock(self, config):
        """Test parsing con HTML mock."""
        platform = TikTokPlatform(name='tiktok', global_config=config)
        
        # HTML mock con __UNIVERSAL_DATA_FOR_REHYDRATION__
        mock_html = """
        <html>
        <script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">
        {
            "__DEFAULT_SCOPE__": {
                "webapp.video-detail": {
                    "itemInfo": {
                        "itemStruct": {
                            "author": {
                                "id": "123456",
                                "uniqueId": "test_user",
                                "nickname": "Test User",
                                "signature": "Test bio",
                                "avatarLarger": "https://example.com/avatar.jpg",
                                "createTime": 1609459200,
                                "secUid": "test_sec_uid"
                            },
                            "authorStats": {
                                "followerCount": 1000,
                                "followingCount": 500,
                                "heart": 5000,
                                "videoCount": 100,
                                "diggCount": 2000,
                                "friendCount": 50
                            },
                            "locationCreated": "US"
                        }
                    }
                }
            }
        }
        </script>
        </html>
        """
        
        result = platform._parse_channel_info_from_html(mock_html)
        
        assert result is not None
        assert result['channel'] == 'Test User'
        assert result['uploader'] == 'test_user'
        assert result['unique_id'] == 'test_user'
        assert result['channel_id'] == 'test_sec_uid'
        assert result['channel_follower_count'] == 1000
        assert result['following_count'] == 500
        assert result['heart_count'] == 5000
        assert result['video_count'] == 100
        assert result['digg_count'] == 2000
        assert result['friend_count'] == 50
        assert result['location'] == 'US'
        assert result['description'] == 'Test bio'
        assert 'test_user' in result['channel_url']
    
    def test_tiktok_get_channel_info_with_real_dump_file(self, config):
        """
        Test get_channel_info usando archivo dump real.
        
        Simula que yt-dlp ya generó el dump y solo prueba la lógica de lectura.
        Usa pytest --pdb para debuggear.
        """
        # Buscar archivo dump real
        dump_files = list(Path('.').glob('*.dump'))
        if not dump_files:
            pytest.skip("No dump file found in root directory")
        
        dump_file = dump_files[0]
        dump_content = dump_file.read_text(encoding='utf-8', errors='ignore')
        
        print(f"\n=== Testing with dump file: {dump_file} ===")
        print(f"Dump file size: {len(dump_content)} characters")
        
        platform = TikTokPlatform(name='tiktok', global_config=config)
        
        # Mock tempfile.TemporaryDirectory para usar el dump real
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Copiar dump al directorio temporal
            test_dump_file = tmpdir_path / dump_file.name
            test_dump_file.write_text(dump_content, encoding='utf-8')
            
            print(f"Created test dump file: {test_dump_file}")
            print(f"Test dump exists: {test_dump_file.exists()}")
            
            # Mock YoutubeDL para que no haga requests reales
            with patch('social.platforms.tiktok.YoutubeDL') as mock_ydl_class:
                mock_ydl_instance = MagicMock()
                mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
                mock_ydl_class.return_value.__exit__.return_value = None
                mock_ydl_instance.extract_info.return_value = None
                
                # Mock tempfile.TemporaryDirectory para usar nuestro tmpdir
                with patch('tempfile.TemporaryDirectory') as mock_tmpdir:
                    mock_tmpdir.return_value.__enter__.return_value = str(tmpdir_path)
                    mock_tmpdir.return_value.__exit__.return_value = None
                    
                    # Llamar get_channel_info
                    url = "https://www.tiktok.com/@test/video/123"
                    result = platform.get_channel_info(url)
                    
                    # Verificar resultado
                    if result:
                        assert 'channel' in result
                        print("\n=== Channel Info Result ===")
                        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
                    else:
                        # Si falla, permitir debug con --pdb
                        print(f"\n=== DEBUG INFO ===")
                        print(f"Temp dir: {tmpdir_path}")
                        print(f"Files in temp dir: {list(tmpdir_path.iterdir())}")
                        print(f"Test dump file exists: {test_dump_file.exists()}")
                        pytest.fail("get_channel_info returned None - use pytest --pdb to debug")
    
    @pytest.mark.e2e
    def test_tiktok_get_channel_info_integration(self, config):
        """
        Test de integración real (requiere conexión).
        
        Este test hace una llamada real a TikTok.
        Usa pytest --pdb para debuggear si falla.
        """
        platform = TikTokPlatform(name='tiktok', global_config=config)
        
        # URL de prueba
        test_url = "https://www.tiktok.com/@krizz_moor/video/7233599914847128838"
        
        print(f"\n=== Integration Test: {test_url} ===")
        
        # Llamar get_channel_info (esto hará una request real)
        result = platform.get_channel_info(test_url)
        
        # Verificar resultado
        if result:
            assert 'channel' in result
            assert result.get('channel') or result.get('uploader')
            print("\n=== Integration Test Result ===")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        else:
            # Si falla, permitir debug con --pdb
            pytest.fail("Integration test failed - use pytest --pdb to debug")

