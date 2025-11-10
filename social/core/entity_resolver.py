"""Entity resolver for Telegram upload destinations.

This module provides a clean abstraction for resolving Telegram entity_id and topic_id
based on platform and content type, following SOLID principles.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import json

from social.logger import get_logger

logger = get_logger(__name__)


class ContentType(Enum):
    """Content type classification."""
    VIDEO = "video"
    SHORT = "short"
    CLIP = "clip"
    

class EntityConfig:
    """Configuration for a platform's entity and topics."""
    
    def __init__(self, group_id: int, topics: Dict[str, int]):
        """
        Initialize entity configuration.
        
        Args:
            group_id: Telegram group/channel ID
            topics: Dictionary mapping content types to topic IDs
        """
        self.group_id = group_id
        self.topics = topics
    
    def get_topic_id(self, content_type: ContentType) -> Optional[int]:
        """
        Get topic ID for a content type.
        
        Args:
            content_type: Type of content
            
        Returns:
            Topic ID or None if not configured
        """
        # Map content type to topic key
        type_mapping = {
            ContentType.VIDEO: "videos",
            ContentType.SHORT: "shorts",
            ContentType.CLIP: "shorts",  # Clips go to shorts topic
        }
        
        topic_key = type_mapping.get(content_type, "videos")
        return self.topics.get(topic_key)


class IEntityResolver(ABC):
    """Interface for entity resolution."""
    
    @abstractmethod
    def resolve(self, content_type: ContentType) -> Tuple[Optional[int], Optional[int]]:
        """
        Resolve entity_id and topic_id for a content type.
        
        Args:
            content_type: Type of content to resolve
            
        Returns:
            Tuple of (entity_id, topic_id) or (None, None) if not configured
        """
        pass


class EntityResolver(IEntityResolver):
    """Default entity resolver implementation."""
    
    def __init__(self, entity_config: Optional[EntityConfig]):
        """
        Initialize resolver with entity configuration.
        
        Args:
            entity_config: Configuration for this entity, or None
        """
        self.entity_config = entity_config
    
    def resolve(self, content_type: ContentType) -> Tuple[Optional[int], Optional[int]]:
        """
        Resolve entity_id and topic_id for a content type.
        
        Args:
            content_type: Type of content to resolve
            
        Returns:
            Tuple of (entity_id, topic_id) or (None, None) if not configured
        """
        if not self.entity_config:
            logger.warning("No entity configuration available")
            return None, None
        
        entity_id = self.entity_config.group_id
        topic_id = self.entity_config.get_topic_id(content_type)
        
        if topic_id is None:
            logger.warning(f"No topic configured for content type: {content_type.value}")
            # Fallback to default topic (1) or first available topic
            topic_id = self.entity_config.topics.get("videos", 1)
        
        logger.debug(f"Resolved entity_id={entity_id}, topic_id={topic_id} for {content_type.value}")
        return entity_id, topic_id


class EntityResolverFactory:
    """Factory for creating entity resolvers per platform."""
    
    def __init__(self, entities_file: Path):
        """
        Initialize factory with entities configuration file.
        
        Args:
            entities_file: Path to entities.json configuration file
        """
        self.entities_file = entities_file
        self._configs: Dict[str, EntityConfig] = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load entity configurations from file."""
        if not self.entities_file.exists():
            logger.warning(f"Entities file not found: {self.entities_file}")
            return
        
        try:
            with open(self.entities_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for platform_name, config_data in data.items():
                group_id = config_data.get('group_id')
                topics = config_data.get('topics', {})
                
                if group_id:
                    self._configs[platform_name] = EntityConfig(group_id, topics)
                    logger.debug(f"Loaded entity config for platform: {platform_name}")
        
        except Exception as e:
            logger.error(f"Error loading entities configuration: {e}")
    
    def get_resolver(self, platform_name: str) -> IEntityResolver:
        """
        Get entity resolver for a platform.
        
        Args:
            platform_name: Name of the platform (e.g., 'youtube', 'vk')
            
        Returns:
            Entity resolver for the platform
        """
        entity_config = self._configs.get(platform_name.lower())
        
        if not entity_config:
            logger.warning(f"No entity configuration found for platform: {platform_name}")
        
        return EntityResolver(entity_config)
    
    def reload(self):
        """Reload configurations from file."""
        self._configs.clear()
        self._load_configs()

