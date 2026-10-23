import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

import database as db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}

logging.basicConfig(level=logging.INFO)

router = Router()
is_admin = F.from_user.id.in_(ADMIN_IDS)


class AddMovie(StatesGroup):
    video = State()
    code = State()
    title = State()


class AddChannel(StatesGroup):
    chat = State()


# ---------- Umumiy yordamchi funksiyalar ----------

async def get_unsubscribed(bot: Bot, user_id: int) -> list[dict]:
    """Foydalanuvchi a'zo bo'lmagan majburiy kanallar ro'yxatini qaytaradi."""
    missing = []
    for ch in await db.list_channels():
        try:
            member = await bot.get_chat_member(ch["chat_id"], user_id)
            if member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
                missing.append(ch)
        except Exception:
            logging.exception("Kanalni tekshirib bo'lmadi: %s", ch["chat_id"])
            missing.append(ch)
    return missing


def subscribe_keyboard(channels: list[dict], code: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"📢 {ch['title'] or 'Kanal'}", url=ch["invite_link"])]
        for ch in channels
    ]
    rows.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data=f"check:{code}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_movie(bot: Bot, chat_id: int, movie: dict) -> None:
    await bot.send_video(
        chat_id,
        movie["file_id"],
        caption=movie["title"] or None,
    )


ADMIN_HELP = (
    "<b>Admin buyruqlari:</b>\n"
    "/add_movie - yangi kino qo'shish (video + kod)\n"
    "/movies - kinolar ro'yxati\n"
    "/del_movie KOD - kinoni o'chirish\n"
    "/add_channel - majburiy obuna kanali qo'shish\n"
    "/channels - kanallar ro'yxati va o'chirish\n"
    "/cancel - joriy amalni bekor qilish"
)


# ---------- Umumiy buyruqlar ----------

@router.message(CommandStart())
async def cmd_start(message: Message):
    text = "Assalomu alaykum! Kino kodini yuboring."
    if message.from_user.id in ADMIN_IDS:
        text += "\n\n" + ADMIN_HELP
    await message.answer(text)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.")


@router.message(Command("help"), is_admin)
async def cmd_help(message: Message):
    await message.answer(ADMIN_HELP)


# ---------- Admin: kino qo'shish ----------

@router.message(Command("add_movie"), is_admin)
async def add_movie_start(message: Message, state: FSMContext):
    await state.set_state(AddMovie.video)
    await message.answer("Kino videosini yuboring (video sifatida).")


