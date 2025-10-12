import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# === CONFIGURATION ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID", "-1002454833654")  # группа поддержки
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN not found in environment variables")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# === SIMPLE REPLY MENU ===
def reply_menu():
    kb = [
        [KeyboardButton(text="🎬 Меню"), KeyboardButton(text="💰 Оплата")],
        [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="👤 Кабинет")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# === GLOBAL STATES ===
user_waiting_for_support = set()
user_waiting_for_video_orientation = {}

# === /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Это <b>SORA 2 от Neurokudo</b>.\n\n"
        "Здесь ты можешь создавать видео по описанию — просто напиши, что хочешь снять.\n"
        "Пример:\n<code>Рыбаки вытаскивают сеть, в ней русалка, съёмка на телефон</code>\n\n"
        "🎥 Хочешь пошаговую инструкцию? → /instructions",
        reply_markup=reply_menu()
    )

# === /help ===
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    user_waiting_for_support.add(message.from_user.id)
    await message.answer("🧭 Опиши свою проблему, я постараюсь помочь скоро!")

# === /instructions ===
@dp.message(Command("instructions"))
async def cmd_instructions(message: types.Message):
    await message.answer(
        "💡 Всё просто:\n"
        "1️⃣ Напиши идею видео.\n"
        "2️⃣ Выбери ориентацию видео (вертикальная или горизонтальная).\n"
        "3️⃣ Бот превратит твоё описание в видео.\n\n"
        "Хочешь примеры описаний? → /templates"
    )

# === /templates ===
@dp.message(Command("templates"))
async def cmd_templates(message: types.Message):
    await message.answer(
        "📘 Примеры идей для видео:\n\n"
        "🔹 Рыбаки вытаскивают сеть, в ней странное существо.\n"
        "🔹 Грибники находят движущуюся массу под листьями.\n"
        "🔹 Бабушка кормит капибару у окна, рассвет.\n"
        "🔹 Советские рабочие открывают капсулу времени.\n\n"
        "Теперь попробуй сам → /video"
    )

# === /buy ===
@dp.message(Command("buy"))
async def cmd_buy(message: types.Message):
    await message.answer(
        "💰 Выбери пакет:\n\n"
        "🐣 Пробный — 3 видео → ₽490\n"
        "🎬 Базовый — 10 видео → ₽1 290\n"
        "🚀 Максимум — 30 видео → ₽2 990\n\n"
        "После оплаты пакет активируется сразу.\n"
        "Купить → /buy",
        reply_markup=reply_menu()
    )

# === /profile ===
@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    await message.answer(
        "👤 Кабинет\n"
        "🎞 Осталось видео: {placeholder}\n"
        "💡 Текущий пакет: {plan_name}\n"
        "💰 Всего оплачено: {total_payments} ₽\n\n"
        "🔁 Купить ещё → /buy\n"
        "🧠 Инструкция → /instructions\n"
        "📘 Примеры → /templates"
    )

# === /video ===
@dp.message(Command("video"))
async def cmd_video(message: types.Message):
    user_waiting_for_video_orientation[message.from_user.id] = None
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 Вертикальное", callback_data="orientation_vertical"),
            InlineKeyboardButton(text="🖥 Горизонтальное", callback_data="orientation_horizontal")
        ]
    ])
    await message.answer("📐 Выбери ориентацию будущего видео:", reply_markup=markup)

# === CALLBACK: Orientation choice ===
@dp.callback_query()
async def orientation_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if callback.data == "orientation_vertical":
        user_waiting_for_video_orientation[user_id] = "vertical"
        await callback.message.answer("✅ Выбрана вертикальная ориентация.\n\nТеперь напиши, что хочешь снять.")
    elif callback.data == "orientation_horizontal":
        user_waiting_for_video_orientation[user_id] = "horizontal"
        await callback.message.answer("✅ Выбрана горизонтальная ориентация.\n\nТеперь напиши, что хочешь снять.")
    await callback.answer()

# === DEFAULT HANDLER ===
@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Если пользователь сейчас пишет в поддержку
    if user_id in user_waiting_for_support:
        username = message.from_user.username or "без ника"
        full_name = message.from_user.full_name
        chat_text = (
            f"📩 <b>Новое сообщение в поддержку</b>\n\n"
            f"👤 Пользователь: @{username} ({full_name})\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"💬 Сообщение:\n{text}"
        )
        try:
            await bot.send_message(SUPPORT_CHAT_ID, chat_text, parse_mode="HTML")
            await message.answer("✅ Сообщение отправлено. Я постараюсь ответить как можно скорее!")
        except Exception as e:
            logging.error(f"Ошибка при отправке в поддержку: {e}")
            await message.answer("⚠️ Не удалось отправить сообщение. Попробуй позже.")
        user_waiting_for_support.remove(user_id)
        return

    # Если пользователь выбрал ориентацию, то это описание для видео
    if user_id in user_waiting_for_video_orientation and user_waiting_for_video_orientation[user_id]:
        orientation = user_waiting_for_video_orientation[user_id]
        await message.answer(
            f"🎬 Принято описание!\n"
            f"📐 Ориентация: <b>{'вертикальная' if orientation == 'vertical' else 'горизонтальная'}</b>\n"
            f"Видео будет создано через Sora 2 и отправлено сюда.\n\n"
            "💡 Пример описания: <code>Рыбаки в лодке поймали русалку</code>"
        )
        # После генерации очистим состояние
        del user_waiting_for_video_orientation[user_id]
        return

    # Если пользователь пишет команду
    if any(k in text.lower() for k in ["меню", "оплата", "помощь", "кабинет"]):
        await cmd_start(message)
    else:
        await message.answer(
            "✏️ Опиши идею или используй команду /video, чтобы выбрать ориентацию."
        )

# === ENTRYPOINT ===
async def start_bot():
    logging.info("🚀 Launching sora2kudo-bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(start_bot())