from kmp.services.uploaders.video import VideoUploader
from telethon import TelegramClient
from typing import TypedDict
from social.logger import get_logger

logger = get_logger(__name__)

class UploadOptions(TypedDict):
    video: any
    entity: any
    reply_to: int
    client: TelegramClient
    bot_client: TelegramClient
    caption: str

class TelegramUploderService:
    @staticmethod
    async def upload(options: UploadOptions) -> str:
        uploader = VideoUploader(**options)
        logger.info("Uploading video to Telegram")
        await uploader.start()
        logger.info(f"Starting uploading...")
        await uploader.upload()
        logger.info("Video uploaded")
        await uploader.send_file()
        logger.info("File sent")
        await uploader.finalize_upload()
