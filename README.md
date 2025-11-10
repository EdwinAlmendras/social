# Social Downloader

CLI tool for downloading videos from social media platforms (YouTube, VK, TikTok, Rutube) and uploading them to Telegram with custom captions.

## Features

- 📥 Download videos from multiple platforms (YouTube, VK, TikTok, Rutube)
- 📝 Generate platform-specific captions with metadata
- 📤 Upload videos to Telegram with custom captions
- 🎯 Automatic content type detection (videos/shorts/clips)
- 🔧 Configurable platform settings and Telegram entities
- ⚡ Parallel downloads (up to 5 simultaneous downloads by default)
- 🔄 Sequential uploads to avoid Telegram rate limits
- 🧪 Comprehensive test suite (unit, integration, e2e)

## Installation

```bash
pip install -e .
```

Or with development dependencies:

```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Configure Environment

Create a `.env` file:

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
YOUTUBE_API_KEY=your_youtube_api_key  # Optional, for channel info
MAX_PARALLEL_DOWNLOADS=5  # Optional, default is 5 (range: 1-10)
```

### 2. Configure Entities

Create `.config/entities.json`:

```json
{
    "youtube": {
        "group_id": -1001234567890,
        "topics": {
            "videos": 5,
            "shorts": 3
        }
    }
}
```

### 3. Use the CLI

```bash
# Download and upload a video
social upload "https://www.youtube.com/watch?v=VIDEO_ID"

# Download and upload multiple videos (parallel downloads, sequential uploads)
social upload "URL1,URL2,URL3"

# Set max parallel downloads (5 is default)
social upload "URL1,URL2,URL3" --parallel 3

# Download only
social download url "https://www.youtube.com/watch?v=VIDEO_ID"

# Get video info
social info url "https://www.youtube.com/watch?v=VIDEO_ID"

# Change max parallel downloads setting
social config set-parallel 3

# Show current configuration
social config show
```

## Commands

### CLI Commands
- `social download` - Download videos from URLs
- `social upload` - Download and upload videos to Telegram (supports `--parallel` flag)
- `social info` - Get video information without downloading
- `social config` - Manage configuration
  - `social config show` - Display current configuration
  - `social config set-parallel <value>` - Set max parallel downloads (1-10)
- `social database` - Manage video ID database
- `social channel` - Get channel information

### Bot
Run the Telegram bot:
```bash
python -m social.bot
```

Bot features:
- Send single URL → Instant processing
- Send multiple URLs → Choose to create profile or process individually
- Parallel downloads (configurable via MAX_PARALLEL_DOWNLOADS)
- Inline buttons for profile selection
- Progress tracking for batch processing

## Project Structure

```
social/
├── bot/              # Telegram bot
│   ├── handlers/     # URL, batch, and profile handlers
│   └── bot.py        # Main bot class
├── cli/              # CLI commands
├── core/             # Core functionality (caption builder, entity resolver)
├── platforms/        # Platform-specific implementations
├── services/         # Business logic services
└── utils/            # Utility functions
```

## Testing

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit

# Run only e2e tests (requires credentials)
pytest tests/e2e -m e2e
```

## License

MIT License

