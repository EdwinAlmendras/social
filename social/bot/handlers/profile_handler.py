"""Handler for profile creation and selection."""
from telethon import TelegramClient
from social.config import Config
from social.logger import get_logger
from social.services.social_flow_service import SocialFlowService

logger = get_logger(__name__)


class ProfileHandler:
    def __init__(self, config: Config, user_client: TelegramClient, bot_client: TelegramClient):
        self.config = config
        self.user_client = user_client
        self.bot_client = bot_client
        self.flow_service = SocialFlowService(config)
    
    async def handle_callback(self, event, data: str):
        if data == "profile_back":
            return
        
        parts = data.split('_')
        if len(parts) < 3:
            return
        
        platform = parts[1]
        topic_name = parts[2]
        
        logger.info(f"Selected profile: {platform}/{topic_name}")
        
        await event.answer(f"Using profile: {platform}/{topic_name}")

