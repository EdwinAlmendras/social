"""Tests end-to-end para TelegramUploaderService con integración real."""
import pytest
import pytest_asyncio
import os
import json
import asyncio
from pathlib import Path
from telethon import TelegramClient
from dotenv import load_dotenv

from social.services.telegram_uploader import TelegramUploderService
from social.config import Config

# Cargar variables de entorno del archivo .env
load_dotenv()


# Marcar todos los tests de este módulo como e2e
pytestmark = pytest.mark.e2e


def _telegram_credentials_exist():
    """Verifica si existen las credenciales de Telegram."""
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    bot_token = os.getenv('BOT_TOKEN')
    return all([api_id, api_hash, bot_token])


def _test_video_exists():
    """Verifica si existe un video de prueba."""
    test_video = Path('downloads/youtube/ZF5Q_K8YyGc.mp4')
    return test_video.exists()


def _entities_config_exists():
    """Verifica si existe la configuración de entities."""
    entities_file = Path('.config/entities.json')
    if not entities_file.exists():
        return False
    
    try:
        with open(entities_file, 'r', encoding='utf-8') as f:
            entities = json.load(f)
            youtube = entities.get('youtube', {})
            return 'group_id' in youtube and 'topics' in youtube
    except:
        return False


@pytest_asyncio.fixture
async def telegram_client():
    """Crea un cliente de Telegram real usando sesión existente."""
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    # Usar sesión existente (debe estar en la raíz del proyecto)
    session_file = 'uploader'
    
    # Verificar si existe el archivo de sesión
    session_path = Path(f'{session_file}.session')
    print(f"\n🔍 Checking session file: {session_path.absolute()}")
    print(f"   Session exists: {session_path.exists()}")
    
    client = TelegramClient(session_file, api_id, api_hash)
    
    print(f"🔌 Connecting to Telegram...")
    await client.connect()
    print(f"   Connected: {client.is_connected()}")
    
    is_authorized = await client.is_user_authorized()
    print(f"   Authorized: {is_authorized}")
    
    if not is_authorized:
        await client.disconnect()
        pytest.skip(f"Telegram client not authorized. Session file: {session_path.absolute()}")
    
    yield client
    
    await client.disconnect()


@pytest_asyncio.fixture
async def bot_client():
    """Crea un cliente bot de Telegram."""
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    bot_token = os.getenv('BOT_TOKEN')
    
    bot = TelegramClient('bot_session', api_id, api_hash)
    await bot.start(bot_token=bot_token)
    
    yield bot
    
    await bot.disconnect()


