"""Tests for pipeline behavior in SocialFlowService."""
import pytest
import asyncio
from pathlib import Path

from social.services.social_flow_service import SocialFlowService
from social.config import Config


@pytest.mark.asyncio
async def test_pipeline_parallel_downloads_sequential_uploads(config, mocker):
    """Test that downloads run in parallel (max 5) and uploads run sequentially."""
    service = SocialFlowService(config)
    
    download_times = []
    upload_order = []
    
    async def mock_download(url, platform=None):
        await asyncio.sleep(0.1)
        download_times.append(asyncio.get_event_loop().time())
        return {
            'id': f'video_{url}',
            'title': f'Video {url}',
            'extractor': 'youtube',
            'ext': 'mp4',
            'filepath': str(config.DOWNLOADS_DIR / 'youtube' / f'{url}.mp4')
        }
    
    async def mock_upload(options):
        upload_order.append(options['video'])
        await asyncio.sleep(0.05)
    
    test_path = Path('/tmp/test.mp4')
    test_path_mock = mocker.MagicMock()
    test_path_mock.exists.return_value = True
    test_path_mock.name = 'test.mp4'
    test_path_mock.__str__ = lambda self: str(test_path)
    
    mocker.patch.object(service, '_download_video_async', side_effect=mock_download)
    mocker.patch('social.services.social_flow_service.TelegramUploderService.upload', side_effect=mock_upload)
    mocker.patch.object(service, '_get_downloaded_file_path', return_value=test_path_mock)
    mocker.patch.object(service, '_determine_content_type', return_value=None)
    
    resolver_mock = mocker.MagicMock()
    resolver_mock.resolve.return_value = (123, 456)
    mocker.patch.object(service.entity_resolver_factory, 'get_resolver', return_value=resolver_mock)
    
    platform_mock = mocker.MagicMock()
    platform_mock.name = 'youtube'
    platform_mock.create_caption.return_value.build_caption.return_value = 'Test caption'
    mocker.patch.object(service.downloader, '_get_platform_for_extractor', return_value=platform_mock)
    
    urls = [f'url_{i}' for i in range(10)]
    telegram_client = mocker.AsyncMock()
    bot_client = mocker.AsyncMock()
    
    results = await service.process_videos_batch(
        urls=urls,
        telegram_client=telegram_client,
        bot_client=bot_client,
        max_parallel=3
    )
    
    assert len(results) == 10
    assert len(upload_order) == 10
    assert upload_order[0] in [str(Path('/tmp/test.mp4'))]
    assert len(download_times) == 10


@pytest.mark.asyncio
async def test_pipeline_max_parallel_limit(config, mocker):
    """Test that max parallel downloads is limited to 5."""
    service = SocialFlowService(config)
    
    concurrent_downloads = []
    max_concurrent = [0]
    
    async def mock_download(url, platform=None):
        concurrent_downloads.append(1)
        current = len(concurrent_downloads)
        if current > max_concurrent[0]:
            max_concurrent[0] = current
        await asyncio.sleep(0.1)
        concurrent_downloads.pop()
        return {
            'id': f'video_{url}',
            'title': f'Video {url}',
            'extractor': 'youtube',
            'ext': 'mp4',
            'filepath': str(config.DOWNLOADS_DIR / 'youtube' / f'{url}.mp4')
        }
    
    test_path = Path('/tmp/test.mp4')
    test_path_mock = mocker.MagicMock()
    test_path_mock.exists.return_value = True
    test_path_mock.name = 'test.mp4'
    test_path_mock.__str__ = lambda self: str(test_path)
    
    mocker.patch.object(service, '_download_video_async', side_effect=mock_download)
    mocker.patch('social.services.social_flow_service.TelegramUploderService.upload', new=mocker.AsyncMock())
    mocker.patch.object(service, '_get_downloaded_file_path', return_value=test_path_mock)
    mocker.patch.object(service, '_determine_content_type', return_value=None)
    
    resolver_mock = mocker.MagicMock()
    resolver_mock.resolve.return_value = (123, 456)
    mocker.patch.object(service.entity_resolver_factory, 'get_resolver', return_value=resolver_mock)
    
    platform_mock = mocker.MagicMock()
    platform_mock.name = 'youtube'
    platform_mock.create_caption.return_value.build_caption.return_value = 'Test caption'
    mocker.patch.object(service.downloader, '_get_platform_for_extractor', return_value=platform_mock)
    
    urls = [f'url_{i}' for i in range(20)]
    telegram_client = mocker.AsyncMock()
    bot_client = mocker.AsyncMock()
    
    await service.process_videos_batch(
        urls=urls,
        telegram_client=telegram_client,
        bot_client=bot_client,
        max_parallel=10
    )
    
    assert max_concurrent[0] <= 5


@pytest.mark.asyncio
async def test_pipeline_uploads_sequential(config, mocker):
    """Test that uploads happen sequentially, not in parallel."""
    service = SocialFlowService(config)
    
    upload_times = []
    upload_in_progress = [False]
    
    async def mock_download(url, platform=None):
        await asyncio.sleep(0.05)
        return {
            'id': f'video_{url}',
            'title': f'Video {url}',
            'extractor': 'youtube',
            'ext': 'mp4',
            'filepath': str(config.DOWNLOADS_DIR / 'youtube' / f'{url}.mp4')
        }
    
    async def mock_upload(options):
        assert not upload_in_progress[0], "Upload should be sequential"
        upload_in_progress[0] = True
        upload_times.append(asyncio.get_event_loop().time())
        await asyncio.sleep(0.1)
        upload_in_progress[0] = False
    
    test_path = Path('/tmp/test.mp4')
    test_path_mock = mocker.MagicMock()
    test_path_mock.exists.return_value = True
    test_path_mock.name = 'test.mp4'
    test_path_mock.__str__ = lambda self: str(test_path)
    
    mocker.patch.object(service, '_download_video_async', side_effect=mock_download)
    mocker.patch('social.services.social_flow_service.TelegramUploderService.upload', side_effect=mock_upload)
    mocker.patch.object(service, '_get_downloaded_file_path', return_value=test_path_mock)
    mocker.patch.object(service, '_determine_content_type', return_value=None)
    
    resolver_mock = mocker.MagicMock()
    resolver_mock.resolve.return_value = (123, 456)
    mocker.patch.object(service.entity_resolver_factory, 'get_resolver', return_value=resolver_mock)
    
    platform_mock = mocker.MagicMock()
    platform_mock.name = 'youtube'
    platform_mock.create_caption.return_value.build_caption.return_value = 'Test caption'
    mocker.patch.object(service.downloader, '_get_platform_for_extractor', return_value=platform_mock)
    
    urls = ['url_1', 'url_2', 'url_3']
    telegram_client = mocker.AsyncMock()
    bot_client = mocker.AsyncMock()
    
    results = await service.process_videos_batch(
        urls=urls,
        telegram_client=telegram_client,
        bot_client=bot_client,
        max_parallel=2
    )
    
    assert len(upload_times) == 3
    assert len([r for r in results if r.get('upload_status') == 'success']) == 3

