import json
import os
from dotenv import load_dotenv
from pathlib import Path

from social.logger import get_logger

logger = get_logger(__name__)

def get_env(key: str):
    return os.getenv(key)

class Config:
    def __init__(self, env_file = None):
        
        DEFAULT_CONFIG_DIR = Path.home() / ".config" / "social"
        DEFAULT_CACHE_DIR = Path.home() / ".cache" / "social"
        
        if not env_file:
            env_file = DEFAULT_CONFIG_DIR / ".env"
        load_dotenv(env_file)
        config_dir_env = os.getenv("CONFIG_DIR")
        if config_dir_env:
            self.CONFIG_DIR = Path(config_dir_env)
        else:
            # First try .config in current working directory
            current_dir_config = DEFAULT_CONFIG_DIR
            if current_dir_config.exists():
                self.CONFIG_DIR = current_dir_config
                logger.info(f"Using config directory from current directory: {self.CONFIG_DIR}")
            else:
                logger.warning(f"CONFIG_DIR not set, using default config directory: {DEFAULT_CONFIG_DIR}")
                self.CONFIG_DIR = DEFAULT_CONFIG_DIR

        cookies_dir_env = os.getenv("COOKIES_DIR")
        if cookies_dir_env:
            self.COOKIES_DIR = Path(cookies_dir_env)
        else:
            logger.warning(f"COOKIES_DIR not set, using default cookies directory: {self.CONFIG_DIR / "cookies"}")
            self.COOKIES_DIR = self.CONFIG_DIR / "cookies"
            
        entities_file_env = os.getenv("entities")
        if entities_file_env:
            self.ENTITIES_FILE = Path(entities_file_env)
        else:
            # First try .config/entities.json in current working directory
            current_dir_entities = Path.cwd() / ".config" / "entities.json"
            if current_dir_entities.exists():
                self.ENTITIES_FILE = current_dir_entities
                logger.info(f"Using entities file from current directory: {self.ENTITIES_FILE}")
            else:
                logger.warning(f"ENTITIES_FILE not set, using default entities file: {self.CONFIG_DIR / "entities.json"}")
                self.ENTITIES_FILE = self.CONFIG_DIR / "entities.json"
        
        platforms_file_env = os.getenv("PLATFORMS_FILE")
        if platforms_file_env:
            self.PLATFORMS_FILE = Path(platforms_file_env)
        else:
            self.PLATFORMS_FILE = self.CONFIG_DIR / "platforms.json"
            
        downloads_dir_env = os.getenv("DOWNLOADS_DIR")
        if downloads_dir_env:
            self.DOWNLOADS_DIR = Path(downloads_dir_env)
        else:
            logger.warning(f"DOWNLOADS_DIR not set, using default downloads directory: {self.CONFIG_DIR / "downloads"}")
            self.DOWNLOADS_DIR = DEFAULT_CACHE_DIR / "downloads"
        
        # Telegram credentials
        self.TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID', 0))
        self.TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH', '')
        self.BOT_TOKEN = os.getenv('BOT_TOKEN', '')
        self.YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
        
        # Telegram sessions directory
        self.SESSIONS_DIR = self.CONFIG_DIR / "sessions"
        
        # Session files - check env vars first, then use centralized defaults
        telegram_session_env = os.getenv("TELEGRAM_SESSION_FILE")
        if telegram_session_env:
            self.TELEGRAM_SESSION_FILE = Path(telegram_session_env)
        else:
            self.TELEGRAM_SESSION_FILE = self.SESSIONS_DIR / "uploader.session"
        
        bot_session_env = os.getenv("BOT_SESSION_FILE")
        if bot_session_env:
            self.BOT_SESSION_FILE = Path(bot_session_env)
        else:
            self.BOT_SESSION_FILE = self.SESSIONS_DIR / "bot.session"
        
        # Parallel downloads configuration
        self.MAX_PARALLEL_DOWNLOADS = int(os.getenv('MAX_PARALLEL_DOWNLOADS', 5))
        logger.info(f"Max parallel downloads set to: {self.MAX_PARALLEL_DOWNLOADS}")
        
        # make all dirs
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        self.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        
        count_cookies = len(list(self.COOKIES_DIR.glob("*.txt")))
        logger.info(f"Found {count_cookies} cookies in {self.COOKIES_DIR}")
        logger.info(f"Config initialized with CONFIG_DIR: {self.CONFIG_DIR}, COOKIES_DIR: {self.COOKIES_DIR}, ENTITIES_FILE: {self.ENTITIES_FILE}, PLATFORMS_FILE: {self.PLATFORMS_FILE}")
        
    
    def load_platforms_config(self):
        """
        Carga la configuración de plataformas desde platforms.json si existe.
        
        Returns:
            dict con configuración de plataformas o {} si el archivo no existe
        """
        if self.PLATFORMS_FILE.exists():
            try:
                with open(self.PLATFORMS_FILE, "r", encoding="utf-8") as f:
                    platforms_config = json.load(f)
                logger.info(f"Platforms config file {self.PLATFORMS_FILE} loaded successfully with {len(platforms_config)} platforms.")
                return platforms_config
            except Exception as e:
                logger.error(f"Error loading platforms config file {self.PLATFORMS_FILE}: {e}")
                return {}
        else:
            logger.debug(f"Platforms config file {self.PLATFORMS_FILE} not found, using default platform configurations.")
            return {}
    
    def load_entities(self):
        """ 
        Load entities telegram groups and topics
        """
        if self.ENTITIES_FILE.exists():
            with open(self.ENTITIES_FILE, "r") as f:
                self.ENTITIES = json.load(f)
            logger.info(f"Entities file {self.ENTITIES_FILE} loaded successfully with {len(self.ENTITIES)} entities.")
        else:
            logger.warning(f"Entities file {self.ENTITIES_FILE} not found, the app will not be able to use entities.")
            self.ENTITIES = {}
    
    def get_telegram_session_file(self, custom_session: str = None) -> Path:
        """
        Get the path to the Telegram session file.
        
        Args:
            custom_session: Custom session file path (optional)
            
        Returns:
            Path to the session file (centralized in config/sessions/)
        """
        if custom_session:
            # If custom path is provided, check if it's absolute or relative
            custom_path = Path(custom_session)
            if custom_path.is_absolute():
                return custom_path
            else:
                # Relative paths are resolved from sessions directory
                return self.SESSIONS_DIR / custom_session
        return self.TELEGRAM_SESSION_FILE
    
    def get_bot_session_file(self, custom_session: str = None) -> Path:
        """
        Get the path to the bot session file.
        
        Args:
            custom_session: Custom session file path (optional)
            
        Returns:
            Path to the bot session file (centralized in config/sessions/)
        """
        if custom_session:
            # If custom path is provided, check if it's absolute or relative
            custom_path = Path(custom_session)
            if custom_path.is_absolute():
                return custom_path
            else:
                # Relative paths are resolved from sessions directory
                return self.SESSIONS_DIR / custom_session
        return self.BOT_SESSION_FILE
    
    def validate_telegram_config(self) -> tuple[bool, str]:
        """
        Validate that all required Telegram configuration is present.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.TELEGRAM_API_ID or self.TELEGRAM_API_ID == 0:
            return False, "TELEGRAM_API_ID is not set or invalid"
        
        if not self.TELEGRAM_API_HASH:
            return False, "TELEGRAM_API_HASH is not set"
        
        if not self.BOT_TOKEN:
            return False, "BOT_TOKEN is not set"
        
        return True, ""


