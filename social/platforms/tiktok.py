from social.platforms.base import Platform
from typing import Dict, Any, Optional
from yt_dlp import YoutubeDL
import json
import re
from pathlib import Path
from social.logger import get_logger

logger = get_logger(__name__)


class TikTokPlatform(Platform):
    """Platform configuration for TikTok."""
    
    def get_channel_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract channel info from TikTok video URL by parsing HTML.
        
        Uses yt-dlp with write_pages to get the HTML dump, then parses
        __UNIVERSAL_DATA_FOR_REHYDRATION__ to extract author information.
        
        Args:
            url: URL of a TikTok video
            
        Returns:
            Dictionary with harmonized channel information (snake_case)
        """
        try:
            # Use current directory for write_pages (yt-dlp saves there by default)
            current_dir = Path.cwd()
            logger.debug(f"Using current directory for pages: {current_dir}")
            
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'write_pages': True,
                'pages_directory': str(current_dir),  # Use current directory
            }
            
            # Add cookies if available
            if self.cookies.exists():
                ydl_opts['cookiefile'] = str(self.cookies)
                logger.debug(f"Using cookies file: {self.cookies}")
            
            logger.debug(f"Extracting info from URL: {url}")
            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=False)
            
            # Find dump file in current directory
            dump_files = list(current_dir.glob('*.dump'))
            logger.debug(f"Found {len(dump_files)} dump file(s) in current dir: {[f.name for f in dump_files]}")
            
            # Also check for .html files
            html_files = list(current_dir.glob('*.html'))
            logger.debug(f"Found {len(html_files)} HTML file(s) in current dir: {[f.name for f in html_files]}")
            
            if not dump_files:
                # Try HTML files as fallback
                if html_files:
                    logger.debug(f"Using HTML file as fallback: {html_files[0]}")
                    with open(html_files[0], 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    return self._parse_channel_info_from_html(content)
                else:
                    logger.warning(f"No dump or HTML file found in {current_dir}")
                    # List all files for debugging
                    all_files = list(current_dir.glob('*'))
                    logger.warning(f"Available files in current dir: {[f.name for f in all_files[:20]]}")
                    return None
            
            # Use the most recent dump file (in case there are multiple)
            dump_file = max(dump_files, key=lambda p: p.stat().st_mtime)
            logger.debug(f"Reading dump file: {dump_file}")
            file_size = dump_file.stat().st_size
            logger.debug(f"Dump file size: {file_size} bytes")
            
            with open(dump_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            logger.debug(f"Read {len(content)} characters from dump file")
            return self._parse_channel_info_from_html(content)
                
        except Exception as e:
            logger.error(f"Error extracting TikTok channel info: {e}", exc_info=True)
            return None
    
    def _parse_channel_info_from_html(self, html_content: str) -> Optional[Dict[str, Any]]:
        """
        Parse HTML content to extract channel info from __UNIVERSAL_DATA_FOR_REHYDRATION__.
        
        Args:
            html_content: HTML content from TikTok page
            
        Returns:
            Dictionary with harmonized channel information (snake_case)
        """
        try:
            logger.debug(f"Parsing HTML content ({len(html_content)} characters)")
            
            # Find the script tag with __UNIVERSAL_DATA_FOR_REHYDRATION__
            pattern = r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.+?)</script>'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if not match:
                logger.warning("Could not find __UNIVERSAL_DATA_FOR_REHYDRATION__ in HTML")
                # Try alternative patterns
                alt_patterns = [
                    r'window\.__UNIVERSAL_DATA_FOR_REHYDRATION__\s*=\s*({.+?});',
                    r'<script[^>]*>(.*?__UNIVERSAL_DATA_FOR_REHYDRATION__.*?)</script>',
                ]
                for alt_pattern in alt_patterns:
                    alt_match = re.search(alt_pattern, html_content, re.DOTALL)
                    if alt_match:
                        logger.debug(f"Found alternative pattern: {alt_pattern[:50]}...")
                        break
                if not any(re.search(p, html_content, re.DOTALL) for p in alt_patterns):
                    logger.warning("HTML content preview (first 500 chars): " + html_content[:500])
                return None
            
            json_str = match.group(1).strip()
            logger.debug(f"Extracted JSON string length: {len(json_str)}")
            data = json.loads(json_str)
            logger.debug(f"Successfully parsed JSON, keys: {list(data.keys())[:5]}")
            
            # Navigate to itemStruct
            item_struct = data['__DEFAULT_SCOPE__']['webapp.video-detail']['itemInfo']['itemStruct']
            
            # Extract author info (camelCase from TikTok)
            author = item_struct.get('author', {})
            author_stats = item_struct.get('authorStats', {})
            location_created = item_struct.get('locationCreated', '')
            
            # Harmonize to snake_case (matching YouTube format)
            # Include all available TikTok author stats
            result = {
                'channel': author.get('nickname', ''),  # TikTok uses 'nickname'
                'channel_id': author.get('secUid', ''),  # TikTok uses 'secUid'
                'channel_url': f"https://www.tiktok.com/@{author.get('uniqueId', '')}",
                'channel_follower_count': author_stats.get('followerCount', 0),
                'uploader': author.get('uniqueId', ''),  # TikTok username
                'uploader_id': str(author.get('id', '')),  # TikTok numeric ID
                'uploader_url': f"https://www.tiktok.com/@{author.get('uniqueId', '')}",
                'location': location_created,
                'channel_created': author.get('createTime', 0),  # Unix timestamp
                'avatar': author.get('avatarLarger', ''),  # TikTok uses 'avatarLarger'
                'description': author.get('signature', ''),  # TikTok uses 'signature' for bio
            }
            
            # Add TikTok-specific stats (extend harmonized format)
            result['following_count'] = author_stats.get('followingCount', 0)
            result['heart_count'] = author_stats.get('heart', 0) or author_stats.get('heartCount', 0)
            result['video_count'] = author_stats.get('videoCount', 0)
            result['digg_count'] = author_stats.get('diggCount', 0)
            result['friend_count'] = author_stats.get('friendCount', 0)
            
            # Additional author fields
            result['unique_id'] = author.get('uniqueId', '')
            result['verified'] = author.get('verified', False)
            result['avatar_medium'] = author.get('avatarMedium', '')
            result['avatar_thumb'] = author.get('avatarThumb', '')
            
            return result
            
        except KeyError as e:
            logger.error(f"Error navigating JSON structure: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from HTML: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing channel info from HTML: {e}")
            return None

