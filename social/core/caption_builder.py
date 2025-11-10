from datetime import datetime
from typing import Optional


class CaptionFormatter:
    """Base class with shared utilities for caption formatting."""
    
    @staticmethod
    def _format_number(num: int) -> str:
        """
        Formatea números grandes con K (miles), M (millones) y B (billones).
        
        Args:
            num: Número a formatear
            
        Returns:
            String con el número formateado
            
        Examples:
            525 -> "525"
            16354 -> "16.3K"
            1500000 -> "1.5M"
            1456091000 -> "1.5B"
        """
        if num < 1000:
            return str(num)
        elif num < 1_000_000:
            # Miles (K)
            k = num / 1000
            # Si es número entero, no mostrar decimales
            if k == int(k):
                return f"{int(k)}K"
            # Si es mayor a 100, sin decimales
            elif k >= 100:
                return f"{int(k)}K"
            # Mostrar 1 decimal
            else:
                formatted = f"{k:.1f}K"
                # Eliminar .0 si termina en .0
                return formatted.replace('.0K', 'K')
        elif num < 1_000_000_000:
            # Millones (M)
            m = num / 1_000_000
            # Si es número entero, no mostrar decimales
            if m == int(m):
                return f"{int(m)}M"
            # Si es mayor a 100, sin decimales
            elif m >= 100:
                return f"{int(m)}M"
            # Mostrar 1 decimal
            else:
                formatted = f"{m:.1f}M"
                # Eliminar .0 si termina en .0
                return formatted.replace('.0M', 'M')
        else:
            # Billones (B)
            b = num / 1_000_000_000
            # Si es número entero, no mostrar decimales
            if b == int(b):
                return f"{int(b)}B"
            # Si es mayor a 100, sin decimales
            elif b >= 100:
                return f"{int(b)}B"
            # Mostrar 1 decimal
            else:
                formatted = f"{b:.1f}B"
                # Eliminar .0 si termina en .0
                return formatted.replace('.0B', 'B')


class VideoCaptionBuilder(CaptionFormatter):
    def __init__(self, title: str, video_url: str, creation_date: datetime, 
                 channel_name: str, channel_url: str, likes: Optional[int] = None, 
                 views: Optional[int] = None):
        self.title = title
        self.video_url = video_url
        self.creation_date = creation_date
        self.channel_name = channel_name
        self.channel_url = channel_url
        self.likes = likes
        self.views = views
    
    def build_caption(self) -> str:
        """
        Build a formatted caption for a video.
        
        Returns:
            Formatted caption string with Markdown formatting
            
        Example:
            [Video Title](https://youtube.com/watch?v=xxx)
            📅 10.11.2025 14:30 | 👁️ 1.2M | ❤️ 45K
            👤 [Channel Name](https://youtube.com/@username)
        """
        
        # Build the caption
        caption = f"[{self.title}]({self.video_url})\n"
        
        # Add date and time
        date_time = self.creation_date.strftime("%d.%m.%Y %H:%M").replace(" 0", " ")
        caption += f"📅 {date_time}"
        
        # Add views if provided (formatted)
        if self.views is not None:
            views_formatted = self._format_number(self.views)
            caption += f" | 👁️ {views_formatted}"
        
        # Add likes if provided (formatted)
        if self.likes is not None:
            likes_formatted = self._format_number(self.likes)
            caption += f" | ❤️ {likes_formatted}"
        
        caption += "\n"
        
        # Add channel info in markdown format
        caption += f"👤 [{self.channel_name}]({self.channel_url})"
        
        return caption


class ChannelCaptionBuilder(CaptionFormatter):
    """Builder for channel information captions."""
    
    def __init__(self, channel_name: str, channel_url: str, username: Optional[str] = None,
                 uploader_url: Optional[str] = None, channel_follower_count: Optional[int] = None,
                 video_count: Optional[int] = None, view_count: Optional[int] = None,
                 location: Optional[str] = None, channel_created: Optional[int] = None,
                 description: Optional[str] = None, avatar: Optional[str] = None):
        """
        Initialize ChannelCaptionBuilder with channel information.
        
        Args:
            channel_name: Name of the channel
            channel_url: URL of the channel
            username: Username/handle of the channel (e.g., @username)
            uploader_url: URL for the uploader (used for username link)
            channel_follower_count: Number of subscribers/followers
            video_count: Total number of videos
            view_count: Total view count of the channel
            location: Country/location of the channel
            channel_created: Unix timestamp of channel creation date
            description: Channel description
            avatar: Avatar/profile picture URL
        """
        self.channel_name = channel_name
        self.channel_url = channel_url
        self.username = username
        self.uploader_url = uploader_url
        self.channel_follower_count = channel_follower_count
        self.video_count = video_count
        self.view_count = view_count
        self.location = location
        self.channel_created = channel_created
        self.description = description
        self.avatar = avatar
    
    def build_caption(self) -> str:
        """
        Build a formatted caption for a channel.
        
        Returns:
            Formatted caption string with Markdown formatting
            
        Example:
            📺 [Channel Name](https://youtube.com/@username)
            👥 2.38M subscribers | 📹 7.5K videos | 👁️ 1.5B views
            📍 Country | 📅 Created: 2011
            📝 Channel description...
        """
        # Build channel header with two links: username (uploader_url) and channel name (channel_url)
        if self.username and self.uploader_url:
            # Show both username link (with uploader_url) and channel name link (with channel_url)
            caption = f"📺 **[{self.username}]({self.uploader_url})** | **[{self.channel_name}]({self.channel_url})**\n"
        elif self.username:
            # Username available but no uploader_url, use channel_url for both
            caption = f"📺 **[{self.username}]({self.channel_url})** | **[{self.channel_name}]({self.channel_url})**\n"
        else:
            # Only channel name available
            caption = f"📺 **[{self.channel_name}]({self.channel_url})**\n"
        
        # Stats line
        stats = []
        if self.channel_follower_count is not None:
            followers_formatted = self._format_number(self.channel_follower_count)
            stats.append(f"👥 {followers_formatted} subscribers")
        
        if self.video_count is not None:
            videos_formatted = self._format_number(self.video_count)
            stats.append(f"📹 {videos_formatted} videos")
        
        if self.view_count is not None:
            views_formatted = self._format_number(self.view_count)
            stats.append(f"👁️ {views_formatted} views")
        
        if stats:
            caption += " | ".join(stats) + "\n"
        
        # Location and creation date
        metadata = []
        if self.location:
            metadata.append(f"📍 {self.location}")
        
        if self.channel_created and self.channel_created > 0:
            creation_date = datetime.fromtimestamp(self.channel_created)
            date_formatted = creation_date.strftime("%d.%m.%Y")
            metadata.append(f"📅 Created: {date_formatted}")
        
        if metadata:
            caption += " | ".join(metadata) + "\n"
        
        # Description (truncated if too long)
        if self.description:
            max_desc_length = 200
            description = self.description.strip()
            if len(description) > max_desc_length:
                description = description[:max_desc_length].rsplit(' ', 1)[0] + '...'
            caption += f"📝 {description}\n"
        
        return caption.rstrip()


# Backwards compatibility alias
CaptionBuilder = VideoCaptionBuilder
