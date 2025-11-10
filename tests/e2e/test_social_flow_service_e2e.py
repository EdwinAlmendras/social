"""Tests end-to-end para SocialFlowService con integración real."""
import pytest
import pytest_asyncio
import os
import json
from pathlib import Path
from telethon import TelegramClient
from dotenv import load_dotenv

from social.services.social_flow_service import SocialFlowService
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
def social_flow_service():
    """Crea una instancia de SocialFlowService."""
    config = Config()
    return SocialFlowService(config)


class TestSocialFlowServiceE2E:
    """Tests E2E para SocialFlowService con flujo completo."""
    
    @pytest.mark.skipif(
        not _telegram_credentials_exist(),
        reason="Telegram credentials not found in environment variables"
    )
    @pytest.mark.skipif(
        not _entities_config_exists(),
        reason="Entities configuration not found or incomplete"
    )
    @pytest.mark.asyncio
    async def test_process_youtube_video(
        self,
        social_flow_service,
        telegram_client,
        bot_client,
        entities_config
    ):
        """Test E2E: Procesa un video de YouTube completo (descarga, caption, subida)."""
        # URL de prueba de YouTube (puedes cambiar por una URL real)
        test_url = "https://www.youtube.com/watch?v=IxdhuO30720"
        
        try:
            result = await social_flow_service.process_video(
                url=test_url,
                telegram_client=telegram_client,
                bot_client=bot_client
            )
            
            # Verificar resultado
            assert result['success'], f"Process failed: {result.get('error', 'Unknown error')}"
            assert 'video_path' in result
            assert 'caption' in result
            assert result['platform_name'] == 'youtube'
            
            # Verificar que el archivo existe
            video_path = result['video_path']
            assert video_path.exists(), f"Video file not found: {video_path}"
            
            # Verificar que el caption no está vacío
            assert result['caption'], "Caption is empty"
            
            print(f"\n✓ Video processed successfully!")
            print(f"  Video: {video_path.name}")
            print(f"  Platform: {result['platform_name']}")
            print(f"  Caption length: {len(result['caption'])} chars")
            print(f"  Caption preview: {result['caption'][:100]}...")
            
        except Exception as e:
            pytest.fail(f"Process video failed: {e}")
    
    @pytest.mark.skipif(
        not _telegram_credentials_exist(),
        reason="Telegram credentials not found"
    )
    @pytest.mark.skipif(
        not _entities_config_exists(),
        reason="Entities configuration not found"
    )
    @pytest.mark.asyncio
    async def test_process_youtube_short(
        self,
        social_flow_service,
        telegram_client,
        bot_client,
        entities_config
    ):
        """Test E2E: Procesa un YouTube Short (debe usar topic 'shorts' y original_url)."""
        # URL de prueba de YouTube Short (puedes cambiar por una URL real)
        # Formato: https://www.youtube.com/shorts/VIDEO_ID
        test_url = "https://www.youtube.com/shorts/OHb1wR1GUlo"
        
        try:
            result = await social_flow_service.process_video(
                url=test_url,
                telegram_client=telegram_client,
                bot_client=bot_client
            )
            
            # Verificar resultado
            assert result['success'], f"Process failed: {result.get('error', 'Unknown error')}"
            assert 'video_path' in result
            assert 'caption' in result
            assert result['platform_name'] == 'youtube'
            
            # Verificar que el archivo existe
            video_path = result['video_path']
            assert video_path.exists(), f"Video file not found: {video_path}"
            
            # Verificar que el caption contiene original_url (no webpage_url para shorts)
            caption = result['caption']
            assert '/shorts/' in caption or 'youtube.com/shorts' in caption, \
                "Caption should contain shorts URL"
            
            print(f"\n✓ YouTube Short processed successfully!")
            print(f"  Video: {video_path.name}")
            print(f"  Platform: {result['platform_name']}")
            print(f"  Caption preview: {caption[:150]}...")
            
        except Exception as e:
            # Si el video no existe o hay error de descarga, skip el test
            if "Video unavailable" in str(e) or "Private video" in str(e):
                pytest.skip(f"Test video unavailable: {e}")
            else:
                pytest.fail(f"Process short failed: {e}")
    
    @pytest.mark.skipif(
        not _telegram_credentials_exist(),
        reason="Telegram credentials not found"
    )
    @pytest.mark.asyncio
    async def test_process_video_without_upload(
        self,
        social_flow_service
    ):
        """Test E2E: Procesa un video sin subir a Telegram (solo descarga y caption)."""
        test_url = "https://www.youtube.com/shorts/OHb1wR1GUlo"
        
        try:
            result = await social_flow_service.process_video(
                url=test_url
                # No proporcionar telegram_client ni bot_client
            )
            
            # Verificar resultado
            assert result['success'], f"Process failed: {result.get('error', 'Unknown error')}"
            assert 'video_path' in result
            assert 'caption' in result
            assert result['platform_name'] == 'youtube'
            
            # Verificar que el archivo existe
            video_path = result['video_path']
            assert video_path.exists(), f"Video file not found: {video_path}"
            
            print(f"\n✓ Video processed without upload!")
            print(f"  Video: {video_path.name}")
            print(f"  Caption: {result['caption'][:100]}...")
            
        except Exception as e:
            pytest.fail(f"Process video without upload failed: {e}")


@pytest.mark.e2e
class TestSocialFlowServiceE2EAdvanced:
    """Tests E2E avanzados para SocialFlowService."""
    
    @pytest.mark.skipif(
        not all([_telegram_credentials_exist(), _entities_config_exists()]),
        reason="Required resources not available"
    )
    @pytest.mark.asyncio
    async def test_process_video_with_custom_entity(
        self,
        social_flow_service,
        telegram_client,
        bot_client,
        entities_config
    ):
        """Test E2E: Procesa un video con entity y topic personalizados."""
        test_url = "https://www.youtube.com/shorts/OHb1wR1GUlo"
        youtube_config = entities_config['youtube']
        
        try:
            result = await social_flow_service.process_video(
                url=test_url,
                telegram_client=telegram_client,
                bot_client=bot_client,
                entity_id=youtube_config['group_id'],
                topic_id=youtube_config['topics']['videos']
            )
            
            assert result['success']
            print(f"\n✓ Video processed with custom entity!")
            
        except Exception as e:
            pytest.fail(f"Process with custom entity failed: {e}")