@pytest.fixture
def entities_config():
    """Carga la configuración de entities."""
    with open('.config/entities.json', 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def test_video_path():
    """Retorna la ruta del video de prueba."""
    return Path('downloads/youtube/ZF5Q_K8YyGc.mp4')


class TestTelegramUploaderE2E:
    """Tests E2E para TelegramUploaderService con subida real."""
    
    @pytest.mark.skipif(
        not _telegram_credentials_exist(),
        reason="Telegram credentials not found in environment variables"
    )
    @pytest.mark.skipif(
        not _test_video_exists(),
        reason="Test video not found at downloads/youtube/ZF5Q_K8YyGc.mp4"
    )
    @pytest.mark.skipif(
        not _entities_config_exists(),
        reason="Entities configuration not found or incomplete"
    )
    @pytest.mark.asyncio
    async def test_upload_video_to_telegram(
        self, 
        telegram_client,
        bot_client,
        entities_config, 
        test_video_path
    ):
        """Test E2E: Sube un video real a Telegram usando bot."""
        # Obtener configuración
        youtube_config = entities_config['youtube']
        group_id = youtube_config['group_id']
        topic_id = youtube_config['topics'].get('videos', 1)
        
        # Verificar que el video existe
        assert test_video_path.exists(), f"Video not found: {test_video_path}"
        
        # Verificar tamaño del video
        video_size = test_video_path.stat().st_size
        assert video_size > 0, "Video file is empty"
        
        # Preparar opciones de subida
        upload_options = {
            'video': str(test_video_path),
            'entity': group_id,
            'reply_to': topic_id,
            'client': telegram_client,
            'bot_client': bot_client,
            'caption': '🧪 Test upload from E2E tests\n\nThis is an automated test upload.'
        }
        
        # Realizar la subida
        try:
            result = await TelegramUploderService.upload(upload_options)
            
            # Verificar que la subida fue exitosa
            print(f"\n✓ Video uploaded successfully!")
            print(f"  Video: {test_video_path.name}")
            print(f"  Size: {video_size / (1024*1024):.2f} MB")
            print(f"  Group ID: {group_id}")
            print(f"  Topic ID: {topic_id}")
        
        except Exception as e:
            pytest.fail(f"Upload failed: {e}")
    
    @pytest.mark.skipif(
        not _telegram_credentials_exist(),
        reason="Telegram credentials not found in environment variables"
    )
    @pytest.mark.skipif(
        not _test_video_exists(),
        reason="Test video not found"
    )
    @pytest.mark.skipif(
        not _entities_config_exists(),
        reason="Entities configuration not found or incomplete"
    )
    @pytest.mark.asyncio
    async def test_upload_with_custom_caption(
        self, 
        telegram_client,
        bot_client,
        entities_config, 
        test_video_path
    ):
        """Test E2E: Sube un video con caption personalizado."""
        youtube_config = entities_config['youtube']
        group_id = youtube_config['group_id']
        topic_id = youtube_config['topics'].get('videos', 1)
        
        # Caption personalizado con formato
        custom_caption = """
🎬 **Test Video Upload**

📝 Description: This is a test upload with custom caption
🏷️ Tags: #test #e2e #automated
⏱️ Duration: Test video
📊 Quality: Original

_Uploaded via automated E2E tests_
        """.strip()
        
        upload_options = {
            'video_path': str(test_video_path),
            'entity': group_id,
            'reply_to': topic_id,
            'client': telegram_client,
            'bot_client': bot_client,
            'caption': custom_caption
        }
        
        try:
            result = await TelegramUploderService.upload(upload_options)
            
            print(f"\n✓ Video uploaded with custom caption!")
        
        except Exception as e:
            pytest.fail(f"Upload with custom caption failed: {e}")
    
    @pytest.mark.skipif(
        not _telegram_credentials_exist(),
        reason="Telegram credentials not found"
    )
    @pytest.mark.asyncio
    async def test_telegram_client_connection(self, telegram_client):
        """Test E2E: Verifica que el cliente de Telegram se conecta correctamente."""
        # Verificar que el cliente está conectado
        assert telegram_client.is_connected(), "Client is not connected"
        
        # Verificar que el usuario está autorizado
        is_authorized = await telegram_client.is_user_authorized()
        assert is_authorized, "User is not authorized"
        
        # Obtener información del usuario
        me = await telegram_client.get_me()
        assert me is not None, "Could not get user info"
        
        print(f"\n✓ Telegram client connected successfully!")
        print(f"  User: {me.first_name} {me.last_name or ''}")
        print(f"  Phone: {me.phone}")
        print(f"  ID: {me.id}")
    
    @pytest.mark.skipif(
        not _telegram_credentials_exist(),
        reason="Telegram credentials not found"
    )
    @pytest.mark.skipif(
        not _entities_config_exists(),
        reason="Entities configuration not found"
    )
    @pytest.mark.asyncio
    async def test_telegram_group_access(self, telegram_client, entities_config):
        """Test E2E: Verifica que se puede acceder al grupo de Telegram."""
        youtube_config = entities_config['youtube']
        group_id = youtube_config['group_id']
        
        try:
            # Intentar obtener información del grupo
            entity = await telegram_client.get_entity(group_id)
            
            assert entity is not None, "Could not get group entity"
            
            print(f"\n✓ Group access verified!")
            print(f"  Group ID: {group_id}")
            print(f"  Group Title: {entity.title}")
            
        except Exception as e:
            pytest.fail(f"Could not access group: {e}")
    
    def test_video_file_exists(self, test_video_path):
        """Test E2E: Verifica que el video de prueba existe."""
        assert test_video_path.exists(), f"Test video not found: {test_video_path}"
        
        # Verificar que es un archivo
        assert test_video_path.is_file(), "Path is not a file"
        
        # Verificar tamaño
        size = test_video_path.stat().st_size
        assert size > 0, "Video file is empty"
        
        print(f"\n✓ Test video found!")
        print(f"  Path: {test_video_path}")
        print(f"  Size: {size / (1024*1024):.2f} MB")
    
    def test_entities_config_valid(self, entities_config):
        """Test E2E: Verifica que la configuración de entities es válida."""
        assert 'youtube' in entities_config, "youtube config not found"
        
        youtube = entities_config['youtube']
        assert 'group_id' in youtube, "group_id not found"
        assert 'topics' in youtube, "topics not found"
        
        group_id = youtube['group_id']
        assert isinstance(group_id, int), "group_id should be an integer"
        assert group_id < 0, "group_id should be negative for groups"
        
        topics = youtube['topics']
        assert isinstance(topics, dict), "topics should be a dictionary"
        assert 'videos' in topics, "videos topic not found"
        
        print(f"\n✓ Entities configuration is valid!")
        print(f"  Group ID: {group_id}")
        print(f"  Topics: {list(topics.keys())}")


@pytest.mark.e2e
@pytest.mark.slow
class TestTelegramUploaderE2EAdvanced:
    """Tests E2E avanzados para TelegramUploaderService."""
    
    @pytest.mark.skipif(
        not all([_telegram_credentials_exist(), _test_video_exists(), _entities_config_exists()]),
        reason="Required resources not available"
    )
    @pytest.mark.asyncio
    async def test_upload_multiple_videos(self, tmp_path):
        """Test E2E: Sube múltiples videos (si hay más disponibles)."""
        # Este test se puede expandir cuando haya más videos de prueba
        pytest.skip("Multiple video upload test not implemented yet")
    
    @pytest.mark.skipif(
        not all([_telegram_credentials_exist(), _entities_config_exists()]),
        reason="Required resources not available"
    )
    @pytest.mark.asyncio
    async def test_upload_with_bot_client(self):
        """Test E2E: Sube usando bot client (si está configurado)."""
        # Este test requiere configuración adicional de bot
        pytest.skip("Bot client test not implemented yet")