@router.message(AddMovie.video, is_admin, F.video)
async def add_movie_video(message: Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await state.set_state(AddMovie.code)
    await message.answer("Endi kino kodini yuboring (masalan: 101).")


@router.message(AddMovie.video, is_admin)
async def add_movie_video_wrong(message: Message):
    await message.answer("Iltimos, video yuboring yoki /cancel bosing.")


@router.message(AddMovie.code, is_admin, F.text)
async def add_movie_code(message: Message, state: FSMContext):
    code = message.text.strip().lower()
    if not code or " " in code or code.startswith("/"):
        await message.answer("Kod bo'sh bo'lmasligi va bo'shliqsiz bo'lishi kerak. Qayta yuboring.")
        return
    if await db.get_movie(code):
        await message.answer("Bu kod band. Boshqa kod yuboring.")
        return
    await state.update_data(code=code)
    await state.set_state(AddMovie.title)
    await message.answer("Kino nomini yuboring (yoki \"-\" deb yozing, nomsiz qoldirish uchun).")


@router.message(AddMovie.title, is_admin, F.text)
async def add_movie_title(message: Message, state: FSMContext):
    data = await state.get_data()
    title = None if message.text.strip() == "-" else message.text.strip()
    await db.add_movie(data["code"], title, data["file_id"])
    await state.clear()
    await message.answer(f"Kino saqlandi. Kod: <code>{data['code']}</code>")


# ---------- Admin: kinolar ----------

@router.message(Command("movies"), is_admin)
async def list_movies(message: Message):
    movies = await db.list_movies()
    if not movies:
        await message.answer("Hali kino qo'shilmagan.")
        return
    lines = [f"<code>{m['code']}</code> - {m['title'] or 'nomsiz'}" for m in movies]
    await message.answer("\n".join(lines))


@router.message(Command("del_movie"), is_admin)
async def del_movie(message: Message, command: CommandObject):
    code = (command.args or "").strip().lower()
    if not code:
        await message.answer("Foydalanish: /del_movie KOD")
        return
    ok = await db.delete_movie(code)
    await message.answer("O'chirildi." if ok else "Bunday kod topilmadi.")


# ---------- Admin: kanallar ----------

@router.message(Command("add_channel"), is_admin)
async def add_channel_start(message: Message, state: FSMContext):
    await state.set_state(AddChannel.chat)
    await message.answer(
        "Kanalni qo'shing:\n"
        "- kanaldan xabarni forward qiling, yoki\n"
        "- kanal username sini yuboring (masalan: @mening_kanalim)\n\n"
        "Bot kanalda admin bo'lishi shart."
    )


@router.message(AddChannel.chat, is_admin)
async def add_channel_receive(message: Message, state: FSMContext, bot: Bot):
    if message.forward_from_chat:
        chat_ref = message.forward_from_chat.id
    else:
        raw = (message.text or "").strip()
        if not raw:
            await message.answer("Kanal username yoki forward xabar yuboring.")
            return
        chat_ref = int(raw) if raw.lstrip("-").isdigit() else raw

    try:
        chat = await bot.get_chat(chat_ref)
        me = await bot.get_chat_member(chat.id, bot.id)
    except Exception:
        logging.exception("Kanal topilmadi: %s", chat_ref)
        await message.answer("Kanal topilmadi yoki bot unga kira olmaydi. Qayta urinib ko'ring.")
        return

    if me.status != ChatMemberStatus.ADMINISTRATOR:
        await message.answer("Bot bu kanalda admin emas. Avval botni admin qiling.")
        return

    if chat.username:
        link = f"https://t.me/{chat.username}"
    else:
        link = (await bot.create_chat_invite_link(chat.id)).invite_link

    await db.add_channel(chat.id, chat.title, link)
    await state.clear()
    await message.answer(f"Kanal qo'shildi: {chat.title}")


@router.message(Command("channels"), is_admin)
async def list_channels(message: Message):
    channels = await db.list_channels()
    if not channels:
        await message.answer("Majburiy obuna kanallari yo'q.")
        return
    rows = [
        [InlineKeyboardButton(text=f"🗑 {ch['title'] or ch['chat_id']}", callback_data=f"delch:{ch['chat_id']}")]
        for ch in channels
    ]
    await message.answer(
        "Kanalni o'chirish uchun tugmasini bosing:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("delch:"), is_admin)
async def cb_delete_channel(callback: CallbackQuery):
    chat_id = int(callback.data.split(":", 1)[1])
    ok = await db.delete_channel(chat_id)
    await callback.answer("O'chirildi" if ok else "Topilmadi", show_alert=False)
    await callback.message.edit_text("Kanal o'chirildi." if ok else "Kanal topilmadi.")


# ---------- Foydalanuvchi: kod yuborish ----------

@router.callback_query(F.data.startswith("check:"))
async def cb_check(callback: CallbackQuery, bot: Bot):
    code = callback.data.split(":", 1)[1]
    movie = await db.get_movie(code)
    if not movie:
        await callback.answer("Kino topilmadi.", show_alert=True)
        return

    missing = await get_unsubscribed(bot, callback.from_user.id)
    if missing:
        await callback.answer("Hali barcha kanallarga a'zo bo'lmagansiz.", show_alert=True)
        return

    await callback.answer()
    await callback.message.delete()
    await send_movie(bot, callback.from_user.id, movie)


@router.message(F.text, ~F.text.startswith("/"))
async def user_code(message: Message, bot: Bot):
    code = message.text.strip().lower()
    movie = await db.get_movie(code)
    if not movie:
        await message.answer("Bunday kod topilmadi. Kodni tekshirib qayta yuboring.")
        return

    missing = await get_unsubscribed(bot, message.from_user.id)
    if missing:
        await message.answer(
            "Kinoni olish uchun quyidagi kanallarga a'zo bo'ling, so'ng \"Tekshirish\" tugmasini bosing:",
            reply_markup=subscribe_keyboard(missing, code),
        )
        return

    await send_movie(bot, message.chat.id, movie)


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN .env faylda ko'rsatilmagan.")
    if not ADMIN_IDS:
        logging.warning("ADMIN_IDS bo'sh: admin buyruqlari ishlamaydi.")

    await db.init_db()

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
