import asyncio
import time

from pyrogram import enums, filters, types

from Dev import unnati, app, config, db, lang, queue, tasks, userbot, yt
from Dev.helpers import buttons
from Dev.plugins.loop import get_loop, set_loop



@app.on_message(filters.video_chat_started, group=19)
@app.on_message(filters.video_chat_ended, group=20)
async def _watcher_vc(_, m: types.Message):
    await unnati.stop(m.chat.id)


async def auto_leave():
    while True:
        await asyncio.sleep(1800)
        for ub in userbot.clients:
            left = 0
            try:
                for dialog in await ub.get_dialogs():
                    chat_id = dialog.chat.id
                    if left >= 20:
                        break
                    if chat_id in [app.logger, -1003199377375, -1002117705202]:
                        continue
                    if dialog.chat.type in [
                        enums.ChatType.GROUP,
                        enums.ChatType.SUPERGROUP,
                    ]:
                        if chat_id in db.active_calls:
                            continue
                        await ub.leave_chat(chat_id)
                        left += 1
                    await asyncio.sleep(5)
            except:
                continue


async def track_time():
    while True:
        await asyncio.sleep(1)
        for chat_id in db.active_calls:
            if not await db.playing(chat_id):
                continue
            media = queue.get_current(chat_id)
            if not media:
                continue
            media.time += 1


async def update_timer(length=10):
    while True:
        await asyncio.sleep(7)

        for chat_id in db.active_calls:
            if not await db.playing(chat_id):
                continue

            try:
                media = queue.get_current(chat_id)
                if not media:
                    continue

                duration = media.duration_sec
                message_id = media.message_id

                if not duration or not message_id or not media.time:
                    continue

                played = media.time
                remaining = duration - played

                pos = min(int((played / duration) * length), length - 1)
                bar = "—" * pos + "◉" + "—" * (length - pos - 1)

                # ⏳ Preload next
                if remaining <= 30:
                    nxt = queue.get_next(chat_id, check=True)
                    if nxt and not nxt.file_path:
                        nxt.file_path = await yt.download(nxt.id, video=nxt.video)

                # 🔁 LOOP / NEXT
                if remaining < 1:
                    loop_count = await get_loop(chat_id)

                    if loop_count > 0:
                        current = queue.get_current(chat_id)
                        if current:
                            current.time = 0
                            await set_loop(chat_id, loop_count - 1)

                            await unnati.play_media(
                                chat_id=chat_id,
                                message=None,
                                media=current,
                            )
                            continue

                    await unnati.play_next(chat_id)
                    continue

                timer = (
                    f"{time.strftime('%M:%S', time.gmtime(played))}"
                    f" | {bar} | -{time.strftime('%M:%S', time.gmtime(remaining))}"
                )

                await app.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=buttons.controls(
                        chat_id=chat_id,
                        timer=timer,
                        remove=False,
                    ),
                )

            except Exception as e:
                print("TIMER ERROR:", e)
                

async def vc_watcher(sleep=15):
    while True:
        await asyncio.sleep(sleep)
        for chat_id in db.active_calls:
            client = await db.get_assistant(chat_id)
            played = await client.time(chat_id)
            participants = await client.get_participants(chat_id)
            if len(participants) < 2 and played > 30:
                _lang = await lang.get_lang(chat_id)
                sent = await app.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=queue.get_current(chat_id).message_id,
                    reply_markup=buttons.controls(
                        chat_id=chat_id, status=_lang["stopped"], remove=True
                    ),
                )
                await unnati.stop(chat_id)
                await sent.reply_text(_lang["auto_left"])


if config.AUTO_END:
    tasks.append(asyncio.create_task(vc_watcher()))
if config.AUTO_LEAVE:
    tasks.append(asyncio.create_task(auto_leave()))
tasks.append(asyncio.create_task(track_time()))
tasks.append(asyncio.create_task(update_timer()))
