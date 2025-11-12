"""Tests for RecoveryMetadataParser."""
import pytest
from datetime import datetime
from social.services.recovery_metadata_parser import RecoveryMetadataParser


class TestRecoveryMetadataParser:
    
    def test_parse_youtube_caption(self):
        caption = """#I'mOld   zD2tyJysP8U 720p  --.mp4

👀 Channel: Jemima Avison (https://www.youtube.com/channel/UCnwewRbbRB05Z34foKOWJuA)
📅 21.06.2025

https://www.youtube.com/shorts/zD2tyJysP8U"""
        
        metadata = RecoveryMetadataParser.parse(caption)
        
        assert metadata['title'] == "I'mOld"
        assert metadata['channel_name'] == 'Jemima Avison'
        assert metadata['channel_url'] == 'https://www.youtube.com/channel/UCnwewRbbRB05Z34foKOWJuA'
        assert metadata['video_url'] == 'https://www.youtube.com/shorts/zD2tyJysP8U'
        assert metadata['upload_date'] == datetime(2025, 6, 21)
    
    def test_parse_caption_with_all_fields(self):
        caption = """#TestVideo abc123 720p

👀 Channel: Test Channel (https://www.youtube.com/channel/UCtest)
📅 15.03.2025

https://www.youtube.com/watch?v=abc123"""
        
        metadata = RecoveryMetadataParser.parse(caption)
        
        assert metadata['title'] == 'TestVideo'
        assert metadata['channel_name'] == 'Test Channel'
        assert metadata['upload_date'] == datetime(2025, 3, 15)
    
    def test_parse_empty_caption_raises_error(self):
        with pytest.raises(ValueError, match="Caption is empty"):
            RecoveryMetadataParser.parse("")
    
    def test_parse_caption_missing_fields(self):
        caption = """#SimpleVideo abc123 720p

https://www.youtube.com/watch?v=abc123"""
        
        metadata = RecoveryMetadataParser.parse(caption)
        
        assert metadata['title'] == 'SimpleVideo'
        assert metadata['video_url'] == 'https://www.youtube.com/watch?v=abc123'
        assert metadata['channel_name'] is None
        assert metadata['upload_date'] is None
    
    def test_parse_hashtag_with_apostrophe(self):
        caption = """#I'mOld abc123 720p

https://www.youtube.com/watch?v=abc123"""
        
        metadata = RecoveryMetadataParser.parse(caption)
        assert metadata['title'] == "I'mOld"
    
    def test_parse_hashtag_with_underscore(self):
        caption = """#Test_Tag abc123 720p

https://www.youtube.com/watch?v=abc123"""
        
        metadata = RecoveryMetadataParser.parse(caption)
        assert metadata['title'] == "Test Tag"

