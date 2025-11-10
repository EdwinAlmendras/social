"""Upload strategies for different upload modes."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from telethon import TelegramClient

from social.services.social_flow_service import SocialFlowService
from social.services.channel_operations_service import ChannelOperationsService
from social.services.url_id_extractor import URLIDExtractor
from social.config import Config
from social.logger import get_logger

logger = get_logger(__name__)


class UploadStrategy(ABC):
    """Abstract base class for upload strategies."""
    
    @abstractmethod
    async def execute(
        self,
        urls: List[str],
        service: SocialFlowService,
        telegram_client: TelegramClient,
        bot_client: TelegramClient,
        config: Config,
        quiet: bool = False,
        max_parallel: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute the upload strategy.
        
        Args:
            urls: List of URLs to process
            service: SocialFlowService instance
            telegram_client: Telegram client for user
            bot_client: Telegram client for bot
            config: Config instance
            quiet: Whether to suppress output
            max_parallel: Max parallel downloads (optional)
            
        Returns:
            Dictionary with execution results
        """
        pass


class StandardUploadStrategy(UploadStrategy):
    """
    Standard upload strategy.
    
    Uses entity resolver to determine target group/topic for each video.
    Supports parallel downloads for multiple URLs.
    """
    
    async def execute(
        self,
        urls: List[str],
        service: SocialFlowService,
        telegram_client: TelegramClient,
        bot_client: TelegramClient,
        config: Config,
        quiet: bool = False,
        max_parallel: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute standard upload strategy."""
        logger.info(f"Executing standard upload strategy for {len(urls)} URLs")
        
        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        # Use batch processing if multiple URLs
        if len(urls) > 1:
            logger.info(f"Using batch processing with parallel downloads for {len(urls)} URLs")
            batch_results = await service.process_videos_batch(
                urls=urls,
                telegram_client=telegram_client,
                bot_client=bot_client,
                max_parallel=max_parallel
            )
            
            for result in batch_results:
                if result.get('success') and result.get('upload_status') == 'success':
                    results['success_count'] += 1
                else:
                    results['error_count'] += 1
                    error_msg = result.get('error') or result.get('upload_error', 'Unknown error')
                    results['errors'].append(error_msg)
            
            return results
        
        # Single URL processing (original behavior)
        for i, url in enumerate(urls, 1):
            try:
                logger.debug(f"Processing URL {i}/{len(urls)}: {url}")
                
                result = await service.process_video(
                    url=url,
                    telegram_client=telegram_client,
                    bot_client=bot_client
                )
                
                if result['success']:
                    results['success_count'] += 1
                    logger.debug(f"Video uploaded successfully: {result.get('video_path')}")
                else:
                    results['error_count'] += 1
                    error_msg = result.get('error', 'Unknown error')
                    results['errors'].append({'url': url, 'error': error_msg})
                    logger.warning(f"Upload failed for {url}: {error_msg}")
                    
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append({'url': url, 'error': str(e)})
                logger.error(f"Exception processing {url}: {e}")
        
        logger.info(f"Standard upload complete: {results['success_count']} success, {results['error_count']} errors")
        return results


class ChannelUploadStrategy(UploadStrategy):
    """
    Channel upload strategy.
    
    Creates a new topic for the channel from first URL and uploads all videos there.
    Validates that all URLs are from the same platform (unless skip_validation=True).
    """
    
    def __init__(self, skip_validation: bool = False):
        """
        Initialize channel upload strategy.
        
        Args:
            skip_validation: If True, skip platform validation
        """
        self.skip_validation = skip_validation
    
    async def execute(
        self,
        urls: List[str],
        service: SocialFlowService,
        telegram_client: TelegramClient,
        bot_client: TelegramClient,
        config: Config,
        quiet: bool = False,
        max_parallel: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute channel upload strategy."""
        logger.info(f"Executing channel upload strategy for {len(urls)} URLs")
        
        if not urls:
            raise ValueError("No URLs provided")
        
        # Step 1: Validate all URLs are from same platform (unless skipped)
        if not self.skip_validation:
            logger.debug("Validating URLs are from same platform")
            self._validate_same_platform(urls)
        else:
            logger.debug("Platform validation skipped")
        
        # Step 2: Setup channel topic from first URL
        first_url = urls[0]
        logger.info(f"Setting up channel topic from first URL: {first_url}")
        
        topic_setup = await self._setup_channel_topic(
            first_url,
            config,
            telegram_client
        )
        
        topic_id = topic_setup['topic_id']
        entity_id = topic_setup['entity_id']
        platform = topic_setup['platform']
        
        logger.info(f"Topic created. ID: {topic_id}, Platform: {platform}")
        
        # Step 3: Upload all videos to the created topic
        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': [],
            'topic_id': topic_id,
            'entity_id': entity_id,
            'platform': platform
        }
        
        # Use batch processing if multiple URLs
        if len(urls) > 1:
            logger.info(f"Using batch processing with parallel downloads for {len(urls)} URLs")
            batch_results = await service.process_videos_batch(
                urls=urls,
                telegram_client=telegram_client,
                bot_client=bot_client,
                entity_id=entity_id,
                topic_id=topic_id,
                max_parallel=max_parallel
            )
            
            for result in batch_results:
                if result.get('success') and result.get('upload_status') == 'success':
                    results['success_count'] += 1
                else:
                    results['error_count'] += 1
                    error_msg = result.get('error') or result.get('upload_error', 'Unknown error')
                    results['errors'].append(error_msg)
            
            logger.info(f"Channel upload complete: {results['success_count']} success, {results['error_count']} errors")
            return results
        
        # Single URL processing
        for i, url in enumerate(urls, 1):
            try:
                logger.debug(f"Processing URL {i}/{len(urls)}: {url}")
                
                result = await service.process_video(
                    url=url,
                    telegram_client=telegram_client,
                    bot_client=bot_client,
                    entity_id=entity_id,
                    topic_id=topic_id
                )
                
                if result['success']:
                    results['success_count'] += 1
                    logger.debug(f"Video uploaded to topic {topic_id}")
                else:
                    results['error_count'] += 1
                    error_msg = result.get('error', 'Unknown error')
                    results['errors'].append({'url': url, 'error': error_msg})
                    logger.warning(f"Upload failed for {url}: {error_msg}")
                    
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append({'url': url, 'error': str(e)})
                logger.error(f"Exception processing {url}: {e}")
        
        logger.info(f"Channel upload complete: {results['success_count']} success, {results['error_count']} errors")
        return results
    
    def _validate_same_platform(self, urls: List[str]) -> None:
        """
        Validate that all URLs are from the same platform.
        
        Args:
            urls: List of URLs to validate
            
        Raises:
            ValueError: If URLs are from different platforms
        """
        platforms = []
        
        for url in urls:
            platform = URLIDExtractor.detect_platform(url)
            if not platform:
                raise ValueError(f"Could not detect platform for URL: {url}")
            platforms.append(platform)
        
        unique_platforms = set(platforms)
        
        if len(unique_platforms) > 1:
            raise ValueError(
                f"All URLs must be from the same platform. "
                f"Found: {', '.join(unique_platforms)}. "
                f"Use --skip-validation to bypass this check."
            )
        
        logger.info(f"Platform validation passed: all URLs are from '{platforms[0]}'")
    
    async def _setup_channel_topic(
        self,
        url: str,
        config: Config,
        telegram_client: TelegramClient
    ) -> Dict[str, Any]:
        """
        Setup channel topic from URL.
        
        Args:
            url: URL to extract channel info from
            config: Config instance
            telegram_client: Telegram client
            
        Returns:
            Dictionary with topic_id, entity_id, and platform
            
        Raises:
            ValueError: If setup fails
        """
        # Initialize channel operations service
        channel_ops = ChannelOperationsService(config, telegram_client)
        
        # Get platform to determine entity_id
        platform_name = URLIDExtractor.detect_platform(url)
        if not platform_name:
            raise ValueError(f"Could not detect platform from URL: {url}")
        
        # Get entity_id from entities config
        config.load_entities()
        entities = config.ENTITIES
        
        platform_entity = entities.get(platform_name.lower())
        if not platform_entity:
            raise ValueError(f"No entity configuration found for platform: {platform_name}")
        
        entity_id = platform_entity['group_id']
        logger.debug(f"Using entity_id {entity_id} for platform {platform_name}")
        
        # Setup channel topic
        setup_result = await channel_ops.setup_channel_topic(url, entity_id)
        
        return {
            'topic_id': setup_result['topic_id'],
            'entity_id': entity_id,
            'platform': platform_name
        }


class UploadStrategyFactory:
    """Factory for creating upload strategies."""
    
    @staticmethod
    def create(use_channel_mode: bool, skip_validation: bool = False) -> UploadStrategy:
        """
        Create an upload strategy based on mode.
        
        Args:
            use_channel_mode: If True, create ChannelUploadStrategy
            skip_validation: If True, skip platform validation (only for channel mode)
            
        Returns:
            UploadStrategy instance
        """
        if use_channel_mode:
            logger.debug(f"Creating ChannelUploadStrategy (skip_validation={skip_validation})")
            return ChannelUploadStrategy(skip_validation=skip_validation)
        
        logger.debug("Creating StandardUploadStrategy")
        return StandardUploadStrategy()

