import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from social.services.telegram_message_scanner import TelegramMessageScanner


class TestTelegramMessageScanner:
    
    @pytest.fixture
    def mock_client(self):
        return MagicMock()
    
    @pytest.fixture
    def scanner(self, mock_client):
        return TelegramMessageScanner(mock_client)
    
    @pytest.mark.asyncio
    async def test_scan_group_success(self, scanner, mock_client):
        mock_entity = MagicMock()
        mock_client.get_entity = AsyncMock(return_value=mock_entity)
        
        msg1 = MagicMock()
        msg1.id = 1
        msg1.date = datetime.now()
        msg1.text = "Check this https://www.youtube.com/watch?v=abc123"
        
        msg2 = MagicMock()
        msg2.id = 2
        msg2.date = datetime.now()
        msg2.text = "No URLs here"
        
        msg3 = MagicMock()
        msg3.id = 3
        msg3.date = datetime.now()
        msg3.text = "TikTok https://tiktok.com/@user/video/123456"
        
        async def mock_iter():
            for msg in [msg1, msg2, msg3]:
                yield msg
        
        mock_client.iter_messages = MagicMock(return_value=mock_iter())
        
        results = await scanner.scan_group(123456, limit=10)
        
        assert len(results) == 2
        assert results[0]['message_id'] == 1
        assert len(results[0]['urls']) == 1
        assert 'youtube.com' in results[0]['urls'][0]
        assert results[1]['message_id'] == 3
    
    def test_extract_urls_youtube(self, scanner):
        text = "Check https://www.youtube.com/watch?v=abc123 and https://youtu.be/xyz789"
        urls = scanner._extract_urls(text)
        assert len(urls) == 2
        assert 'youtube.com' in urls[0]
        assert 'youtu.be' in urls[1]
    
    def test_extract_urls_tiktok(self, scanner):
        text = "TikTok video: https://tiktok.com/@user/video/123456"
        urls = scanner._extract_urls(text)
        assert len(urls) == 1
        assert 'tiktok.com' in urls[0]
    
    def test_extract_urls_vk(self, scanner):
        text = "VK https://vk.com/video123456"
        urls = scanner._extract_urls(text)
        assert len(urls) == 1
        assert 'vk.com' in urls[0]
    
    def test_extract_urls_none(self, scanner):
        text = "No URLs here"
        urls = scanner._extract_urls(text)
        assert len(urls) == 0

