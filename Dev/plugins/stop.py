from pyrogram import filters, types

from Dev import unnati, app, db, lang
from Dev.helpers import can_manage_vc


@app.on_message(filters.command(["end", "bc"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _stop(_, m: types.Message):
    if len(m.command) > 1:
        return
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_dev"])

    await unnati.stop(m.chat.id)
    await m.reply_text(m.lang["play_stopped"].format(m.from_user.mention))
