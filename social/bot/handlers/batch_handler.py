"""Handler for multiple URLs processing."""
import json
from telethon import TelegramClient, Button
from social.config import Config
from social.logger import get_logger
from social.services.social_flow_service import SocialFlowService

logger = get_logger(__name__)


class BatchHandler:
    def __init__(self, config: Config, user_client: TelegramClient, bot_client: TelegramClient):
        self.config = config
        self.user_client = user_client
        self.bot_client = bot_client
        self.flow_service = SocialFlowService(config)
        self.pending_batches = {}  # Store pending URL batches
    
    async def handle_multiple_urls(self, event, urls: list[str]):
        chat_id = event.chat_id
        self.pending_batches[chat_id] = urls
        
        logger.info(f"Received {len(urls)} URLs from chat {chat_id}")
        
        url_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(urls)])
        
        buttons = [
            [Button.inline("🆕 Create new profile", b"batch_create_profile")],
            [Button.inline("📁 Use existing profile", b"batch_existing_profile")],
            [Button.inline("🔄 Process individually", b"batch_process_individual")],
            [Button.inline("❌ Cancel", b"batch_cancel")]
        ]
        
        await event.respond(
            f"📋 Found {len(urls)} URLs:\n\n{url_list}\n\nWhat would you like to do?",
            buttons=buttons
        )
    
    async def handle_callback(self, event, data: str):
        chat_id = event.chat_id
        urls = self.pending_batches.get(chat_id, [])
        
        if not urls:
            await event.answer("Session expired. Please send URLs again.")
            return
        
        if data == "batch_create_profile":
            await self._handle_create_profile(event, urls)
        elif data == "batch_existing_profile":
            await self._handle_existing_profile(event, urls)
        elif data == "batch_process_individual":
            await self._process_individually(event, urls)
        elif data == "batch_cancel":
            del self.pending_batches[chat_id]
            await event.edit("❌ Cancelled")
    
    async def _handle_create_profile(self, event, urls: list[str]):
        await event.edit("🆕 Profile creation - Coming soon!\n\nProcessing individually for now...")
        await self._process_individually(event, urls)
    
    async def _handle_existing_profile(self, event, urls: list[str]):
        entities = getattr(self.config, 'ENTITIES', {})
        
        if not entities:
            await event.edit("No profiles configured. Processing individually...")
            await self._process_individually(event, urls)
            return
        
        buttons = []
        for platform, config in entities.items():
            topics = config.get('topics', {})
            for topic_name in topics.keys():
                callback_data = f"profile_{platform}_{topic_name}".encode('utf-8')
                buttons.append([Button.inline(f"📁 {platform}/{topic_name}", callback_data)])
        
        buttons.append([Button.inline("🔙 Back", b"batch_back")])
        
        await event.edit("Select profile:", buttons=buttons)
    
    async def _process_individually(self, event, urls: list[str]):
        chat_id = event.chat_id
        del self.pending_batches[chat_id]
        
        max_parallel = self.config.MAX_PARALLEL_DOWNLOADS
        await event.edit(
            f"🔄 Processing {len(urls)} videos...\n"
            f"⚡ Max parallel downloads: {max_parallel}"
        )
        
        try:
            logger.info(f"Using batch processing with max {max_parallel} parallel downloads")
            
            # Use batch processing with parallel downloads
            results = await self.flow_service.process_videos_batch(
                urls=urls,
                telegram_client=self.user_client,
                bot_client=self.bot_client,
                max_parallel=max_parallel
            )
            
            # Count results
            success_count = sum(1 for r in results if r.get('success') and r.get('upload_status') == 'success')
            failed_count = len(results) - success_count
            
            await event.edit(
                f"✅ Batch complete!\n\n"
                f"✅ Successful: {success_count}\n"
                f"❌ Failed: {failed_count}\n"
                f"📊 Total: {len(urls)}"
            )
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}", exc_info=True)
            await event.edit(f"❌ Batch processing failed: {str(e)}")

