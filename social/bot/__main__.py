"""Entry point for running the bot: python -m social.bot"""
import asyncio
from social.config import Config
from social.logger import get_logger
from social.bot.bot import SocialBot

logger = get_logger(__name__)

def main():
    config = Config()
    
    if not all([config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH, config.BOT_TOKEN]):
        logger.error("Missing required environment variables: TELEGRAM_API_ID, TELEGRAM_API_HASH, BOT_TOKEN")
        return
    
    bot = SocialBot(config=config)
    
    logger.info("Starting Social Bot...")
    asyncio.run(bot.run())

if __name__ == "__main__":
    main()

