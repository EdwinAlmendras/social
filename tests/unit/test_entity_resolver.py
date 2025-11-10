"""Unit tests for Entity Resolver."""
import pytest
import json
import tempfile
from pathlib import Path

from social.core.entity_resolver import (
    ContentType,
    EntityConfig,
    EntityResolver,
    EntityResolverFactory
)


class TestEntityConfig:
    """Tests for EntityConfig class."""
    
    def test_get_topic_id_for_video(self):
        """Test getting topic ID for regular videos."""
        config = EntityConfig(
            group_id=-1001234567890,
            topics={"videos": 5, "shorts": 3}
        )
        
        topic_id = config.get_topic_id(ContentType.VIDEO)
        assert topic_id == 5
    
    def test_get_topic_id_for_short(self):
        """Test getting topic ID for shorts."""
        config = EntityConfig(
            group_id=-1001234567890,
            topics={"videos": 5, "shorts": 3}
        )
        
        topic_id = config.get_topic_id(ContentType.SHORT)
        assert topic_id == 3
    
    def test_get_topic_id_for_clip_maps_to_shorts(self):
        """Test that clips map to shorts topic."""
        config = EntityConfig(
            group_id=-1001234567890,
            topics={"videos": 5, "shorts": 3}
        )
        
        topic_id = config.get_topic_id(ContentType.CLIP)
        assert topic_id == 3  # Clips should map to shorts
    
    def test_get_topic_id_missing_topic(self):
        """Test getting topic ID when topic is not configured."""
        config = EntityConfig(
            group_id=-1001234567890,
            topics={"videos": 5}  # No shorts configured
        )
        
        topic_id = config.get_topic_id(ContentType.SHORT)
        assert topic_id is None


class TestEntityResolver:
    """Tests for EntityResolver class."""
    
    def test_resolve_with_config(self):
        """Test resolving entity and topic with configuration."""
        config = EntityConfig(
            group_id=-1001234567890,
            topics={"videos": 5, "shorts": 3}
        )
        resolver = EntityResolver(config)
        
        entity_id, topic_id = resolver.resolve(ContentType.VIDEO)
        assert entity_id == -1001234567890
        assert topic_id == 5
    
    def test_resolve_without_config(self):
        """Test resolving without configuration returns None."""
        resolver = EntityResolver(None)
        
        entity_id, topic_id = resolver.resolve(ContentType.VIDEO)
        assert entity_id is None
        assert topic_id is None
    
    def test_resolve_fallback_to_videos_topic(self):
        """Test fallback to 'videos' topic when content type not configured."""
        config = EntityConfig(
            group_id=-1001234567890,
            topics={"videos": 5}  # No shorts configured
        )
        resolver = EntityResolver(config)
        
        entity_id, topic_id = resolver.resolve(ContentType.SHORT)
        assert entity_id == -1001234567890
        assert topic_id == 5  # Should fallback to videos


class TestEntityResolverFactory:
    """Tests for EntityResolverFactory class."""
    
    def test_load_configs_from_file(self):
        """Test loading entity configurations from JSON file."""
        # Create temporary entities file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "youtube": {
                    "group_id": -1001234567890,
                    "topics": {"videos": 5, "shorts": 3}
                },
                "vk": {
                    "group_id": -1009876543210,
                    "topics": {"videos": 2, "shorts": 4}
                }
            }
            json.dump(config_data, f)
            temp_file = Path(f.name)
        
        try:
            factory = EntityResolverFactory(temp_file)
            
            # Test YouTube resolver
            youtube_resolver = factory.get_resolver("youtube")
            entity_id, topic_id = youtube_resolver.resolve(ContentType.VIDEO)
            assert entity_id == -1001234567890
            assert topic_id == 5
            
            # Test VK resolver
            vk_resolver = factory.get_resolver("vk")
            entity_id, topic_id = vk_resolver.resolve(ContentType.SHORT)
            assert entity_id == -1009876543210
            assert topic_id == 4
        
        finally:
            temp_file.unlink()
    
    def test_get_resolver_for_unconfigured_platform(self):
        """Test getting resolver for platform without configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {"youtube": {"group_id": -1001234567890, "topics": {"videos": 5}}}
            json.dump(config_data, f)
            temp_file = Path(f.name)
        
        try:
            factory = EntityResolverFactory(temp_file)
            
            # Request resolver for unconfigured platform
            tiktok_resolver = factory.get_resolver("tiktok")
            entity_id, topic_id = tiktok_resolver.resolve(ContentType.SHORT)
            
            # Should return None for unconfigured platform
            assert entity_id is None
            assert topic_id is None
        
        finally:
            temp_file.unlink()
    
    def test_load_configs_from_nonexistent_file(self):
        """Test loading configs from file that doesn't exist."""
        nonexistent_file = Path("/path/that/does/not/exist.json")
        factory = EntityResolverFactory(nonexistent_file)
        
        # Should not raise error, but resolver should return None
        resolver = factory.get_resolver("youtube")
        entity_id, topic_id = resolver.resolve(ContentType.VIDEO)
        assert entity_id is None
        assert topic_id is None

