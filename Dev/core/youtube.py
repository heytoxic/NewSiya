import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Union

from pyrogram import enums, types
from py_yt import Playlist, VideosSearch

from Dev import logger
from Dev.helpers import Track, utils


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.warned = False
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )

    def get_cookies(self):
        if not self.checked:
            if os.path.exists("Dev/cookies"):
                for file in os.listdir("Dev/cookies"):
                    if file.endswith(".txt"):
                        self.cookies.append(file)
            self.checked = True
        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies are missing; downloads might fail.")
            return None
        return f"Dev/cookies/{random.choice(self.cookies)}"

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        os.makedirs("Dev/cookies", exist_ok=True)
        async with aiohttp.ClientSession() as session:
            for url in urls:
                path = f"Dev/cookies/cookie{random.randint(10000, 99999)}.txt"
                link = url.replace("me/", "me/raw/")
                async with session.get(link) as resp:
                    resp.raise_for_status()
                    with open(path, "wb") as fw:
                        fw.write(await resp.read())
        self.checked = False
        self.cookies = []
        logger.info("Cookies saved.")

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def url(self, message_1: types.Message) -> Union[str, None]:
        messages = [message_1]
        link = None
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:
            text = message.text or message.caption or ""

            if message.entities:
                for entity in message.entities:
                    if entity.type == enums.MessageEntityType.URL:
                        link = text[entity.offset : entity.offset + entity.length]
                        break

            if message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == enums.MessageEntityType.TEXT_LINK:
                        link = entity.url
                        break

        if link:
            return link.split("&si")[0].split("?si")[0]
        return None

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        _search = VideosSearch(query, limit=1)
        results = await _search.next()
        if results and results["result"]:
            data = results["result"][0]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track | None]:
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist["videos"][:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")),
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails")[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except:
            pass
        return tracks

    async def download(self, video_id: str, video: bool = False) -> Optional[str]:
        url = self.base + video_id

        existing = next(Path("downloads").glob(f"{video_id}.*"), None)
        if existing:
            return str(existing)

        cookie = self.get_cookies()

        base_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "no_warnings": True,
            "overwrites": False,
            "nocheckcertificate": True,
            "geo_bypass": True,
            "cookiefile": cookie,
            "concurrent_fragment_downloads": 4,
            "socket_timeout": 10,
            "retries": 3,
            "fragment_retries": 3,
        }

        if video:
            ydl_opts = {
                **base_opts,
                "format": (
                    "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/"
                    "bestvideo[height<=720]+bestaudio/"
                    "best[height<=720]/best"
                ),
                "merge_output_format": "mp4",
            }
        else:
            ydl_opts = {
                **base_opts,
                "format": (
                    "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best"
                ),
            }

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([url])
                    path = next(Path("downloads").glob(f"{video_id}.*"), None)
                    return str(path) if path else None
                except yt_dlp.utils.DownloadError as ex:
                    err = str(ex)
                    if "Sign in" in err or "bot" in err:
                        logger.warning("Cookie invalid or IP blocked: %s", video_id)
                        cookie_name = cookie.replace("Dev/cookies/", "") if cookie else None
                        if cookie_name and cookie_name in self.cookies:
                            self.cookies.remove(cookie_name)
                    else:
                        logger.error("Download failed: %s", ex)
                    return None
                except Exception as ex:
                    logger.error("Download failed: %s", ex)
                    return None

        return await asyncio.to_thread(_download)
