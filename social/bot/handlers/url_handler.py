"""Handler for single URL processing."""
import re
from telethon import TelegramClient
from social.config import Config
from social.logger import get_logger
from social.services.social_flow_service import SocialFlowService

logger = get_logger(__name__)


class URLHandler:
    def __init__(self, config: Config, user_client: TelegramClient, bot_client: TelegramClient):
        self.config = config
        self.user_client = user_client
        self.bot_client = bot_client
        self.flow_service = SocialFlowService(config)
    
    def extract_urls(self, text: str) -> list[str]:
        url_pattern = r'https?://(?:www\.)?(?:youtube\.com|youtu\.be|vk\.com|tiktok\.com|rutube\.ru)[^\s]+'
        return re.findall(url_pattern, text)
    
    async def handle_single_url(self, event, url: str):
        status_msg = await event.respond(f"⏳ Processing: {url}")
        
        try:
            logger.info(f"Processing single URL: {url}")
            
            result = await self.flow_service.process_video(
                url=url,
                telegram_client=self.user_client,
                bot_client=self.bot_client
            )
            
            if result['success']:
                await status_msg.edit(f"✅ Video uploaded successfully!\n\n{url}")
                logger.info(f"Successfully processed: {url}")
            else:
                await status_msg.edit(f"❌ Failed: {result.get('error', 'Unknown error')}")
                logger.error(f"Failed to process {url}: {result.get('error')}")
                
        except Exception as e:
            await status_msg.edit(f"❌ Error: {str(e)}")
            logger.error(f"Error processing {url}: {e}", exc_info=True)

