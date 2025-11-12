"""Tests for TelegramRecoveryBotClient."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from social.services.telegram_recovery_bot_client import TelegramRecoveryBotClient


class TestTelegramRecoveryBotClient:
    """Test suite for TelegramRecoveryBotClient."""
    
    @pytest.fixture
    def mock_telegram_client(self):
        """Create a mock TelegramClient."""
        client = MagicMock()
        return client
    
    @pytest.fixture
    def bot_client(self, mock_telegram_client):
        """Create TelegramRecoveryBotClient instance."""
        return TelegramRecoveryBotClient(mock_telegram_client)
    
    @pytest.mark.asyncio
    async def test_recover_video_success(self, bot_client, mock_telegram_client, tmp_path):
        """Test successful video recovery."""
        # Mock conversation context
        mock_conv = MagicMock()
        mock_telegram_client.conversation = MagicMock(return_value=mock_conv)
        
        # Mock "Found" response
        mock_response1 = MagicMock()
        mock_response1.text = "Found video!"
        
        # Mock video message response
        mock_response2 = MagicMock()
        mock_response2.video = True
        mock_response2.document = None
        mock_response2.text = "#TestVideo abc123 720p\n\n👀 Channel: Test (https://youtube.com)"
        mock_response2.message = mock_response2.text
        
        # Mock download
        video_file = tmp_path / "test_video.mp4"
        video_file.write_text("fake video content")
        mock_response2.download_media = AsyncMock(return_value=str(video_file))
        
        # Setup conversation mock
        mock_conv.send_message = AsyncMock()
        mock_conv.get_response = AsyncMock(side_effect=[mock_response1, mock_response2])
        mock_conv.__aenter__ = AsyncMock(return_value=mock_conv)
        mock_conv.__aexit__ = AsyncMock()
        
        # Test recovery
        result_path, caption = await bot_client.recover_video(
            "https://youtube.com/watch?v=abc123",
            download_path=tmp_path
        )
        
        assert result_path == video_file
        assert caption == mock_response2.text
        assert video_file.exists()
    
    @pytest.mark.asyncio
    async def test_recover_video_not_found(self, bot_client, mock_telegram_client):
        mock_conv = MagicMock()
        mock_telegram_client.conversation = MagicMock(return_value=mock_conv)
        
        mock_response1 = MagicMock()
        mock_response1.text = "Error"  # No "found" word
        
        mock_conv.send_message = AsyncMock()
        mock_conv.get_response = AsyncMock(return_value=mock_response1)
        mock_conv.__aenter__ = AsyncMock(return_value=mock_conv)
        mock_conv.__aexit__ = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError):
            await bot_client.recover_video("https://youtube.com/watch?v=notfound")
    
    @pytest.mark.asyncio
    async def test_recover_video_no_video_in_response(self, bot_client, mock_telegram_client):
        mock_conv = MagicMock()
        mock_telegram_client.conversation = MagicMock(return_value=mock_conv)
        
        mock_response1 = MagicMock()
        mock_response1.text = "Found video!"
        
        mock_response2 = MagicMock()
        mock_response2.video = None
        mock_response2.document = None
        mock_response2.text = "Text only"
        
        mock_conv.send_message = AsyncMock()
        mock_conv.get_response = AsyncMock(side_effect=[mock_response1, mock_response2])
        mock_conv.__aenter__ = AsyncMock(return_value=mock_conv)
        mock_conv.__aexit__ = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError):
            await bot_client.recover_video("https://youtube.com/watch?v=abc123")
    
    @pytest.mark.asyncio
    async def test_recover_video_download_failed(self, bot_client, mock_telegram_client, tmp_path):
        mock_conv = MagicMock()
        mock_telegram_client.conversation = MagicMock(return_value=mock_conv)
        
        mock_response1 = MagicMock()
        mock_response1.text = "Found video!"
        
        mock_response2 = MagicMock()
        mock_response2.video = True
        mock_response2.document = None
        mock_response2.text = "Caption"
        mock_response2.message = "Caption"
        mock_response2.download_media = AsyncMock(return_value=None)
        
        mock_conv.send_message = AsyncMock()
        mock_conv.get_response = AsyncMock(side_effect=[mock_response1, mock_response2])
        mock_conv.__aenter__ = AsyncMock(return_value=mock_conv)
        mock_conv.__aexit__ = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError):
            await bot_client.recover_video("https://youtube.com/watch?v=abc123", download_path=tmp_path)
    
    @pytest.mark.asyncio
    async def test_check_bot_available_success(self, bot_client, mock_telegram_client):
        """Test checking bot availability when bot is available."""
        mock_entity = MagicMock()
        mock_entity.username = "Kyreth_hq_bot"
        mock_telegram_client.get_entity = AsyncMock(return_value=mock_entity)
        
        result = await bot_client.check_bot_available()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_bot_available_failure(self, bot_client, mock_telegram_client):
        """Test checking bot availability when bot is not available."""
        mock_telegram_client.get_entity = AsyncMock(side_effect=Exception("Bot not found"))
        
        result = await bot_client.check_bot_available()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_recover_video_with_document(self, bot_client, mock_telegram_client, tmp_path):
        """Test recovery when bot sends video as document."""
        mock_conv = MagicMock()
        mock_telegram_client.conversation = MagicMock(return_value=mock_conv)
        
        mock_response1 = MagicMock()
        mock_response1.text = "Found video!"
        
        # Mock video as document instead of video
        mock_response2 = MagicMock()
        mock_response2.video = None
        mock_response2.document = True  # Document instead of video
        mock_response2.text = "Caption"
        mock_response2.message = "Caption"
        
        video_file = tmp_path / "test_video.mp4"
        video_file.write_text("fake content")
        mock_response2.download_media = AsyncMock(return_value=str(video_file))
        
        mock_conv.send_message = AsyncMock()
        mock_conv.get_response = AsyncMock(side_effect=[mock_response1, mock_response2])
        mock_conv.__aenter__ = AsyncMock(return_value=mock_conv)
        mock_conv.__aexit__ = AsyncMock()
        
        result_path, caption = await bot_client.recover_video(
            "https://youtube.com/watch?v=abc123",
            download_path=tmp_path
        )
        
        assert result_path == video_file
        assert caption == "Caption"

