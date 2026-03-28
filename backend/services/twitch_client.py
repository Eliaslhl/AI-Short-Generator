"""
twitch_client.py – Twitch API integration for VOD download and metadata.

Supports:
- OAuth2 authentication
- VOD lookup and metadata
- Video download (via yt-dlp)
- Stream information retrieval
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class TwitchAuthManager:
    """Handles Twitch OAuth2 authentication and token management."""
    
    def __init__(self):
        self.client_id = os.getenv("TWITCH_CLIENT_ID", "")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("TWITCH_REDIRECT_URI", "http://localhost:8000/auth/twitch/callback")
        self.access_token = None
        self.token_expires_at = None
        
        if not self.client_id or not self.client_secret:
            logger.warning("⚠️ Twitch credentials not found. Set TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET")
    
    def get_app_access_token(self) -> Optional[str]:
        """
        Get an OAuth2 app access token for server-to-server requests.
        
        Returns:
            Access token or None if failed
        """
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            logger.debug("✅ Using cached access token")
            return self.access_token
        
        try:
            url = "https://id.twitch.tv/oauth2/token"
            params = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            }
            
            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            
            logger.info("✅ New Twitch app access token obtained")
            return self.access_token
            
        except Exception as e:
            logger.error(f"❌ Failed to get Twitch access token: {e}")
            return None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers for authenticated Twitch API requests."""
        token = self.get_app_access_token()
        if not token:
            return {}
        
        return {
            "Authorization": f"Bearer {token}",
            "Client-ID": self.client_id,
        }


class TwitchClient:
    """Main Twitch API client for VOD and stream operations."""
    
    BASE_URL = "https://api.twitch.tv/helix"
    
    def __init__(self):
        self.auth_manager = TwitchAuthManager()
    
    def get_user_by_login(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by login name.
        
        Args:
            username: Twitch username
        
        Returns:
            User info dict or None
        """
        try:
            url = f"{self.BASE_URL}/users"
            params = {"login": username}
            headers = self.auth_manager.get_auth_headers()
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("data"):
                user = data["data"][0]
                logger.info(f"✅ Found user: {username} (ID: {user['id']})")
                return user
            
            logger.warning(f"⚠️ User not found: {username}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching user {username}: {e}")
            return None
    
    def get_vods(
        self,
        user_id: str,
        limit: int = 10,
        period: str = "all",
        sort: str = "time",
    ) -> List[Dict[str, Any]]:
        """
        Get VODs for a user.
        
        Args:
            user_id: Twitch user ID
            limit: number of VODs to fetch (max 100)
            period: time period (all, day, week, month)
            sort: sort order (time, trending, views)
        
        Returns:
            List of VOD info dicts
        """
        try:
            url = f"{self.BASE_URL}/videos"
            params = {
                "user_id": user_id,
                "type": "archive",
                "first": min(limit, 100),
                "period": period,
                "sort": sort,
                "language": "en",
            }
            headers = self.auth_manager.get_auth_headers()
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            vods = data.get("data", [])
            logger.info(f"✅ Fetched {len(vods)} VODs for user {user_id}")
            
            return vods
            
        except Exception as e:
            logger.error(f"❌ Error fetching VODs: {e}")
            return []
    
    def get_vod_by_id(self, vod_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed VOD information by ID.
        
        Args:
            vod_id: Twitch VOD ID
        
        Returns:
            VOD info dict or None
        """
        try:
            url = f"{self.BASE_URL}/videos"
            params = {"id": vod_id}
            headers = self.auth_manager.get_auth_headers()
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("data"):
                vod = data["data"][0]
                logger.info(f"✅ Found VOD: {vod['title']} (Duration: {vod['duration']}s)")
                return vod
            
            logger.warning(f"⚠️ VOD not found: {vod_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching VOD {vod_id}: {e}")
            return None
    
    def parse_twitch_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        Parse Twitch URL to extract channel/VOD info.
        
        Args:
            url: Twitch URL (e.g., https://twitch.tv/videos/123456 or https://twitch.tv/username)
        
        Returns:
            Dict with 'type' and 'id'/'username', or None
        """
        try:
            # Remove protocol and trailing slashes
            url = url.replace("https://", "").replace("http://", "").rstrip("/")
            
            # Extract twitch.tv part
            if "twitch.tv/" not in url:
                logger.warning(f"⚠️ Invalid Twitch URL: {url}")
                return None
            
            parts = url.split("twitch.tv/")[-1].split("/")
            
            # VOD: /videos/{id}
            if parts[0] == "videos" and len(parts) > 1:
                return {"type": "vod", "id": parts[1]}
            
            # Clip: /clip/{id}
            if parts[0] == "clip" and len(parts) > 1:
                return {"type": "clip", "id": parts[1]}
            
            # Channel: /{username}
            if parts[0] and not parts[0].startswith("www"):
                return {"type": "channel", "username": parts[0]}
            
            logger.warning(f"⚠️ Could not parse Twitch URL: {url}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error parsing URL {url}: {e}")
            return None


class VideoDownloadManager:
    """Manages video download via yt-dlp."""
    
    def __init__(self, output_dir: str = "/tmp/twitch_downloads"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def download_twitch_vod(
        self,
        video_url: str,
        vod_id: str,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Download Twitch VOD using yt-dlp.
        
        Args:
            video_url: Twitch video URL
            vod_id: VOD ID for naming
            output_path: custom output path (optional)
        
        Returns:
            Path to downloaded file or None
        """
        try:
            import yt_dlp
            
            if output_path is None:
                output_path = os.path.join(self.output_dir, f"vod_{vod_id}.mp4")
            
            logger.info(f"📥 Downloading VOD {vod_id}...")
            
            ydl_opts = {
                "format": "best[ext=mp4]",
                "outtmpl": output_path.replace(".mp4", ""),
                "quiet": False,
                "no_warnings": False,
                "socket_timeout": 30,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                },
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                actual_path = ydl.prepare_filename(info)
                
                # Ensure it has .mp4 extension
                if not actual_path.endswith(".mp4"):
                    import shutil
                    final_path = output_path
                    shutil.move(actual_path, final_path)
                    actual_path = final_path
                
                file_size_mb = os.path.getsize(actual_path) / (1024 * 1024)
                logger.info(f"✅ Downloaded VOD: {actual_path} ({file_size_mb:.1f} MB)")
                
                return actual_path
        
        except Exception as e:
            logger.error(f"❌ Failed to download VOD: {e}")
            return None
    
    def get_video_duration(self, video_path: str) -> Optional[float]:
        """
        Get video duration using cv2.
        
        Args:
            video_path: path to video file
        
        Returns:
            Duration in seconds or None
        """
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            
            if fps and frame_count:
                duration = frame_count / fps
                logger.info(f"✅ Video duration: {duration:.1f}s ({duration/60:.1f} min)")
                return duration
            
            logger.warning(f"⚠️ Could not determine video duration")
            return None
        
        except Exception as e:
            logger.error(f"❌ Error getting video duration: {e}")
            return None


def create_twitch_client() -> TwitchClient:
    """Factory function to create Twitch client."""
    return TwitchClient()


def create_download_manager(output_dir: str = "/tmp/twitch_downloads") -> VideoDownloadManager:
    """Factory function to create download manager."""
    return VideoDownloadManager(output_dir)
