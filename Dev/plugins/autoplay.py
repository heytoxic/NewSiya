import re
import json
import asyncio
import aiohttp

from pyrogram import filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from Dev import app, lang, db

autoplay_db: dict[int, bool] = {}
autoplay_history: dict[int, list[str]] = {}


async def get_autoplay(chat_id: int) -> bool:
    if chat_id not in autoplay_db:
        autoplay_db[chat_id] = await db.get_autoplay(chat_id)
    return autoplay_db[chat_id]


async def set_autoplay(chat_id: int, state: bool) -> None:
    autoplay_db[chat_id] = state
    await db.set_autoplay(chat_id, state)


def _thumb(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


async def get_related_video(video_id: str, chat_id: int) -> dict | None:
    if chat_id not in autoplay_history:
        autoplay_history[chat_id] = []
    tried = autoplay_history[chat_id]

    payload = {
        "videoId": video_id,
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240101.00.00",
                "hl": "en",
                "gl": "US",
            }
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-YouTube-Client-Name": "1",
        "X-YouTube-Client-Version": "2.20240101.00.00",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Origin": "https://www.youtube.com",
        "Referer": f"https://www.youtube.com/watch?v={video_id}",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://www.youtube.com/youtubei/v1/next",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=12),
            ) as resp:
                data = await resp.json(content_type=None)

        results = (
            data.get("contents", {})
            .get("twoColumnWatchNextResults", {})
            .get("secondaryResults", {})
            .get("secondaryResults", {})
            .get("results", [])
        )

        for item in results:
            renderer = item.get("compactVideoRenderer")
            if not renderer:
                cr = item.get("compactAutoplayRenderer", {})
                contents = cr.get("contents", [])
                if contents:
                    renderer = contents[0].get("compactVideoRenderer")
            if not renderer:
                continue

            vid_id = renderer.get("videoId", "")
            if not vid_id or vid_id == video_id or vid_id in tried:
                continue

            title_obj = renderer.get("title", {})
            title = (
                title_obj.get("simpleText")
                or (title_obj.get("runs") or [{}])[0].get("text")
                or "Unknown"
            )
            duration = renderer.get("lengthText", {}).get("simpleText", "")

            tried.append(vid_id)
            if len(tried) > 50:
                tried.pop(0)

            return {
                "id": vid_id,
                "title": title[:25],
                "duration": duration,
                "thumbnail": _thumb(vid_id),
                "url": f"https://www.youtube.com/watch?v={vid_id}",
            }

    except Exception:
        pass

    return None


async def get_related_via_search(title: str, chat_id: int) -> dict | None:
    from py_yt import VideosSearch

    if chat_id not in autoplay_history:
        autoplay_history[chat_id] = []
    tried = autoplay_history[chat_id]

    clean = re.sub(r"(lyrical|lyrics|official|video|hd|full|song|audio)", "", title, flags=re.I).strip()
    clean = re.sub(r"\s+", " ", clean).strip()

    queries = [
        f"{clean} similar songs",
        f"songs like {clean}",
        f"{clean} playlist",
    ]

    for q in queries:
        try:
            search = VideosSearch(q, limit=20)
            results = await search.next()
            if not results or not results.get("result"):
                continue
            for item in results["result"]:
                vid_id = item.get("id", "")
                if not vid_id or vid_id in tried:
                    continue
                item_title = item.get("title", "")
                if item_title.lower() == title.lower():
                    continue
                thumbnails = item.get("thumbnails", [])
                thumbnail = thumbnails[-1].get("url", "").split("?")[0] if thumbnails else _thumb(vid_id)
                tried.append(vid_id)
                if len(tried) > 50:
                    tried.pop(0)
                return {
                    "id": vid_id,
                    "title": item_title[:25],
                    "duration": item.get("duration", ""),
                    "thumbnail": thumbnail,
                    "url": item.get("link", f"https://www.youtube.com/watch?v={vid_id}"),
                }
        except Exception:
            continue

    return None


def _markup(chat_id: int, state: bool):
    btn_text = "Turn OFF" if state else "Turn ON"
    cb_data = f"autoplay_off_{chat_id}" if state else f"autoplay_on_{chat_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_text, callback_data=cb_data)],
        [InlineKeyboardButton("Close", callback_data="autoplay_close")],
    ])


@app.on_message(
    filters.command(["autoplay", "ap"]) & filters.group & ~app.bl_users
)
@lang.language()
async def autoplay_cmd(_, m: types.Message):
    chat_id = m.chat.id
    args = m.command[1].lower() if len(m.command) > 1 else None
    state = await get_autoplay(chat_id)

    if args in ("on", "enable"):
        await set_autoplay(chat_id, True)
        return await m.reply_text(
            f"<b>Autoplay: ON</b>\n\nSimilar songs will play automatically after the current song ends.\n\nBy {m.from_user.mention}",
            reply_markup=_markup(chat_id, True),
        )

    if args in ("off", "disable"):
        await set_autoplay(chat_id, False)
        return await m.reply_text(
            f"<b>Autoplay: OFF</b>\n\nBy {m.from_user.mention}",
            reply_markup=_markup(chat_id, False),
        )

    status = "<b>ON</b>" if state else "<b>OFF</b>"
    await m.reply_text(
        f"<b>Autoplay Status:</b> {status}\n\n"
        f"<b>Usage:</b>\n"
        f"/autoplay on  - Enable autoplay\n"
        f"/autoplay off - Disable autoplay",
        reply_markup=_markup(chat_id, state),
    )


@app.on_callback_query(filters.regex(r"^autoplay_(on|off)_(-?\d+)$"))
async def autoplay_cb(_, q: CallbackQuery):
    action = q.matches[0].group(1)
    chat_id = int(q.matches[0].group(2))
    user_id = q.from_user.id

    admin_list = await db.get_admins(chat_id)
    if user_id not in admin_list and user_id not in app.sudoers:
        return await q.answer("Only admins can toggle autoplay.", show_alert=True)

    new_state = (action == "on")
    await set_autoplay(chat_id, new_state)

    status_text = "ON" if new_state else "OFF"
    await q.answer(f"Autoplay {status_text}", show_alert=False)
    try:
        await q.message.edit_reply_markup(reply_markup=_markup(chat_id, new_state))
    except Exception:
        pass


@app.on_callback_query(filters.regex("^autoplay_close$"))
async def autoplay_close_cb(_, q: CallbackQuery):
    try:
        await q.message.delete()
    except Exception:
        await q.answer("Cannot close.", show_alert=True)
