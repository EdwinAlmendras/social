from pathlib import Path
from typing import Optional, Dict, Any, List
from telethon import TelegramClient
import asyncio
from collections import deque

from social.config import Config
from social.logger import get_logger
from social.services.YT_Downloader import YT_Downloader
from social.services.telegram_uploader import TelegramUploderService, UploadOptions
from social.services.video_recovery_service import VideoRecoveryService
from social.services.video_database import VideoDatabaseService
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
    
    def __init__(self, config: Config, telegram_client: Optional[TelegramClient] = None, db_service: Optional[VideoDatabaseService] = None):
        """
        Initialize the social flow service.
        
        Args:
            config: Config instance with platform and entity configurations
            telegram_client: Optional TelegramClient for video recovery
            db_service: Optional VideoDatabaseService for duplicate checking
        """
        self.config = config
        self.downloader = YT_Downloader(config)
        config.load_entities()
        
        # Initialize entity resolver factory
        self.entity_resolver_factory = EntityResolverFactory(config.ENTITIES_FILE)
        
        # Initialize recovery service if telegram client provided
        self.recovery_service = VideoRecoveryService(config, telegram_client) if telegram_client else None
        
        # Database service for duplicate checking
        self.db_service = db_service
    
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
    
    async def _download_video_async(self, url: str, platform: Optional[Platform] = None) -> Dict[str, Any]:
        """Download video asynchronously without blocking the event loop."""
        loop = asyncio.get_event_loop()
        info_dict = await loop.run_in_executor(
            None,
            lambda: self.downloader.download(url, platform=platform, donwload=True)
        )
        return info_dict

    async def process_video(
        self,
        url: str,
        platform: Optional[Platform] = None,
        telegram_client: Optional[TelegramClient] = None,
        bot_client: Optional[TelegramClient] = None,
        entity_id: Optional[int] = None,
        topic_id: Optional[int] = None,
        enable_recovery: bool = True,
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
            enable_recovery: Try recovery bot if download fails (default: True)
            
        Returns:
            Dict with result information including:
            - success: bool
            - video_path: Path to downloaded video
            - caption: Generated caption
            - platform_name: Detected platform name
            - message: Result message
            - recovered: bool (True if video was recovered)
        """
        recovered = False
        try:
            # Check for duplicates before downloading
            if self.db_service and self.db_service.is_duplicate(url):
                from social.services.url_id_extractor import URLIDExtractor
                video_id = URLIDExtractor.extract_id(url)
                logger.info(f"Duplicate detected: {video_id}, skipping download")
                return {
                    'success': False,
                    'url': url,
                    'error': 'Duplicate video',
                    'message': f"Video {video_id} already exists in database",
                    'duplicate': True
                }
            
            # Step 1: Download video
            logger.info(f"Starting download process for: {url}")
            info_dict = await self._download_video_async(url, platform=platform)
            
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
                'message': f"Video processed successfully: {video_path.name}",
                'recovered': recovered
            }
            
        except Exception as e:
            logger.error(f"Error processing video {url}: {e}", exc_info=True)
            
            # Try recovery if enabled and available
            if enable_recovery and self.recovery_service:
                logger.info(f"Download failed, attempting recovery for: {url}")
                try:
                    recovery_result = await self.recovery_service.recover_video(url, error_message=str(e))
                    
                    if recovery_result['success']:
                        logger.info(f"Video recovered successfully: {url}")
                        recovered = True
                        video_path = recovery_result['video_path']
                        caption = recovery_result['caption']
                        
                        # Resolve entity and topic if not provided
                        if entity_id is None or topic_id is None:
                            # Assume it's a short/clip since it was deleted
                            content_type = ContentType.SHORT
                            logger.debug(f"Recovered video assumed as: {content_type.value}")
                            
                            # Detect platform from URL
                            from social.services.url_id_extractor import URLIDExtractor
                            platform_name = URLIDExtractor.detect_platform(url) or 'youtube'
                            
                            resolver = self.entity_resolver_factory.get_resolver(platform_name)
                            resolved_entity_id, resolved_topic_id = resolver.resolve(content_type)
                            
                            if entity_id is None:
                                entity_id = resolved_entity_id
                            if topic_id is None:
                                topic_id = resolved_topic_id
                            
                            logger.info(f"Resolved upload target: entity={entity_id}, topic={topic_id}")
                        
                        # Upload recovered video if clients provided
                        if telegram_client and bot_client and entity_id:
                            logger.info(f"Uploading recovered video to Telegram")
                            upload_options: UploadOptions = {
                                'video': str(video_path),
                                'entity': entity_id,
                                'reply_to': topic_id or 1,
                                'client': telegram_client,
                                'bot_client': bot_client,
                                'caption': caption
                            }
                            await TelegramUploderService.upload(upload_options)
                            logger.info("Recovered video uploaded successfully to Telegram")
                        
                        return {
                            'success': True,
                            'video_path': video_path,
                            'caption': caption,
                            'platform_name': 'recovered',
                            'message': f"Video recovered and uploaded: {video_path.name}",
                            'recovered': True
                        }
                    else:
                        logger.warning(f"Recovery failed: {recovery_result.get('error')}")
                
                except Exception as recovery_error:
                    logger.error(f"Recovery attempt failed: {recovery_error}", exc_info=True)
            
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to process video: {e}",
                'recovered': False
            }
    
    async def _download_and_prepare(
        self,
        url: str,
        platform: Optional[Platform],
        entity_id: Optional[int],
        topic_id: Optional[int]
    ) -> Dict[str, Any]:
        """Download video and prepare metadata without uploading."""
        try:
            logger.info(f"Starting download: {url}")
            info_dict = await self._download_video_async(url, platform=platform)
            
            if platform is None:
                extractor = info_dict.get('extractor', '').lower()
                platform = self.downloader._get_platform_for_extractor(extractor)
            
            platform_name = platform.name
            video_path = self._get_downloaded_file_path(info_dict, platform)
            
            if not video_path:
                raise FileNotFoundError(f"Downloaded video file not found for {url}")
            
            caption_builder = platform.create_caption(info_dict)
            caption = caption_builder.build_caption()
            
            if entity_id is None or topic_id is None:
                content_type = self._determine_content_type(url, info_dict, platform)
                resolver = self.entity_resolver_factory.get_resolver(platform_name)
                resolved_entity_id, resolved_topic_id = resolver.resolve(content_type)
                
                if entity_id is None:
                    entity_id = resolved_entity_id
                if topic_id is None:
                    topic_id = resolved_topic_id
            
            logger.info(f"Download completed: {url}")
            return {
                'success': True,
                'url': url,
                'video_path': video_path,
                'caption': caption,
                'platform_name': platform_name,
                'entity_id': entity_id,
                'topic_id': topic_id,
                'content_type': self._determine_content_type(url, info_dict, platform)
            }
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}", exc_info=True)
            return {
                'success': False,
                'url': url,
                'error': str(e),
                'message': f"Download failed: {e}"
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
        """Process videos with pipeline: parallel downloads (max 5) + sequential uploads."""
        if max_parallel is None:
            max_parallel = self.config.MAX_PARALLEL_DOWNLOADS
        
        max_parallel = min(max_parallel, 5)
        logger.info(f"Processing {len(urls)} videos with max {max_parallel} parallel downloads")
        
        if not urls:
            return []
        
        final_results = []
        download_queue = deque(urls)
        upload_queue = asyncio.Queue()
        download_semaphore = asyncio.Semaphore(max_parallel)
        download_tasks = set()
        
        async def _download_with_semaphore(url, semaphore, entity_id, topic_id, queue):
            async with semaphore:
                result = await self._download_and_prepare(url, None, entity_id, topic_id)
                await queue.put(result)
        
        async def download_worker():
            """Download videos in parallel and add to upload queue."""
            while download_queue or download_tasks:
                if download_queue and len(download_tasks) < max_parallel:
                    url = download_queue.popleft()
                    task = asyncio.create_task(_download_with_semaphore(
                        url, download_semaphore, entity_id, topic_id, upload_queue
                    ))
                    download_tasks.add(task)
                    task.add_done_callback(download_tasks.discard)
                else:
                    if download_tasks:
                        await asyncio.sleep(0.1)
                    else:
                        break
            
            if download_tasks:
                await asyncio.gather(*download_tasks, return_exceptions=True)
            
            await upload_queue.put(None)
        
        async def upload_worker():
            """Upload videos sequentially from queue."""
            upload_count = 0
            while True:
                result = await upload_queue.get()
                
                if result is None:
                    break
                
                if not result.get('success'):
                    final_results.append(result)
                    continue
                
                if not telegram_client or not bot_client:
                    final_results.append(result)
                    continue
                
                try:
                    video_path = result.get('video_path')
                    if not video_path or not video_path.exists():
                        result['upload_status'] = 'failed'
                        result['upload_error'] = 'Video file not found'
                        final_results.append(result)
                        continue
                    
                    upload_count += 1
                    logger.info(f"Uploading {upload_count}: {video_path.name}")
                    
                    upload_entity_id = result.get('entity_id', entity_id)
                    upload_topic_id = result.get('topic_id', topic_id)
                    
                    upload_options: UploadOptions = {
                        'video': str(video_path),
                        'entity': upload_entity_id,
                        'reply_to': upload_topic_id or 1,
                        'client': telegram_client,
                        'bot_client': bot_client,
                        'caption': result.get('caption', '')
                    }
                    await TelegramUploderService.upload(upload_options)
                    
                    result['upload_status'] = 'success'
                    logger.info(f"Upload completed: {video_path.name}")
                    
                except Exception as e:
                    logger.error(f"Upload failed: {e}", exc_info=True)
                    result['upload_status'] = 'failed'
                    result['upload_error'] = str(e)
                
                final_results.append(result)
        
        await asyncio.gather(download_worker(), upload_worker())
        
        logger.info(f"Batch processing completed: {len(final_results)} total results")
        return final_results

