"""Main bot class following SOLID principles."""
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from social.config import Config
from social.logger import get_logger
from social.bot.handlers.url_handler import URLHandler
from social.bot.handlers.batch_handler import BatchHandler
from social.bot.handlers.profile_handler import ProfileHandler

logger = get_logger(__name__)


class SocialBot:
    def __init__(self, config: Config):
        self.config = config
        
        self.bot = TelegramClient('bot', config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
        self.user_client = TelegramClient('uploader', config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
        
        self.url_handler = URLHandler(config, self.user_client, self.bot)
        self.batch_handler = BatchHandler(config, self.user_client, self.bot)
        self.profile_handler = ProfileHandler(config, self.user_client, self.bot)
        
    async def run(self):
        await self.bot.start(bot_token=self.config.BOT_TOKEN)
        await self.user_client.connect()
        
        if not await self.user_client.is_user_authorized():
            logger.error("User client not authorized. Run authorize script first.")
            return
        
        logger.info("Bot started successfully")
        
        self._register_handlers()
        
        await self.bot.run_until_disconnected()
    
    def _register_handlers(self):
        @self.bot.on(events.NewMessage(pattern='/start'))
        async def start(event):
            await event.respond(
                "🤖 Social Bot Ready!\n\n"
                "Send me URLs to download and upload to Telegram:\n"
                "• Single URL - Process immediately\n"
                "• Multiple URLs - Choose profile or process individually"
            )
        
        @self.bot.on(events.NewMessage())
        async def message_handler(event):
            if event.message.text.startswith('/'):
                return
            
            urls = self.url_handler.extract_urls(event.message.text)
            
            if not urls:
                return
            
            if len(urls) == 1:
                await self.url_handler.handle_single_url(event, urls[0])
            else:
                await self.batch_handler.handle_multiple_urls(event, urls)
        
        @self.bot.on(events.CallbackQuery())
        async def callback_handler(event):
            data = event.data.decode('utf-8')
            
            if data.startswith('batch_'):
                await self.batch_handler.handle_callback(event, data)
            elif data.startswith('profile_'):
                await self.profile_handler.handle_callback(event, data)

