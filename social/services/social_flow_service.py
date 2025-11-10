from pathlib import Path
from typing import Optional, Dict, Any, List
from telethon import TelegramClient
import asyncio

from social.config import Config
from social.logger import get_logger
from social.services.YT_Downloader import YT_Downloader
from social.services.telegram_uploader import TelegramUploderService, UploadOptions
from social.platforms.base import Platform
from social.core.entity_resolver import EntityResolverFactory, ContentType

logger = get_logger(__name__)


class SocialFlowService:
    """
    Service that orchestrates the complete flow:
    1. Download video using yt-dlp
    2. Create caption from metadata using platform-specific logic
    3. Upload to Telegram with the caption
    """
    
    def __init__(self, config: Config):
        """
        Initialize the social flow service.
        
        Args:
            config: Config instance with platform and entity configurations
        """
        self.config = config
        self.downloader = YT_Downloader(config)
        config.load_entities()
        
        # Initialize entity resolver factory
        self.entity_resolver_factory = EntityResolverFactory(config.ENTITIES_FILE)
    
    def _get_downloaded_file_path(self, info_dict: Dict[str, Any], platform: Platform) -> Optional[Path]:
        """
        Get the path of the downloaded file from info_dict.
        
        Args:
            info_dict: Info dictionary from yt-dlp
            platform: Platform instance used for download
            
        Returns:
            Path to the downloaded file or None if not found
        """
        # Try to get filepath from info_dict (yt-dlp sets this after download)
        filepath = info_dict.get('filepath')
        
        if filepath:
            file_path = Path(filepath)
            if file_path.exists():
                return file_path
        
        # Try requested_downloads (for merged formats)
        requested_downloads = info_dict.get('requested_downloads', [])
        if requested_downloads:
            filepath = requested_downloads[0].get('filepath')
            if filepath:
                file_path = Path(filepath)
                if file_path.exists():
                    return file_path
        
        # If filepath not in info_dict, construct it from id and ext
        # yt-dlp uses pattern: %(id)s.%(ext)s by default
        video_id = info_dict.get('id') or info_dict.get('display_id')
        
        if video_id:
            download_dir = platform.get_download_dir()
            # First, try to find any file with the video id (handles different extensions)
            matching_files = list(download_dir.glob(f"{video_id}.*"))
            # Filter out info.json and other metadata files, keep only video files
            video_files = [f for f in matching_files if f.is_file() and f.suffix in ['.mp4', '.mkv', '.webm', '.flv', '.avi', '.mov', '.ts']]
            if video_files:
                # Return the most recently modified file (likely the downloaded video)
                return max(video_files, key=lambda p: p.stat().st_mtime)
            
            # Fallback: try with expected extension from info_dict
            ext = info_dict.get('ext') or 'mp4'
            file_path = download_dir / f"{video_id}.{ext}"
            if file_path.exists():
                return file_path
        
        logger.warning(f"Could not find downloaded file for video ID: {video_id}")
        return None
    
    def _determine_content_type(self, url: str, info_dict: Dict[str, Any], platform: Platform) -> ContentType:
        """
        Determine content type based on URL, info_dict, and platform.
        
        Args:
            url: Video URL
            info_dict: Info dictionary from yt-dlp
            platform: Platform instance
            
        Returns:
            ContentType enum value
        """
        # Check for shorts/clips indicators
        url_lower = url.lower()
        
        # YouTube shorts
        if '/shorts/' in url_lower:
            return ContentType.SHORT
        
        # VK clips
        if 'vk.com' in url_lower and '/clip' in url_lower:
            return ContentType.CLIP
        
        # TikTok is always short-form
        if 'tiktok.com' in url_lower:
            return ContentType.SHORT
        
        # Platform-specific short detection
        if hasattr(platform, '_is_short') and platform._is_short(info_dict):
            return ContentType.SHORT
        
        return ContentType.VIDEO
    
    async def process_video(
        self,
        url: str,
        platform: Optional[Platform] = None,
        telegram_client: Optional[TelegramClient] = None,
        bot_client: Optional[TelegramClient] = None,
        entity_id: Optional[int] = None,
        topic_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Complete flow: download video, create caption, and upload to Telegram.
        
        Args:
            url: URL of the video to download
            platform: Optional Platform instance (will be auto-detected if not provided)
            telegram_client: TelegramClient for uploading
            bot_client: Bot TelegramClient for uploading
            entity_id: Telegram entity (group/channel) ID (will use config if not provided)
            topic_id: Telegram topic ID for forum groups (will use config if not provided)
            
        Returns:
            Dict with result information including:
            - success: bool
            - video_path: Path to downloaded video
            - caption: Generated caption
            - platform_name: Detected platform name
            - message: Result message
        """
        try:
            # Step 1: Download video
            logger.info(f"Starting download process for: {url}")
            info_dict = self.downloader.download(url, platform=platform, donwload=True)
            
            # Get platform (either provided or detected)
            if platform is None:
                extractor = info_dict.get('extractor', '').lower()
                platform = self.downloader._get_platform_for_extractor(extractor)
            
            platform_name = platform.name
            logger.info(f"Using platform: {platform_name}")
            
            # Step 2: Get downloaded file path
            video_path = self._get_downloaded_file_path(info_dict, platform)
            if not video_path:
                raise FileNotFoundError(f"Downloaded video file not found for {url}")
            
            logger.info(f"Downloaded video: {video_path}")
            
            # Step 3: Create caption using platform-specific logic
            caption_builder = platform.create_caption(info_dict)
            caption = caption_builder.build_caption()
            logger.info(f"Generated caption: {caption[:100]}...")
            
            # Step 4: Resolve entity and topic using entity resolver
            if entity_id is None or topic_id is None:
                # Determine content type
                content_type = self._determine_content_type(url, info_dict, platform)
                logger.debug(f"Determined content type: {content_type.value}")
                
                # Get resolver for platform
                resolver = self.entity_resolver_factory.get_resolver(platform_name)
                
                # Resolve entity and topic
                resolved_entity_id, resolved_topic_id = resolver.resolve(content_type)
                
                if entity_id is None:
                    entity_id = resolved_entity_id
                if topic_id is None:
                    topic_id = resolved_topic_id
            
            # Step 5: Upload to Telegram (if clients provided)
            if telegram_client and bot_client and entity_id:
                logger.info(f"Uploading to Telegram: entity={entity_id}, topic={topic_id}")
                upload_options: UploadOptions = {
                    'video': str(video_path),
                    'entity': entity_id,
                    'reply_to': topic_id or 1,
                    'client': telegram_client,
                    'bot_client': bot_client,
                    'caption': caption
                }
                await TelegramUploderService.upload(upload_options)
                logger.info("Video uploaded successfully to Telegram")
            else:
                logger.info("Telegram clients not provided, skipping upload")
            
            return {
                'success': True,
                'video_path': video_path,
                'caption': caption,
                'platform_name': platform_name,
                'message': f"Video processed successfully: {video_path.name}"
            }
            
        except Exception as e:
            logger.error(f"Error processing video {url}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to process video: {e}"
            }
    
    async def process_videos_batch(
        self,
        urls: List[str],
        telegram_client: Optional[TelegramClient] = None,
        bot_client: Optional[TelegramClient] = None,
        entity_id: Optional[int] = None,
        topic_id: Optional[int] = None,
        max_parallel: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple videos with parallel downloads and sequential uploads.
        
        Args:
            urls: List of video URLs to process
            telegram_client: Telegram client for uploading (optional)
            bot_client: Bot client for uploading (optional)
            entity_id: Target Telegram entity ID (optional, auto-resolved if not provided)
            topic_id: Target topic ID (optional, auto-resolved if not provided)
            max_parallel: Max parallel downloads (default from config)
        
        Returns:
            List of results for each URL
        """
        if max_parallel is None:
            max_parallel = self.config.MAX_PARALLEL_DOWNLOADS
        
        logger.info(f"Processing {len(urls)} videos with max {max_parallel} parallel downloads")
        
        # Step 1: Download all videos in parallel (limited by semaphore)
        semaphore = asyncio.Semaphore(max_parallel)
        download_tasks = []
        
        async def download_with_semaphore(url: str) -> Dict[str, Any]:
            async with semaphore:
                logger.info(f"Starting download: {url}")
                try:
                    # Download only (no upload)
                    result = await self.process_video(
                        url=url,
                        telegram_client=None,  # Don't upload yet
                        bot_client=None,
                        entity_id=entity_id,
                        topic_id=topic_id
                    )
                    logger.info(f"Download completed: {url}")
                    return result
                except Exception as e:
                    logger.error(f"Download failed for {url}: {e}", exc_info=True)
                    return {
                        'success': False,
                        'url': url,
                        'error': str(e),
                        'message': f"Download failed: {e}"
                    }
        
        # Create download tasks for all URLs
        for url in urls:
            task = download_with_semaphore(url)
            download_tasks.append(task)
        
        # Execute all downloads in parallel (limited by semaphore)
        download_results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # Step 2: Upload videos sequentially (one by one)
        final_results = []
        successful_downloads = [r for r in download_results if isinstance(r, dict) and r.get('success')]
        
        logger.info(f"Downloaded {len(successful_downloads)}/{len(urls)} videos successfully")
        
        if telegram_client and bot_client:
            logger.info("Starting sequential uploads...")
            for i, result in enumerate(successful_downloads, 1):
                try:
                    video_path = result.get('video_path')
                    caption = result.get('caption', '')
                    platform_name = result.get('platform_name', '')
                    
                    if not video_path or not video_path.exists():
                        logger.warning(f"Video file not found for upload: {video_path}")
                        result['upload_status'] = 'failed'
                        result['upload_error'] = 'Video file not found'
                        final_results.append(result)
                        continue
                    
                    logger.info(f"Uploading {i}/{len(successful_downloads)}: {video_path.name}")
                    
                    # Determine entity_id and topic_id if not provided
                    upload_entity_id = entity_id
                    upload_topic_id = topic_id
                    
                    if upload_entity_id is None or upload_topic_id is None:
                        # Use the resolved entity from download result
                        resolver = self.entity_resolver_factory.get_resolver(platform_name)
                        content_type = result.get('content_type', ContentType.VIDEO)
                        resolved_entity_id, resolved_topic_id = resolver.resolve(content_type)
                        
                        if upload_entity_id is None:
                            upload_entity_id = resolved_entity_id
                        if upload_topic_id is None:
                            upload_topic_id = resolved_topic_id
                    
                    # Upload to Telegram
                    upload_options: UploadOptions = {
                        'video': str(video_path),
                        'entity': upload_entity_id,
                        'reply_to': upload_topic_id or 1,
                        'client': telegram_client,
                        'bot_client': bot_client,
                        'caption': caption
                    }
                    await TelegramUploderService.upload(upload_options)
                    
                    result['upload_status'] = 'success'
                    logger.info(f"Upload completed: {video_path.name}")
                    
                except Exception as e:
                    logger.error(f"Upload failed for {result.get('video_path')}: {e}", exc_info=True)
                    result['upload_status'] = 'failed'
                    result['upload_error'] = str(e)
                
                final_results.append(result)
        else:
            logger.info("Telegram clients not provided, skipping uploads")
            final_results = successful_downloads
        
        # Add failed downloads to final results
        failed_downloads = [r for r in download_results if not isinstance(r, dict) or not r.get('success')]
        final_results.extend(failed_downloads)
        
        logger.info(f"Batch processing completed: {len(final_results)} total results")
        return final_results

