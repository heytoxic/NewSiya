from pyrogram import filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from Dev import app, lang, db

# ───────────────────────────────────────────────
# In-memory autoplay state  {chat_id: True/False}
# ───────────────────────────────────────────────
autoplay_db: dict[int, bool] = {}


# ── helpers ────────────────────────────────────

async def get_autoplay(chat_id: int) -> bool:
    if chat_id not in autoplay_db:
        autoplay_db[chat_id] = await db.get_autoplay(chat_id)
    return autoplay_db[chat_id]


async def set_autoplay(chat_id: int, state: bool) -> None:
    autoplay_db[chat_id] = state
    await db.set_autoplay(chat_id, state)


def _markup(chat_id: int, state: bool):
    btn_text = "🔴 Turn OFF" if state else "🟢 Turn ON"
    cb_data  = f"autoplay_off_{chat_id}" if state else f"autoplay_on_{chat_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_text, callback_data=cb_data)],
        [InlineKeyboardButton("✖ Close", callback_data="autoplay_close")],
    ])


# ── /autoplay command ──────────────────────────

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
            f"✅ <b>Autoplay ON</b>\n\n"
            f"Ab jab current song khatam hoga, automatically similar songs bajte rahenge!\n\n"
            f"By {m.from_user.mention}",
            reply_markup=_markup(chat_id, True),
        )

    if args in ("off", "disable"):
        await set_autoplay(chat_id, False)
        return await m.reply_text(
            f"❌ <b>Autoplay OFF</b>\n\nBy {m.from_user.mention}",
            reply_markup=_markup(chat_id, False),
        )

    # No arg → show current status
    status = "🟢 <b>ON</b>" if state else "🔴 <b>OFF</b>"
    await m.reply_text(
        f"🎵 <b>Autoplay Status:</b> {status}\n\n"
        f"<b>Usage:</b>\n"
        f"• /autoplay on  – Autoplay enable karo\n"
        f"• /autoplay off – Autoplay band karo",
        reply_markup=_markup(chat_id, state),
    )


# ── Inline button callbacks ────────────────────

@app.on_callback_query(filters.regex(r"^autoplay_(on|off)_(-?\d+)$"))
async def autoplay_cb(_, q: CallbackQuery):
    action  = q.matches[0].group(1)   # "on" or "off"
    chat_id = int(q.matches[0].group(2))
    user_id = q.from_user.id

    # Only admins / sudoers can toggle
    admin_list = await db.get_admins(chat_id)
    if user_id not in admin_list and user_id not in app.sudoers:
        return await q.answer("❌ Sirf admins autoplay toggle kar sakte hain!", show_alert=True)

    new_state = (action == "on")
    await set_autoplay(chat_id, new_state)

    status_text = "🟢 ON" if new_state else "🔴 OFF"
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
        await q.answer("Can't close", show_alert=True)
