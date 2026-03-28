"""
twitch_api_client.py – Client for Twitch API (Helix).

Provides methods to:
- Get VODs for a channel
- Get clips for a channel
- Get channel info
- Authenticate via Client Credentials flow
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
import requests

logger = logging.getLogger(__name__)


class TwitchAPIClient:
    """Async Twitch API (Helix) client using Client Credentials OAuth flow."""

    BASE_URL = "https://api.twitch.tv/helix"
    AUTH_URL = "https://id.twitch.tv/oauth2/token"

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize the Twitch API client.

        Args:
            client_id: Twitch application Client ID
            client_secret: Twitch application Client Secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None
    # Using requests in threads, no aiohttp session required

    async def __aenter__(self):
        # Authenticate synchronously via requests in a thread
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Nothing to close when using requests
        return None

    async def authenticate(self) -> str:
        """Authenticate using Client Credentials flow (requests in thread)."""
        def _auth():
            resp = requests.post(
                self.AUTH_URL,
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                },
                timeout=10,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Twitch auth failed (status {resp.status_code}): {resp.text}")
            data = resp.json()
            token = data.get("access_token")
            if not token:
                raise RuntimeError("No access_token in response")
            return token

        try:
            token = await asyncio.to_thread(_auth)
            self._access_token = token
            logger.info("Twitch API authenticated successfully")
            return token
        except Exception as e:
            raise RuntimeError(f"Twitch auth error: {e}")

    async def _ensure_authenticated(self):
        """Ensure we have a valid access token."""
        if not self._access_token:
            await self.authenticate()

    def _headers(self) -> Dict[str, str]:
        """Build request headers."""
        return {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self._access_token}",
        }

    async def get_user_by_login(self, login: str) -> Optional[Dict[str, Any]]:
        """
        Get user info by login name.

        Args:
            login: Twitch login/username

        Returns:
            User dict with id, login, display_name, or None if not found
        """
        await self._ensure_authenticated()

        def _get():
            resp = requests.get(
                f"{self.BASE_URL}/users",
                params={"login": login},
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                users = data.get("data", [])
                return users[0] if users else None
            if resp.status_code == 404:
                return None
            logger.warning(f"get_user_by_login failed: {resp.status_code} {resp.text}")
            return None

        try:
            return await asyncio.to_thread(_get)
        except Exception:
            logger.exception(f"Error getting user {login}")
            return None

    async def get_vods(
        self,
        channel_login: str,
        limit: int = 20,
        sort: str = "time",  # time | trending | views
    ) -> List[Dict[str, Any]]:
        """
        Get VODs for a channel.

        Args:
            channel_login: Twitch channel login (ex: "ninja")
            limit: Max number of VODs to return (default 20, max 100)
            sort: Sort order (time, trending, views)

        Returns:
            List of VOD dicts with id, title, created_at, duration, view_count, url, thumbnail_url
        """
        await self._ensure_authenticated()

        # First get user ID from login
        user = await self.get_user_by_login(channel_login)
        if not user:
            logger.warning(f"Channel not found: {channel_login}")
            return []

        user_id = user.get("id")
        if not user_id:
            return []

        def _fetch():
            resp = requests.get(
                f"{self.BASE_URL}/videos",
                params={
                    "user_id": user_id,
                    "type": "archive",
                    "first": min(limit, 100),
                    "sort": sort,
                },
                headers=self._headers(),
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"get_vods failed for {channel_login}: {resp.status_code} {resp.text}")
                return []
            data = resp.json()
            vods = data.get("data", [])
            result = []
            def _parse_duration(d):
                """Parse Twitch duration formats like '3h46m53s' into seconds (int).

                If already an int/float, return int(value). If unknown format, return None.
                """
                if d is None:
                    return None
                if isinstance(d, (int, float)):
                    return int(d)
                if isinstance(d, str):
                    # Examples: '3h46m53s', '46m53s', '53s', '123'
                    total = 0
                    num = ''
                    for ch in d:
                        if ch.isdigit():
                            num += ch
                            continue
                        if num:
                            val = int(num)
                            if ch == 'h':
                                total += val * 3600
                            elif ch == 'm':
                                total += val * 60
                            elif ch == 's':
                                total += val
                            else:
                                # unknown designator, ignore
                                pass
                            num = ''
                    # trailing number (no designator) -> seconds
                    if num:
                        try:
                            total += int(num)
                        except Exception:
                            return None
                    return total if total != 0 else None

            for vod in vods:
                raw_dur = vod.get("duration")
                parsed_dur = _parse_duration(raw_dur)
                result.append(
                    {
                        "id": vod.get("id"),
                        "title": vod.get("title"),
                        "created_at": vod.get("created_at"),
                        "duration": parsed_dur,
                        "view_count": vod.get("view_count"),
                        "url": vod.get("url"),
                        "thumbnail_url": vod.get("thumbnail_url"),
                        "channel_name": vod.get("user_login"),
                        "channel_display_name": vod.get("user_name"),
                    }
                )
            return result

        try:
            return await asyncio.to_thread(_fetch)
        except Exception:
            logger.exception(f"Error getting VODs for {channel_login}")
            return []

    async def get_clips(
        self,
        channel_login: str,
        limit: int = 20,
        sort: str = "trending",  # trending | time | views
    ) -> List[Dict[str, Any]]:
        """
        Get clips for a channel.

        Args:
            channel_login: Twitch channel login
            limit: Max clips to return
            sort: Sort order

        Returns:
            List of clip dicts
        """
        await self._ensure_authenticated()

        user = await self.get_user_by_login(channel_login)
        if not user:
            return []

        user_id = user.get("id")
        if not user_id:
            return []

        def _fetch_clips():
            resp = requests.get(
                f"{self.BASE_URL}/clips",
                params={
                    "broadcaster_id": user_id,
                    "first": min(limit, 100),
                    "sort": sort,
                },
                headers=self._headers(),
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"get_clips failed for {channel_login}: {resp.status_code} {resp.text}")
                return []
            data = resp.json()
            clips = data.get("data", [])
            result = []
            for clip in clips:
                result.append(
                    {
                        "id": clip.get("id"),
                        "title": clip.get("title"),
                        "created_at": clip.get("created_at"),
                        "url": clip.get("url"),
                        "thumbnail_url": clip.get("thumbnail_url"),
                        "view_count": clip.get("view_count"),
                        "channel_name": clip.get("broadcaster_login"),
                        "channel_display_name": clip.get("broadcaster_name"),
                    }
                )
            return result

        try:
            return await asyncio.to_thread(_fetch_clips)
        except Exception:
            logger.exception(f"Error getting clips for {channel_login}")
            return []

    async def close(self):
        """Close the aiohttp session."""
        # No persistent session when using requests; nothing to close
        return None
