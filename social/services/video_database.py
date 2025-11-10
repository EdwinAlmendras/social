"""Video Database Service - Track processed video IDs in Telegram messages.

This service manages a text-based database stored entirely in Telegram:
- IDs are stored in a .txt file attached to the message
- Statistics are in the message text
"""
import re
import tempfile
from typing import Set, Optional, Dict, Any
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.types import Message

from social.logger import get_logger
from social.services.url_id_extractor import URLIDExtractor

logger = get_logger(__name__)


class VideoDatabaseService:
    """Service to manage video IDs database in Telegram."""
    
    # Database message format markers
    LAST_MSG_MARKER = "Last processed message ID:"
    TOTAL_IDS_MARKER = "Total video IDs:"
    NEW_IDS_MARKER = "New IDs in this sync:"
    
    def __init__(self, client: TelegramClient, db_entity_id: int, db_message_id: int):
        """
        Initialize video database service.
        
        Args:
            client: Telegram client
            db_entity_id: Entity (group/channel) ID where database message is stored
            db_message_id: ID of the Telegram message containing the database
        """
        self.client = client
        self.db_entity_id = db_entity_id
        self.db_message_id = db_message_id
        self.video_ids: Set[str] = set()
        self.last_processed_msg_id: int = 0
    
    def _parse_database_message(self, message_text: str) -> Dict[str, Any]:
        """
        Parse database message text to extract statistics only.
        IDs are loaded from the attached .txt file, not from text.
        
        Args:
            message_text: Text content of database message
            
        Returns:
            Dictionary with parsed statistics
        """
        result = {
            'last_msg_id': 0,
        }
        
        try:
            # Extract last processed message ID
            last_msg_match = re.search(rf'{self.LAST_MSG_MARKER}\s*(\d+|none)', message_text, re.IGNORECASE)
            if last_msg_match:
                last_msg_str = last_msg_match.group(1)
                if last_msg_str.lower() != 'none':
                    result['last_msg_id'] = int(last_msg_str)
        
        except Exception as e:
            logger.error(f"Error parsing database message: {e}")
        
        return result
    
    def _load_ids_from_file(self, file_path: Path) -> Set[str]:
        """
        Load video IDs from a .txt file.
        
        Args:
            file_path: Path to the .txt file
            
        Returns:
            Set of video IDs
        """
        video_ids = set()
        
        if not file_path.exists():
            logger.warning(f"Database file not found: {file_path}")
            return video_ids
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        video_ids.add(line)
            
            logger.info(f"Loaded {len(video_ids)} video IDs from {file_path}")
        
        except Exception as e:
            logger.error(f"Error loading IDs from file: {e}")
        
        return video_ids
    
    def _save_ids_to_file(self, video_ids: Set[str], file_path: Path):
        """
        Save video IDs to a .txt file.
        
        Args:
            video_ids: Set of video IDs to save
            file_path: Path where to save the file
        """
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Sort IDs for consistent ordering
            sorted_ids = sorted(video_ids)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                for video_id in sorted_ids:
                    f.write(f"{video_id}\n")
            
            logger.info(f"Saved {len(video_ids)} video IDs to {file_path}")
        
        except Exception as e:
            logger.error(f"Error saving IDs to file: {e}")
            raise
    
    def _build_database_message_text(self, last_msg_id: int, total_ids: int, new_ids_count: int) -> str:
        """
        Build database message text with statistics only.
        IDs are stored in the attached .txt file, not in the text.
        
        Args:
            last_msg_id: Last processed message ID
            total_ids: Total number of video IDs
            new_ids_count: Count of new IDs added in this sync
            
        Returns:
            Formatted database message text (statistics only)
        """
        message = f"{self.LAST_MSG_MARKER} {last_msg_id if last_msg_id > 0 else 'none'}\n"
        message += f"{self.TOTAL_IDS_MARKER} {total_ids}\n"
        message += f"{self.NEW_IDS_MARKER} {new_ids_count}"
        
        return message
    
    async def load(self) -> bool:
        """
        Load database from Telegram message.
        
        - Loads statistics from message text
        - Downloads attached .txt file and loads IDs from it
        
        Returns:
            True if database loaded successfully, False otherwise
        """
        try:
            logger.info(f"Loading video database from message ID: {self.db_message_id}")
            
            # Get the specific message by ID
            try:
                message = await self.client.get_messages(
                    self.db_entity_id,
                    ids=self.db_message_id
                )
                
                if not message:
                    logger.warning(f"Database message {self.db_message_id} not found, starting fresh")
                    self.last_processed_msg_id = 0
                    self.video_ids = set()
                    return False
                
                logger.info(f"Found database message: ID={message.id}")
                
                # Parse statistics from message text
                if message.text:
                    parsed = self._parse_database_message(message.text)
                    self.last_processed_msg_id = parsed['last_msg_id']
                else:
                    self.last_processed_msg_id = 0
                
                # Download and load IDs from attached .txt file
                self.video_ids = set()
                if message.media:
                    try:
                        # Download the attached file to a temporary location
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                            tmp_path = Path(tmp_file.name)
                        
                        await self.client.download_media(message.media, file=str(tmp_path))
                        logger.info(f"Downloaded database file: {tmp_path}")
                        
                        # Load IDs from the downloaded file
                        self.video_ids = self._load_ids_from_file(tmp_path)
                        
                        # Clean up temporary file
                        tmp_path.unlink()
                        
                    except Exception as e:
                        logger.warning(f"Could not download/load database file: {e}")
                        self.video_ids = set()
                
                logger.info(f"Database loaded: {len(self.video_ids)} video IDs, last processed: {self.last_processed_msg_id}")
                return True
            
            except Exception as e:
                logger.error(f"Error getting database message {self.db_message_id}: {e}")
                self.last_processed_msg_id = 0
                self.video_ids = set()
                return False
        
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            return False
    
    async def sync(self, content_entity_id: int, content_topic_id: Optional[int] = None) -> int:
        """
        Sync database by scanning messages for video URLs/IDs.
        
        Continues from last_processed_msg_id. If it's 0 (none), starts from the beginning.
        
        Args:
            content_entity_id: Entity ID where content messages are
            content_topic_id: Optional topic ID for content messages
            
        Returns:
            Number of new IDs added
        """
        try:
            start_from = self.last_processed_msg_id if self.last_processed_msg_id > 0 else None
            
            if start_from:
                logger.info(f"Syncing from message ID {start_from} (entity={content_entity_id}, topic={content_topic_id})")
            else:
                logger.info(f"Syncing from beginning (entity={content_entity_id}, topic={content_topic_id})")
            
            new_ids = set()
            latest_msg_id = self.last_processed_msg_id
            
            # Build iter_messages parameters
            iter_params = {
                'entity': content_entity_id,
                'reverse': True,
            }
            
            # Only add min_id if we have a starting point
            if start_from:
                iter_params['min_id'] = start_from
            
            # Iterate messages from last processed ID (or from beginning if none)
            async for message in self.client.iter_messages(**iter_params):
                if message.id > latest_msg_id:
                    latest_msg_id = message.id
                
                # Extract URLs from message - only process the FIRST URL (video URL)
                # The second URL is usually the channel URL, which we want to skip
                if message.text:
                    urls = re.findall(r'https?://[^\s\)]+', message.text)
                    if urls:
                        # Only process the first URL
                        first_url = urls[0]
                        video_id = URLIDExtractor.extract_id(first_url)
                        if video_id and video_id not in self.video_ids:
                            new_ids.add(video_id)
                            logger.debug(f"Found new video ID: {video_id} from message {message.id}")
                        elif video_id:
                            logger.debug(f"Video ID {video_id} already exists, skipping")
            
            # Update database
            self.video_ids.update(new_ids)
            self.last_processed_msg_id = latest_msg_id if latest_msg_id > 0 else self.last_processed_msg_id
            
            logger.info(f"Sync complete: {len(new_ids)} new IDs, total: {len(self.video_ids)}, last processed: {self.last_processed_msg_id}")
            return len(new_ids)
        
        except Exception as e:
            logger.error(f"Error syncing database: {e}")
            return 0
    
    async def save(self, new_ids_count: int = 0) -> bool:
        """
        Save database to Telegram message by merging old and new IDs.
        
        Process:
        1. Read current message and download attached .txt file
        2. Load existing IDs from the file
        3. Merge existing IDs with new IDs (union, not replace)
        4. Create temporary .txt file with merged IDs
        5. Update message with statistics text + attach the file
        
        Args:
            new_ids_count: Count of new IDs added in this sync
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Step 1: Read current message to get existing IDs from attached file
            logger.info(f"Reading current database message: ID={self.db_message_id}")
            current_message = await self.client.get_messages(
                self.db_entity_id,
                ids=self.db_message_id
            )
            
            existing_ids = set()
            if current_message and current_message.media:
                try:
                    # Download existing file to temporary location
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                        tmp_path = Path(tmp_file.name)
                    
                    await self.client.download_media(current_message.media, file=str(tmp_path))
                    logger.info(f"Downloaded existing database file")
                    
                    # Load existing IDs
                    existing_ids = self._load_ids_from_file(tmp_path)
                    logger.info(f"Found {len(existing_ids)} existing IDs in file")
                    
                    # Clean up
                    tmp_path.unlink()
                    
                except Exception as e:
                    logger.warning(f"Could not download existing file: {e}")
            
            # Step 2: Merge existing IDs with new IDs (union)
            merged_ids = existing_ids.union(self.video_ids)
            logger.info(f"Merged IDs: {len(existing_ids)} existing + {len(self.video_ids)} new = {len(merged_ids)} total")
            
            # Step 3: Create temporary file with merged IDs
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)
            
            self._save_ids_to_file(merged_ids, tmp_path)
            logger.info(f"Created temporary database file: {tmp_path}")
            
            # Step 4: Build message text with statistics only
            message_text = self._build_database_message_text(
                self.last_processed_msg_id,
                len(merged_ids),
                new_ids_count
            )
            
            # Step 5: Update the message with text + attach file
            logger.info(f"Updating database message: ID={self.db_message_id}")
            await self.client.edit_message(
                self.db_entity_id,
                self.db_message_id,
                message_text,
                file=str(tmp_path)
            )
            
            # Clean up temporary file
            tmp_path.unlink()
            
            # Update internal state with merged IDs
            self.video_ids = merged_ids
            
            logger.info("Database saved successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            return False
    
    def is_duplicate(self, url: str) -> bool:
        """
        Check if a URL has already been processed.
        
        Args:
            url: Video URL to check
            
        Returns:
            True if URL is a duplicate, False otherwise
        """
        video_id = URLIDExtractor.extract_id(url)
        if not video_id:
            logger.warning(f"Could not extract ID from URL: {url}")
            return False
        
        is_dup = video_id in self.video_ids
        if is_dup:
            logger.info(f"Duplicate detected: {video_id}")
        
        return is_dup
    
    def add_id(self, video_id: str):
        """
        Add a video ID to the database.
        
        Args:
            video_id: Video ID to add
        """
        self.video_ids.add(video_id)

