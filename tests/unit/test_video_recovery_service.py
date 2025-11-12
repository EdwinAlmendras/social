"""Tests for VideoRecoveryService."""
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from social.services.video_recovery_service import VideoRecoveryService
from social.config import Config


class TestVideoRecoveryService:
    """Test suite for VideoRecoveryService."""
    
    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a mock Config instance."""
        config = MagicMock(spec=Config)
        config.DOWNLOADS_DIR = tmp_path / "downloads"
        config.DOWNLOADS_DIR.mkdir(exist_ok=True)
        return config
    
    @pytest.fixture
    def mock_telegram_client(self):
        """Create a mock TelegramClient."""
        return MagicMock()
    
    @pytest.fixture
    def recovery_service(self, mock_config, mock_telegram_client):
        service = VideoRecoveryService(mock_config, mock_telegram_client)
        return service
    
    @pytest.mark.asyncio
    async def test_recover_video_success(self, recovery_service, tmp_path):
        video_file = tmp_path / "recovered_video.mp4"
        video_file.write_text("fake video")
        
        caption = """#TestVideo abc123 720p

[👀 Channel: Test Channel](https://www.youtube.com/channel/UCtest)
__📅 15.06.2025__

https://www.youtube.com/watch?v=abc123"""
        
        recovery_service.bot_client.check_bot_available = AsyncMock(return_value=True)
        recovery_service.bot_client.recover_video = AsyncMock(return_value=(video_file, caption))
        
        result = await recovery_service.recover_video("https://www.youtube.com/watch?v=abc123")
        
        assert result['success'] is True
        assert result['video_path'] == video_file
        assert 'Test Channel' in result['caption']
        assert result['metadata']['channel_name'] == 'Test Channel'
    
    @pytest.mark.asyncio
    async def test_recover_video_bot_unavailable(self, recovery_service):
        """Test recovery when bot is unavailable."""
        recovery_service.bot_client.check_bot_available = AsyncMock(return_value=False)
        
        result = await recovery_service.recover_video("https://www.youtube.com/watch?v=abc123")
        
        assert result['success'] is False
        assert 'not available' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_recover_video_download_failed(self, recovery_service):
        recovery_service.bot_client.check_bot_available = AsyncMock(return_value=True)
        recovery_service.bot_client.recover_video = AsyncMock(return_value=(None, ""))
        
        result = await recovery_service.recover_video("https://www.youtube.com/watch?v=abc123")
        
        assert result['success'] is False
        assert 'Download failed' in result['error']
    
    @pytest.mark.asyncio
    async def test_recover_video_parsing_failed_fallback(self, recovery_service, tmp_path):
        video_file = tmp_path / "recovered_video.mp4"
        video_file.write_text("fake video")
        
        invalid_caption = "Some random text"
        
        recovery_service.bot_client.check_bot_available = AsyncMock(return_value=True)
        recovery_service.bot_client.recover_video = AsyncMock(return_value=(video_file, invalid_caption))
        
        result = await recovery_service.recover_video("https://www.youtube.com/watch?v=abc123")
        
        # Should succeed, parsing will work but create caption with None values
        assert result['success'] is True
        assert result['video_path'] == video_file
    
    @pytest.mark.asyncio
    async def test_rebuild_caption(self, recovery_service):
        """Test caption rebuilding from metadata."""
        metadata = {
            'title': 'Test Video',
            'video_id': 'abc123',
            'video_url': 'https://www.youtube.com/watch?v=abc123',
            'channel_name': 'Test Channel',
            'channel_url': 'https://www.youtube.com/channel/UCtest',
            'upload_date': datetime(2025, 6, 15, 14, 30),
            'quality': '720p',
            'platform': 'youtube'
        }
        
        caption = recovery_service._rebuild_caption(metadata)
        
        assert 'Test Video' in caption
        assert 'Test Channel' in caption
        assert '15.06.2025' in caption
        assert 'youtube.com' in caption
    
    @pytest.mark.asyncio
    async def test_rebuild_caption_missing_date(self, recovery_service):
        """Test caption rebuilding when upload date is missing."""
        metadata = {
            'title': 'Test Video',
            'video_url': 'https://www.youtube.com/watch?v=abc123',
            'channel_name': 'Test Channel',
            'channel_url': 'https://www.youtube.com/channel/UCtest',
            'upload_date': None  # Missing date
        }
        
        # Should not raise error, use current date
        caption = recovery_service._rebuild_caption(metadata)
        
        assert 'Test Video' in caption
        assert 'Test Channel' in caption
    
    @pytest.mark.asyncio
    async def test_recover_videos_batch(self, recovery_service, tmp_path):
        """Test batch recovery of multiple videos."""
        # Create mock video files
        video1 = tmp_path / "video1.mp4"
        video1.write_text("video1")
        video2 = tmp_path / "video2.mp4"
        video2.write_text("video2")
        
        caption1 = "#Video1 abc123 720p\n\nhttps://www.youtube.com/watch?v=abc123"
        caption2 = "#Video2 def456 1080p\n\nhttps://www.youtube.com/watch?v=def456"
        
        # Mock bot responses
        recovery_service.bot_client.check_bot_available = AsyncMock(return_value=True)
        recovery_service.bot_client.recover_video = AsyncMock(
            side_effect=[
                (video1, caption1),
                (video2, caption2)
            ]
        )
        
        urls = [
            "https://www.youtube.com/watch?v=abc123",
            "https://www.youtube.com/watch?v=def456"
        ]
        
        with patch('asyncio.sleep', new_callable=AsyncMock):  # Skip delays in tests
            results = await recovery_service.recover_videos_batch(urls)
        
        assert len(results) == 2
        assert results[0]['success'] is True
        assert results[1]['success'] is True
        assert results[0]['video_path'] == video1
        assert results[1]['video_path'] == video2
    
    @pytest.mark.asyncio
    async def test_recover_videos_batch_partial_failure(self, recovery_service, tmp_path):
        """Test batch recovery with some failures."""
        video1 = tmp_path / "video1.mp4"
        video1.write_text("video1")
        
        caption1 = "#Video1 abc123 720p\n\nhttps://www.youtube.com/watch?v=abc123"
        
        recovery_service.bot_client.check_bot_available = AsyncMock(return_value=True)
        recovery_service.bot_client.recover_video = AsyncMock(
            side_effect=[
                (video1, caption1),
                (None, "")  # Second recovery fails
            ]
        )
        
        urls = [
            "https://www.youtube.com/watch?v=abc123",
            "https://www.youtube.com/watch?v=failed"
        ]
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            results = await recovery_service.recover_videos_batch(urls)
        
        assert len(results) == 2
        assert results[0]['success'] is True
        assert results[1]['success'] is False
    
    @pytest.mark.asyncio
    async def test_recover_video_custom_download_dir(self, recovery_service, tmp_path):
        """Test recovery with custom download directory."""
        custom_dir = tmp_path / "custom_recovery"
        video_file = custom_dir / "video.mp4"
        custom_dir.mkdir()
        video_file.write_text("video")
        
        caption = "#Test abc123 720p\n\nhttps://www.youtube.com/watch?v=abc123"
        
        recovery_service.bot_client.check_bot_available = AsyncMock(return_value=True)
        recovery_service.bot_client.recover_video = AsyncMock(return_value=(video_file, caption))
        
        result = await recovery_service.recover_video(
            "https://www.youtube.com/watch?v=abc123",
            download_dir=custom_dir
        )
        
        assert result['success'] is True
        assert result['video_path'] == video_file

