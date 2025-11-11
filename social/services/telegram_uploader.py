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
        await uploader.start()
        await uploader.upload()
        await uploader.send_file()
        await uploader.finalize_upload()
