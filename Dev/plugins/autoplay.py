import re
import json
import asyncio
import aiohttp

from pyrogram import filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from Dev import app, lang, db

autoplay_db: dict[int, bool] = {}
# {chat_id: {"playlist": [...video_dicts], "index": 0, "seed_id": "", "played_ids": set()}}
autoplay_state: dict[int, dict] = {}


async def get_autoplay(chat_id: int) -> bool:
    if chat_id not in autoplay_db:
        autoplay_db[chat_id] = await db.get_autoplay(chat_id)
    return autoplay_db[chat_id]


async def set_autoplay(chat_id: int, state: bool) -> None:
    autoplay_db[chat_id] = state
    await db.set_autoplay(chat_id, state)


def _thumb(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


async def _fetch_mix_playlist(video_id: str) -> list[dict]:
    """
    Fetch YouTube RD (Radio/Mix) playlist for a given video ID.
    Returns list of {id, title, duration, thumbnail, url}
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.youtube.com/",
    }
    tracks = []
    try:
        url = f"https://www.youtube.com/watch?v={video_id}&list=RD{video_id}"
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                html = await resp.text()

        marker = "var ytInitialData = "
        start = html.find(marker)
        if start == -1:
            return []
        start += len(marker)
        end = html.find(";</script>", start)
        if end == -1:
            return []

        data = json.loads(html[start:end])

        playlist_panel = (
            data.get("contents", {})
            .get("twoColumnWatchNextResults", {})
            .get("playlist", {})
            .get("playlist", {})
            .get("contents", [])
        )

        for item in playlist_panel:
            renderer = item.get("playlistPanelVideoRenderer", {})
            vid_id = renderer.get("videoId", "")
            if not vid_id or vid_id == video_id:
                continue
            title_obj = renderer.get("title", {})
            title = title_obj.get("simpleText") or (title_obj.get("runs") or [{}])[0].get("text") or "Unknown"
            duration = renderer.get("lengthText", {}).get("simpleText", "")
            tracks.append({
                "id": vid_id,
                "title": title[:25],
                "duration": duration,
                "thumbnail": _thumb(vid_id),
                "url": f"https://www.youtube.com/watch?v={vid_id}",
            })

    except Exception:
        pass

    return tracks


async def _fetch_mix_via_innertube(video_id: str) -> list[dict]:
    """Fallback: use InnerTube next API to get related videos."""
    tracks = []
    try:
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://www.youtube.com",
        }
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
            if not vid_id or vid_id == video_id:
                continue
            title_obj = renderer.get("title", {})
            title = (
                title_obj.get("simpleText")
                or (title_obj.get("runs") or [{}])[0].get("text")
                or "Unknown"
            )
            duration = renderer.get("lengthText", {}).get("simpleText", "")
            tracks.append({
                "id": vid_id,
                "title": title[:25],
                "duration": duration,
                "thumbnail": _thumb(vid_id),
                "url": f"https://www.youtube.com/watch?v={vid_id}",
            })

    except Exception:
        pass

    return tracks


async def get_next_autoplay_track(chat_id: int, last: dict) -> dict | None:
    last_id = last.get("id") if isinstance(last, dict) else None
    last_title = last.get("title") if isinstance(last, dict) else str(last)

    # Initialize state for this chat if not present
    if chat_id not in autoplay_state:
        autoplay_state[chat_id] = {"playlist": [], "index": 0, "seed_id": "", "played_ids": set()}

    state = autoplay_state[chat_id]
    played_ids: set = state.setdefault("played_ids", set())

    # Mark the last played song so it never repeats
    if last_id:
        played_ids.add(last_id)

    # If we have a playlist for the current seed, find next UNPLAYED track
    if state.get("seed_id") == last_id and state.get("playlist"):
        playlist = state["playlist"]
        idx = state.get("index", 0)
        while idx < len(playlist):
            track = playlist[idx]
            idx += 1
            state["index"] = idx
            if track["id"] not in played_ids:
                played_ids.add(track["id"])
                return track
        # All tracks in current playlist exhausted — fall through to fetch fresh ones

    # Fetch fresh mix playlist
    playlist = []
    if last_id:
        playlist = await _fetch_mix_playlist(last_id)

    if not playlist and last_id:
        playlist = await _fetch_mix_innertube(last_id)

    if not playlist:
        # Final fallback: search
        from py_yt import VideosSearch
        clean = re.sub(r"(lyrical|lyrics|official|video|hd|full|song|audio|\|)", "", last_title, flags=re.I)
        clean = re.sub(r"\s+", " ", clean).strip()
        try:
            search = VideosSearch(f"{clean} songs playlist", limit=20)
            results = await search.next()
            if results and results.get("result"):
                for item in results["result"]:
                    vid_id = item.get("id", "")
                    if not vid_id or vid_id == last_id:
                        continue
                    thumbnails = item.get("thumbnails", [])
                    thumbnail = thumbnails[-1].get("url", "").split("?")[0] if thumbnails else _thumb(vid_id)
                    playlist.append({
                        "id": vid_id,
                        "title": item.get("title", "Unknown")[:25],
                        "duration": item.get("duration", ""),
                        "thumbnail": thumbnail,
                        "url": item.get("link", f"https://www.youtube.com/watch?v={vid_id}"),
                    })
        except Exception:
            pass

    if not playlist:
        return None

    # Filter out already-played songs from the fresh playlist
    unplayed = [t for t in playlist if t["id"] not in played_ids]

    if not unplayed:
        return None

    # Save new playlist state, carry forward played_ids so history is preserved
    autoplay_state[chat_id] = {
        "seed_id": last_id,
        "playlist": unplayed,
        "index": 1,       # index 0 is being returned right now
        "played_ids": played_ids,
    }

    track = unplayed[0]
    played_ids.add(track["id"])
    return track


async def _fetch_mix_innertube(video_id: str) -> list[dict]:
    return await _fetch_mix_via_innertube(video_id)


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
        autoplay_state.pop(chat_id, None)   # Reset history on re-enable
        return await m.reply_text(
            f"<b>Autoplay: ON</b>\n\nSimilar songs will play automatically after the current song ends.\n\nBy {m.from_user.mention}",
            reply_markup=_markup(chat_id, True),
        )

    if args in ("off", "disable"):
        await set_autoplay(chat_id, False)
        autoplay_state.pop(chat_id, None)   # Clear history on disable
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
    autoplay_state.pop(chat_id, None)   # Reset history on toggle

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
