"""Unit tests for CaptionBuilder classes."""
import pytest
from datetime import datetime
from social.core.caption_builder import CaptionFormatter, VideoCaptionBuilder, ChannelCaptionBuilder, CaptionBuilder


class TestCaptionFormatter:
    """Tests for CaptionFormatter utility class."""
    
    def test_format_number_less_than_thousand(self):
        """Test formatting numbers less than 1000."""
        assert CaptionFormatter._format_number(0) == "0"
        assert CaptionFormatter._format_number(1) == "1"
        assert CaptionFormatter._format_number(99) == "99"
        assert CaptionFormatter._format_number(525) == "525"
        assert CaptionFormatter._format_number(999) == "999"
    
    def test_format_number_thousands(self):
        """Test formatting numbers in thousands (K)."""
        assert CaptionFormatter._format_number(1000) == "1K"
        assert CaptionFormatter._format_number(1500) == "1.5K"
        assert CaptionFormatter._format_number(16354) == "16.4K"
        assert CaptionFormatter._format_number(99900) == "99.9K"
        assert CaptionFormatter._format_number(100000) == "100K"
        assert CaptionFormatter._format_number(150000) == "150K"
        assert CaptionFormatter._format_number(999000) == "999K"
    
    def test_format_number_millions(self):
        """Test formatting numbers in millions (M)."""
        assert CaptionFormatter._format_number(1000000) == "1M"
        assert CaptionFormatter._format_number(1500000) == "1.5M"
        assert CaptionFormatter._format_number(15000000) == "15M"
        assert CaptionFormatter._format_number(100000000) == "100M"
        assert CaptionFormatter._format_number(150000000) == "150M"
    
    def test_format_number_removes_trailing_zero(self):
        """Test that .0 is removed from formatted numbers."""
        assert CaptionFormatter._format_number(5000) == "5K"
        assert CaptionFormatter._format_number(10000) == "10K"
        assert CaptionFormatter._format_number(2000000) == "2M"
        assert CaptionFormatter._format_number(10000000) == "10M"
        assert CaptionFormatter._format_number(5000000000) == "5B"
    
    def test_format_number_billions(self):
        """Test formatting numbers in billions (B)."""
        assert CaptionFormatter._format_number(1000000000) == "1B"
        assert CaptionFormatter._format_number(1456091000) == "1.5B"
        assert CaptionFormatter._format_number(15000000000) == "15B"
        assert CaptionFormatter._format_number(100000000000) == "100B"
        assert CaptionFormatter._format_number(150000000000) == "150B"


class TestVideoCaptionBuilder:
    """Tests for VideoCaptionBuilder class."""
    
    def test_build_caption_basic(self):
        """Test building a basic caption with all fields."""
        creation_date = datetime(2025, 11, 6, 18, 52)
        
        caption_builder = VideoCaptionBuilder(
            title="Test Video",
            video_url="https://youtube.com/watch?v=TEST123",
            creation_date=creation_date,
            channel_name="Test Channel",
            channel_url="https://youtube.com/@testchannel",
            views=16354,
            likes=525
        )
        
        caption = caption_builder.build_caption()
        
        # Verify caption contains all expected elements
        assert "[Test Video](https://youtube.com/watch?v=TEST123)" in caption
        assert "📅 06.11.2025 18:52" in caption
        assert "👁️ 16.4K" in caption
        assert "❤️ 525" in caption
        assert "👤 [Test Channel](https://youtube.com/@testchannel)" in caption
    
    def test_build_caption_without_stats(self):
        """Test building caption without views and likes."""
        creation_date = datetime(2025, 11, 6, 18, 52)
        
        caption_builder = VideoCaptionBuilder(
            title="Test Video",
            video_url="https://youtube.com/watch?v=TEST123",
            creation_date=creation_date,
            channel_name="Test Channel",
            channel_url="https://youtube.com/@testchannel",
            views=None,
            likes=None
        )
        
        caption = caption_builder.build_caption()
        
        # Verify caption doesn't contain stats
        assert "👁️" not in caption
        assert "❤️" not in caption
        assert "[Test Video]" in caption
        assert "📅 06.11.2025 18:52" in caption
        assert "👤 [Test Channel]" in caption
    
    def test_build_caption_with_only_views(self):
        """Test building caption with only views (no likes)."""
        creation_date = datetime(2025, 11, 6, 18, 52)
        
        caption_builder = VideoCaptionBuilder(
            title="Test Video",
            video_url="https://youtube.com/watch?v=TEST123",
            creation_date=creation_date,
            channel_name="Test Channel",
            channel_url="https://youtube.com/@testchannel",
            views=16354,
            likes=None
        )
        
        caption = caption_builder.build_caption()
        
        # Verify caption contains views but not likes
        assert "👁️ 16.4K" in caption
        assert "❤️" not in caption
    
    def test_build_caption_with_only_likes(self):
        """Test building caption with only likes (no views)."""
        creation_date = datetime(2025, 11, 6, 18, 52)
        
        caption_builder = VideoCaptionBuilder(
            title="Test Video",
            video_url="https://youtube.com/watch?v=TEST123",
            creation_date=creation_date,
            channel_name="Test Channel",
            channel_url="https://youtube.com/@testchannel",
            views=None,
            likes=525
        )
        
        caption = caption_builder.build_caption()
        
        # Verify caption contains likes but not views
        assert "❤️ 525" in caption
        assert "👁️" not in caption
    
    def test_build_caption_with_large_numbers(self):
        """Test building caption with large view and like counts."""
        creation_date = datetime(2025, 11, 6, 18, 52)
        
        caption_builder = VideoCaptionBuilder(
            title="Viral Video",
            video_url="https://youtube.com/watch?v=VIRAL123",
            creation_date=creation_date,
            channel_name="Popular Channel",
            channel_url="https://youtube.com/@popular",
            views=15000000,
            likes=500000
        )
        
        caption = caption_builder.build_caption()
        
        # Verify large numbers are formatted correctly
        assert "👁️ 15M" in caption
        assert "❤️ 500K" in caption


