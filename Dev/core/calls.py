from ntgcalls import ConnectionNotFound, TelegramServerError
from pyrogram.errors import MessageIdInvalid
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from Dev import app, config, db, lang, logger, queue, userbot, yt
from Dev.helpers import Media, Track, buttons, thumb
from Dev.plugins.loop import get_loop, set_loop

class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=True)
        return await client.pause(chat_id)

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=False)
        return await client.resume(chat_id)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        try:
            queue.clear(chat_id)
            await db.remove_call(chat_id)
        except:
            pass

        try:
            await client.leave_call(chat_id, close=False)
        except:
            pass


    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
    ) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = (
            await thumb.generate(media)
            if isinstance(media, Track)
            else config.DEFAULT_THUMB
        )

        if not media.file_path:
            return await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))

        stream = types.MediaStream(
            media_path=media.file_path,
            audio_parameters=types.AudioQuality.HIGH,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(
                types.MediaStream.Flags.AUTO_DETECT
                if media.video
                else types.MediaStream.Flags.IGNORE
            ),
            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
        )
        try:
            await client.play(
                chat_id=chat_id,
                stream=stream,
                config=types.GroupCallConfig(auto_start=False),
            )
            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)
                await db.set_last_played(chat_id, media.title)  # 🎵 autoplay ke liye
                text = _lang["play_media"].format(
                    media.url,
                    media.title,
                    media.duration,
                    media.user,
                )
                keyboard = buttons.controls(chat_id)
                try:
                    await message.edit_media(
                        media=InputMediaPhoto(
                            media=_thumb,
                            caption=text,
                        ),
                        reply_markup=keyboard,
                    )
                except MessageIdInvalid:
                    media.message_id = (await app.send_photo(
                        chat_id=chat_id,
                        photo=_thumb,
                        caption=text,
                        reply_markup=keyboard,
                    )).id
        except FileNotFoundError:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            await self.play_next(chat_id)
        except exceptions.NoActiveGroupCall:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_no_call"])
        except exceptions.NoAudioSourceFound:
            await message.edit_text(_lang["error_no_audio"])
            await self.play_next(chat_id)
        except (ConnectionNotFound, TelegramServerError):
            await self.stop(chat_id)
            await message.edit_text(_lang["error_tg_server"])


    async def replay(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return

        media = queue.get_current(chat_id)
        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
        await self.play_media(chat_id, msg, media)

    async def play_next(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return

        # 🔁 LOOP CHECK
        loop_count = await get_loop(chat_id)
        current = queue.get_current(chat_id)

        if loop_count > 0 and current:
            current.time = 0
            await set_loop(chat_id, loop_count - 1)

            _lang = await lang.get_lang(chat_id)
            msg = await app.send_message(
                chat_id=chat_id,
                text=_lang["play_again"]
            )

            current.message_id = msg.id
            await self.play_media(chat_id, msg, current)
            return

        # ⏭️ NORMAL NEXT FLOW
        media = queue.get_next(chat_id)

        try:
            if media and media.message_id:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=media.message_id,
                    revoke=True,
                )
                media.message_id = 0
        except Exception:
            pass

        if not media:
            # 🎵 AUTOPLAY CHECK — queue khatam, dekho autoplay ON hai ya nahi
            if await db.get_autoplay(chat_id):
                await self._autoplay_next(chat_id)
            else:
                await self.stop(chat_id)
            return

        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(
            chat_id=chat_id,
            text=_lang["play_next"]
        )

        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
            if not media.file_path:
                await self.stop(chat_id)
                await msg.edit_text(
                    _lang["error_no_file"].format(config.SUPPORT_CHAT)
                )
                return

        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)
    

    async def _autoplay_next(self, chat_id: int) -> None:
        """
        Autoplay: last played track ke title se similar song search karo
        aur queue mein add karke play karo.
        """
        from Dev.plugins.autoplay import get_autoplay  # circular-import se bachne ke liye yahan import

        # Double check — autoplay still ON?
        if not await get_autoplay(chat_id):
            await self.stop(chat_id)
            return

        # Last played track ka title/id lo  (queue already cleared, isliye
        # hum db se last_title lenge jo humne save kiya hai)
        last_title = await db.get_last_played(chat_id)
        if not last_title:
            await self.stop(chat_id)
            return

        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(
            chat_id=chat_id,
            text=f"🎵 <b>Autoplay:</b> <i>{last_title}</i> jaisi song dhundh raha hoon...",
        )

        # YouTube se related song search karo
        track = await yt.search(last_title + " similar songs", msg.id, video=False)
        if not track:
            await self.stop(chat_id)
            await msg.edit_text("❌ Autoplay: Koi similar song nahi mila.")
            return

        track.user = "🤖 Autoplay"
        track.message_id = msg.id
        queue.force_add(chat_id, track)

        if not track.file_path:
            track.file_path = await yt.download(track.id, video=False)
            if not track.file_path:
                await self.stop(chat_id)
                await msg.edit_text("❌ Autoplay: Download fail ho gaya.")
                return

        await self.play_media(chat_id, msg, track)

    async def ping(self) -> float:
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 2)


    async def decorators(self, client: PyTgCalls) -> None:
        for client in self.clients:

            @client.on_update()
            async def update_handler(_, update: types.Update) -> None:
                if isinstance(update, types.StreamEnded):
                    if update.stream_type == types.StreamEnded.Type.AUDIO:
                        await self.play_next(update.chat_id)
                elif isinstance(update, types.ChatUpdate):
                    if update.status in [
                        types.ChatUpdate.Status.KICKED,
                        types.ChatUpdate.Status.LEFT_GROUP,
                        types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                    ]:
                        await self.stop(update.chat_id)


    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("Toxic PyTgCalls client(s) started.")
