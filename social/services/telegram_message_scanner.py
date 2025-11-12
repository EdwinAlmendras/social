from typing import List, Dict, Any, Optional
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.types import Message
import re
from social.logger import logger


class TelegramMessageScanner:
    
    def __init__(self, client: TelegramClient):
        self.client = client
    
    async def scan_group(self, group_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Scan messages from group and extract URLs."""
        logger.info(f"Scanning group {group_id}, limit: {limit}")
        
        results = []
        try:
            entity = await self.client.get_entity(group_id)
            
            async for message in self.client.iter_messages(entity, limit=limit):
                if not message or not message.text:
                    continue
                
                urls = self._extract_urls(message.text)
                if urls:
                    results.append({
                        'message_id': message.id,
                        'date': message.date,
                        'text': message.text,
                        'urls': urls
                    })
            
            logger.info(f"Found {len(results)} messages with URLs")
            return results
            
        except Exception as e:
            logger.error(f"Scan error: {e}", exc_info=True)
            raise
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract video URLs from text."""
        pattern = r'https?://(?:www\.)?(?:youtube\.com|youtu\.be|tiktok\.com|vk\.com|rutube\.ru)[^\s]+'
        return re.findall(pattern, text)