class TestChannelCaptionBuilder:
    """Tests for ChannelCaptionBuilder class."""
    
    def test_build_caption_complete_channel(self):
        """Test building caption with all channel fields."""
        caption_builder = ChannelCaptionBuilder(
            channel_name="Test Channel",
            channel_url="https://youtube.com/@testchannel",
            username="testchannel",
            channel_follower_count=2380000,
            video_count=7549,
            view_count=1456091000,
            location="US",
            channel_created=1322247948,  # 2011-11-25
            description="This is a test channel with a nice description about content.",
            avatar="https://yt3.ggpht.com/example.jpg"
        )
        
        caption = caption_builder.build_caption()
        
        # Verify all fields are present
        assert "📺 **[testchannel]" in caption  # username sin @ extra
        assert "👥 2.4M subscribers" in caption
        assert "📹 7.5K videos" in caption
        assert "👁️ 1.5B views" in caption
        assert "📍 US" in caption
        assert "📅 Created: 25.11.2011" in caption  # formato completo dd.mm.yyyy
        assert "📝 This is a test channel" in caption
    
    def test_build_caption_minimal_channel(self):
        """Test building caption with only required channel fields."""
        caption_builder = ChannelCaptionBuilder(
            channel_name="Minimal Channel",
            channel_url="https://youtube.com/@minimal"
        )
        
        caption = caption_builder.build_caption()
        
        # Verify only required fields
        assert "📺 **[Minimal Channel]" in caption
        assert "👥" not in caption
        assert "📹" not in caption
        assert "👁️" not in caption
        assert "📍" not in caption
        assert "📅" not in caption
        assert "📝" not in caption
    
    def test_build_caption_with_username(self):
        """Test that username is displayed with @ when available."""
        caption_builder = ChannelCaptionBuilder(
            channel_name="Channel Name",
            channel_url="https://youtube.com/@channelhandle",
            username="channelhandle"
        )
        
        caption = caption_builder.build_caption()
        
        # Verify username is used (sin @ extra)
        assert "[channelhandle]" in caption
        assert "[Channel Name]" not in caption
    
    def test_build_caption_without_username(self):
        """Test that channel name is displayed when username not available."""
        caption_builder = ChannelCaptionBuilder(
            channel_name="Channel Name",
            channel_url="https://youtube.com/channel/UC123456"
        )
        
        caption = caption_builder.build_caption()
        
        # Verify channel name is used
        assert "[Channel Name]" in caption
    
    def test_build_caption_truncates_long_description(self):
        """Test that long descriptions are truncated."""
        long_description = "A" * 300  # Very long description
        
        caption_builder = ChannelCaptionBuilder(
            channel_name="Test Channel",
            channel_url="https://youtube.com/@test",
            description=long_description
        )
        
        caption = caption_builder.build_caption()
        
        # Verify description is truncated
        assert len(caption) < len(long_description) + 100
        assert "..." in caption
        assert "📝" in caption
    
    def test_build_caption_channel_with_stats_only(self):
        """Test channel caption with only statistics."""
        caption_builder = ChannelCaptionBuilder(
            channel_name="Stats Channel",
            channel_url="https://youtube.com/@stats",
            channel_follower_count=5000,
            video_count=120,
            view_count=1000000
        )
        
        caption = caption_builder.build_caption()
        
        # Verify stats are present
        assert "👥 5K subscribers" in caption
        assert "📹 120 videos" in caption
        assert "👁️ 1M views" in caption
        assert " | " in caption  # Stats should be separated
    
    def test_build_caption_channel_with_metadata_only(self):
        """Test channel caption with only metadata (location, creation date)."""
        caption_builder = ChannelCaptionBuilder(
            channel_name="Metadata Channel",
            channel_url="https://youtube.com/@metadata",
            location="GE",
            channel_created=1322247948
        )
        
        caption = caption_builder.build_caption()
        
        # Verify metadata is present
        assert "📍 GE" in caption
        assert "📅 Created: 25.11.2011" in caption
        assert " | " in caption  # Metadata should be separated


class TestBackwardsCompatibility:
    """Tests for backwards compatibility alias."""
    
    def test_caption_builder_alias(self):
        """Test that CaptionBuilder is an alias for VideoCaptionBuilder."""
        assert CaptionBuilder is VideoCaptionBuilder
    
    def test_can_use_old_name(self):
        """Test that old code using CaptionBuilder still works."""
        creation_date = datetime(2025, 11, 6, 18, 52)
        
        caption_builder = CaptionBuilder(
            title="Test Video",
            video_url="https://youtube.com/watch?v=TEST123",
            creation_date=creation_date,
            channel_name="Test Channel",
            channel_url="https://youtube.com/@testchannel",
            views=16354,
            likes=525
        )
        
        caption = caption_builder.build_caption()
        
        # Verify it works as before
        assert "[Test Video]" in caption
        assert "👁️ 16.4K" in caption
        assert "❤️ 525" in caption
 
