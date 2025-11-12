"""Parser for recovery bot caption format."""
import re
from datetime import datetime
from typing import Dict, Any

from social.logger import get_logger

logger = get_logger(__name__)


class RecoveryMetadataParser:
    """Parse metadata from @Kyreth_hq_bot caption for VideoCaptionBuilder."""
    
    @staticmethod
    def parse(caption: str) -> Dict[str, Any]:
        """Extract title, video_url, upload_date, channel_name, channel_url."""
        if not caption or not caption.strip():
            raise ValueError("Caption is empty")
        
        metadata: Dict[str, Any] = {
            'title': None,
            'channel_name': None,
            'channel_url': None,
            'video_url': None,
            'upload_date': None,
        }
        
        lines = caption.strip().split('\n')
        
        # Title: extract from # until video ID or resolution (e.g. abc123, 720p)
        if lines:
            first_line = lines[0].strip()
            
            # Split by special chars (￼, backtick)
            before_special = re.split(r'[￼`]', first_line)[0].strip()
            
            # Split by spaces and build title until ID/resolution
            words = before_special.split()
            title_words = []
            for word in words:
                # Stop at IDs (abc123) or resolutions (720p, 1080p)
                if re.match(r'^[a-zA-Z0-9_-]+\d+[a-zA-Z0-9]*$', word):
                    break
                title_words.append(word)
            
            if title_words:
                metadata['title'] = ' '.join(title_words)
        
        # Channel: [👀 Channel: Name](URL) - markdown link format
        for line in lines:
            channel_match = re.search(r'\[👀 Channel:\s*(.+?)\]\((https?://[^\)]+)\)', line)
            if channel_match:
                metadata['channel_name'] = channel_match.group(1).strip()
                metadata['channel_url'] = channel_match.group(2).strip()
                break
        
        # Date: 📅 DD.MM.YYYY
        for line in lines:
            date_match = re.search(r'📅\s*(\d{2})\.(\d{2})\.(\d{4})', line)
            if date_match:
                try:
                    metadata['upload_date'] = datetime(
                        int(date_match.group(3)),
                        int(date_match.group(2)),
                        int(date_match.group(1))
                    )
                except ValueError as e:
                    logger.warning(f"Invalid date: {e}")
                break
        
        # Video URL (last URL)
        urls = re.findall(r'(https?://[^\s]+)', caption)
        if urls:
            metadata['video_url'] = urls[-1]
        
        logger.info(f"Parsed: {metadata['title']} - {metadata['channel_name']}")
        return metadata

