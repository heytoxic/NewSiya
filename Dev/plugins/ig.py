import os
import asyncio
import tempfile
import aiohttp
import yt_dlp
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from Dev import app as sex

logger = logging.getLogger(__name__)

COOKIE_URL = "https://batbin.me/commemorations"

async def fetch_cookies(url):
    """Batbin link cookies"""
    if "batbin.me/" in url and "/raw/" not in url:
        url = url.replace("batbin.me/", "batbin.me/raw/")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as f:
                        f.write(content)
                        return f.name
    except Exception as e:
        logger.error(f"Cookie Error: {e}")
    return None

@sex.on_message(filters.regex(r"(https?:\/\/(?:www\.)?instagram\.com(?:\/[^\s]+)?)") & filters.incoming)
async def insta_pyro_handler(client: Client, message: Message):
    
    url = message.matches[0].group(0)
    chat_id = message.chat.id

    try:
        await message.delete()
    except Exception:
        pass

    alert = await message.reply("𝘋𝘰𝘸𝘯𝘭𝘰𝘢𝘥𝘪𝘯𝘨...🌿")
    
    cookie_path = await fetch_cookies(COOKIE_URL)
    file_path = f"insta_{message.id}.mp4"

    ydl_opts = {
        'outtmpl': file_path,
        'format': 'best[ext=mp4]',
        'cookiefile': cookie_path,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        def download_it():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=True)

        info = await asyncio.to_thread(download_it)
        
        if not os.path.exists(file_path):
            await alert.edit("**Download Failed!**")
            await asyncio.sleep(2)
            await alert.delete()
            return

        duration = int(info.get('duration', 0))
        width = info.get('width', 0)
        height = info.get('height', 0)
        caption = "@Toxic_Bots 🍃🌲"

        await client.send_video(
            chat_id=chat_id,
            video=file_path,
            caption=caption,
            duration=duration,
            width=width,
            height=height,
            supports_streaming=True
        )

        await alert.delete()

    except Exception as e:
        logger.error(f"Error: {e}")
        await alert.edit(f"**Error:** `{e}`")
        await asyncio.sleep(3)
        await alert.delete()
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if cookie_path and os.path.exists(cookie_path):
            os.remove(cookie_path)

