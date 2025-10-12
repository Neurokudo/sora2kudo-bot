import os
import logging
import asyncio
from datetime import datetime
from aiohttp import web
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# === CONFIGURATION ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")
TELEGRAM_MODE = os.getenv("TELEGRAM_MODE", "webhook")
PORT = int(os.getenv("PORT", 8080))
DATABASE_URL = os.getenv("DATABASE_URL")
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID", "-1002454833654")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN not found in environment variables")

if not PUBLIC_URL:
    raise RuntimeError("❌ PUBLIC_URL not found in environment variables")

if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL not found in environment variables")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# === DATABASE CONNECTION ===
db_pool = None

async def init_database():
    """Инициализация базы данных и создание таблиц"""
    global db_pool
    
    try:
        logging.info("✅ Connecting to DATABASE_URL...")
        
        # Подключение к базе данных
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        logging.info("✅ Database connected successfully.")
        
        # Создание таблицы users
        async with db_pool.acquire() as conn:
            # Проверяем существование таблицы
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                )
            """)
            
            if not table_exists:
                logging.info("📋 Creating table 'users'...")
                await conn.execute('''
                    CREATE TABLE users (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT UNIQUE,
                        username TEXT,
                        first_name TEXT,
                        plan_name TEXT DEFAULT 'trial',
                        videos_left INT DEFAULT 3,
                        total_payments INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                ''')
                logging.info("✅ Table 'users' created successfully.")
            else:
                logging.info("✅ Table 'users' already exists.")
            
            # Создание индекса для быстрого поиска по user_id
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)
            ''')
            
        logging.info("✅ Table 'users' ready")
        return True
        
    except Exception as e:
        logging.error(f"❌ Database initialization failed: {e}")
        logging.error("⚠️ Bot will continue without database functionality")
        db_pool = None
        return False

async def get_user(user_id: int):
    """Получение пользователя из базы данных"""
    if not db_pool:
        logging.warning("⚠️ Database not available, returning default user data")
        return {
            'user_id': user_id,
            'plan_name': 'trial',
            'videos_left': 3,
            'total_payments': 0
        }
        
    try:
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", user_id
            )
            return user
    except Exception as e:
        logging.error(f"❌ Error getting user {user_id}: {e}")
        return None

async def create_user(user_id: int, username: str = None, first_name: str = None):
    """Создание нового пользователя"""
    if not db_pool:
        logging.warning("⚠️ Database not available, skipping user creation")
        return False
        
    try:
        async with db_pool.acquire() as conn:
            result = await conn.execute('''
                INSERT INTO users (user_id, username, first_name)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id, username, first_name)
            
            if "INSERT" in result:
                logging.info(f"✅ Created new user {user_id} ({first_name})")
            else:
                logging.info(f"✅ User {user_id} already exists")
                
        return True
    except Exception as e:
        logging.error(f"❌ Error creating user {user_id}: {e}")
        return False

async def update_user_videos(user_id: int, videos_left: int):
    """Обновление количества оставшихся видео"""
    if not db_pool:
        logging.warning("⚠️ Database not available, skipping video update")
        return False
        
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE users SET videos_left = $2 WHERE user_id = $1
            ''', user_id, videos_left)
        logging.info(f"✅ Updated user {user_id} videos to {videos_left}")
        return True
    except Exception as e:
        logging.error(f"❌ Error updating user videos {user_id}: {e}")
        return False

# === GLOBAL STATES ===
user_waiting_for_support = set()
user_waiting_for_video_orientation = {}

# === MAIN MENU ===
def main_menu():
    """Главное меню с основными кнопками"""
    kb = [
        [KeyboardButton(text="🎬 Создать видео")],
        [KeyboardButton(text="📘 Примеры"), KeyboardButton(text="💰 Кабинет")],
        [KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def orientation_menu():
    """Меню выбора ориентации видео"""
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 Вертикальное", callback_data="orientation_vertical"),
            InlineKeyboardButton(text="🖥 Горизонтальное", callback_data="orientation_horizontal")
        ]
    ])
    return markup

# === /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Проверяем или создаем пользователя в БД
    user = await get_user(user_id)
    if not user:
        await create_user(user_id, username, first_name)
        user = await get_user(user_id)
    
    # Формируем приветственное сообщение
    welcome_text = (
        f"👋 Привет, {first_name or 'друг'}! Это <b>SORA 2 от Neurokudo</b>.\n\n"
        f"🎬 <b>Твой пакет:</b> {user['plan_name'] if user else 'trial'}\n"
        f"🎞 <b>Осталось видео:</b> {user['videos_left'] if user else 3}\n\n"
        "Здесь ты можешь создавать видео по описанию — просто напиши, что хочешь снять.\n\n"
        "💡 <b>Выбери действие:</b>"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=main_menu()
    )
    
    # Показываем кнопки ориентации
    await message.answer(
        "📐 <b>Выбери ориентацию для будущих видео:</b>",
        reply_markup=orientation_menu()
    )

# === /help ===
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    user_waiting_for_support.add(message.from_user.id)
    await message.answer(
        "🧭 <b>Помощь</b>\n\n"
        "Опиши свою проблему, я постараюсь помочь скоро!",
        reply_markup=main_menu()
    )

# === CALLBACK: Orientation choice ===
@dp.callback_query()
async def orientation_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if callback.data == "orientation_vertical":
        user_waiting_for_video_orientation[user_id] = "vertical"
        await callback.message.edit_text(
            "✅ <b>Выбрана вертикальная ориентация</b>\n\n"
            "Теперь нажми <b>🎬 Создать видео</b> и напиши, что хочешь снять!",
            parse_mode="HTML"
        )
    elif callback.data == "orientation_horizontal":
        user_waiting_for_video_orientation[user_id] = "horizontal"
        await callback.message.edit_text(
            "✅ <b>Выбрана горизонтальная ориентация</b>\n\n"
            "Теперь нажми <b>🎬 Создать видео</b> и напиши, что хочешь снять!",
            parse_mode="HTML"
        )
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

    # Обработка кнопок меню
    if text == "🎬 Создать видео":
        await handle_create_video(message)
    elif text == "📘 Примеры":
        await handle_examples(message)
    elif text == "💰 Кабинет":
        await handle_profile(message)
    elif text == "❓ Помощь":
        await cmd_help(message)
    else:
        # Если пользователь выбрал ориентацию, то это описание для видео
        if user_id in user_waiting_for_video_orientation and user_waiting_for_video_orientation[user_id]:
            await handle_video_description(message)
        else:
            await message.answer(
                "💡 Используй кнопки меню или выбери ориентацию видео!",
                reply_markup=main_menu()
            )

async def handle_create_video(message: types.Message):
    """Обработка кнопки 'Создать видео'"""
    user_id = message.from_user.id
    
    # Проверяем, выбрана ли ориентация
    if user_id not in user_waiting_for_video_orientation or not user_waiting_for_video_orientation[user_id]:
        await message.answer(
            "📐 <b>Сначала выбери ориентацию видео:</b>",
            reply_markup=orientation_menu()
        )
        return
    
    # Проверяем лимиты
    user = await get_user(user_id)
    if user and user['videos_left'] <= 0:
        await message.answer(
            "🚫 <b>У тебя закончились видео!</b>\n\n"
            "💳 Купи новый пакет в <b>💰 Кабинет</b>",
            reply_markup=main_menu()
        )
        return
    
    await message.answer(
        "🎬 <b>Создание видео</b>\n\n"
        "📐 Ориентация: <b>{}</b>\n"
        "🎞 Осталось видео: <b>{}</b>\n\n"
        "✏️ <b>Опиши, что хочешь снять:</b>\n"
        "Например: <code>Рыбаки вытаскивают сеть, в ней русалка</code>".format(
            "вертикальная" if user_waiting_for_video_orientation[user_id] == "vertical" else "горизонтальная",
            user['videos_left'] if user else 3
        ),
        reply_markup=main_menu()
    )

async def handle_examples(message: types.Message):
    """Обработка кнопки 'Примеры'"""
    await message.answer(
        "📘 <b>Примеры идей для видео:</b>\n\n"
        "🔹 Рыбаки вытаскивают сеть, в ней странное существо\n"
        "🔹 Грибники находят движущуюся массу под листьями\n"
        "🔹 Бабушка кормит капибару у окна, рассвет\n"
        "🔹 Советские рабочие открывают капсулу времени\n"
        "🔹 Дети находят портал в другой мир\n"
        "🔹 Старый дом с привидениями, ночь\n\n"
        "💡 <b>Теперь создавай свое видео!</b>",
        reply_markup=main_menu()
    )

async def handle_profile(message: types.Message):
    """Обработка кнопки 'Кабинет'"""
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await message.answer("❌ Ошибка получения данных. Попробуй /start")
        return
    
    profile_text = (
        "💰 <b>Твой кабинет</b>\n\n"
        f"👤 Имя: <b>{user['first_name'] or 'Не указано'}</b>\n"
        f"📦 Пакет: <b>{user['plan_name']}</b>\n"
        f"🎞 Осталось видео: <b>{user['videos_left']}</b>\n"
        f"💳 Всего оплачено: <b>{user['total_payments']} ₽</b>\n"
        f"📅 Регистрация: <b>{user['created_at'].strftime('%d.%m.%Y')}</b>\n\n"
        "🔁 <b>Нужно больше видео?</b>\n"
        "Выбери пакет:\n"
        "🐣 Пробный — 3 видео → ₽490\n"
        "🎬 Базовый — 10 видео → ₽1 290\n"
        "🚀 Максимум — 30 видео → ₽2 990"
    )
    
    await message.answer(profile_text, reply_markup=main_menu())

async def handle_video_description(message: types.Message):
    """Обработка описания видео"""
    user_id = message.from_user.id
    text = message.text.strip()
    orientation = user_waiting_for_video_orientation.get(user_id)
    
    # Получаем данные пользователя
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Ошибка. Попробуй /start")
        return
    
    if user['videos_left'] <= 0:
        await message.answer(
            "🚫 <b>У тебя закончились видео!</b>\n\n"
            "💳 Купи новый пакет в <b>💰 Кабинет</b>",
            reply_markup=main_menu()
        )
        return
    
    # Уменьшаем количество видео
    await update_user_videos(user_id, user['videos_left'] - 1)
    
    await message.answer(
        f"🎬 <b>Принято описание!</b>\n\n"
        f"📝 <b>Описание:</b> {text}\n"
        f"📐 <b>Ориентация:</b> {'вертикальная' if orientation == 'vertical' else 'горизонтальная'}\n"
        f"🎞 <b>Осталось видео:</b> {user['videos_left'] - 1}\n\n"
        "⏳ Видео создается через Sora 2...\n"
        "📨 Результат будет отправлен сюда!",
        reply_markup=main_menu()
    )
    
    # Очищаем состояние
    if user_id in user_waiting_for_video_orientation:
        del user_waiting_for_video_orientation[user_id]

# === WEBHOOK HANDLERS ===
async def handle_webhook(request):
    """Обработчик webhook от Telegram"""
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return web.Response()
    except Exception as e:
        logging.error(f"❌ Ошибка в webhook: {e}")
        return web.Response(status=500)

async def health(request):
    """Health check для Railway"""
    return web.Response(text="OK")

# === WEB APPLICATION ===
def create_app():
    """Создание веб-приложения"""
    app = web.Application()
    
    # Маршруты
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/health", health)
    
    return app

# === MAIN FUNCTION ===
async def start_bot():
    """Запуск бота в webhook или polling режиме"""
    logging.info("🚀 Launching sora2kudo-bot...")
    
    # Инициализация базы данных
    db_ready = await init_database()
    if not db_ready:
        logging.warning("⚠️ Database initialization failed, bot will continue with limited functionality")
    
    if TELEGRAM_MODE == "webhook":
        # Webhook режим для Railway
        logging.info(f"🌐 Setting up webhook: {PUBLIC_URL}/webhook")
        await bot.set_webhook(f"{PUBLIC_URL}/webhook")
        logging.info("✅ Webhook установлен")
        
        # Создаем веб-приложение
        app = create_app()
        
        # Запускаем веб-сервер
        logging.info(f"🚀 Starting web server on port {PORT}")
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        
        logging.info("🚀 Bot is running.")
        
        # Держим сервер запущенным
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logging.info("🛑 Stopping bot...")
            await runner.cleanup()
            if db_pool:
                await db_pool.close()
    else:
        # Polling режим для локальной разработки
        logging.info("🔄 Starting bot in polling mode")
        try:
            await dp.start_polling(bot)
        except KeyboardInterrupt:
            logging.info("🛑 Stopping bot...")
            if db_pool:
                await db_pool.close()

if __name__ == "__main__":
    asyncio.run(start_bot())