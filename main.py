import os
import logging
import asyncio
import uuid
import json
from datetime import datetime
import aiohttp
from aiohttp import web
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from yookassa import Configuration, Payment

# Импорт модулей для мультиязычности
from translations import get_text, is_rtl_language
from utils.keyboards import main_menu, language_selection, orientation_menu, tariff_selection

# Импорт Sora client
from sora_client import create_sora_task, extract_user_from_param

# === CONFIGURATION ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")
TELEGRAM_MODE = os.getenv("TELEGRAM_MODE", "webhook")
PORT = int(os.getenv("PORT", 8080))
DATABASE_URL = os.getenv("DATABASE_URL")
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID", "-1002454833654")

# YooKassa configuration
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# Tribute configuration
TRIBUTE_API_KEY = os.getenv("TRIBUTE_API_KEY")

# Sora 2 API configuration
SORA_API_KEY = os.getenv("SORA_API_KEY")
SORA_API_URL = os.getenv("SORA_API_URL", "https://api.sora2.com/v1/videos")

# KIE.AI Sora-2 configuration
KIE_API_KEY = os.getenv("KIE_API_KEY")
KIE_API_URL = os.getenv("KIE_API_URL", "https://api.kie.ai/api/v1/jobs/createTask")

# === TARIFF CONFIGURATION ===
tariff_videos = {
    "trial": 3,
    "basic": 10,
    "maximum": 30
}

tariff_prices = {
    "trial": 390,
    "basic": 990,
    "maximum": 2190
}

tariff_names = {
    "trial": "🌱 Пробный",
    "basic": "✨ Базовый",
    "maximum": "💎 Максимум"
}

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN not found in environment variables")

if not PUBLIC_URL:
    raise RuntimeError("❌ PUBLIC_URL not found in environment variables")

if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL not found in environment variables")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Настройка YooKassa
if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY
    logging.info("✅ YooKassa configured")
else:
    logging.warning("⚠️ YooKassa credentials not found, payments will be disabled")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# === DATABASE CONNECTION ===
db_pool = None

async def init_database():
    """Инициализация базы данных и создание таблиц"""
    global db_pool
    
    try:
        logging.info("✅ Connecting to DATABASE_URL...")
        logging.info(f"🔍 DATABASE_URL format: {DATABASE_URL[:20]}...{DATABASE_URL[-10:]}")
        
        # Подключение к базе данных с таймаутом
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            command_timeout=10
        )
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
                                plan_name TEXT DEFAULT 'Без тарифа',
                                videos_left INT DEFAULT 0,
                                total_payments INT DEFAULT 0,
                                language TEXT DEFAULT 'en',
                                created_at TIMESTAMP DEFAULT NOW()
                            )
                ''')
                logging.info("✅ Table 'users' created successfully.")
            else:
                logging.info("✅ Table 'users' already exists.")
                # Добавляем поле language если его нет
                await conn.execute('''
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'en'
                ''')
                logging.info("✅ Language column checked/added.")
                
                # Обновляем всех пользователей с trial на "Без тарифа"
                await conn.execute('''
                    UPDATE users SET plan_name = 'Без тарифа', videos_left = 0 
                    WHERE plan_name = 'trial'
                ''')
                trial_users_updated = await conn.fetchval('''
                    SELECT COUNT(*) FROM users WHERE plan_name = 'Без тарифа'
                ''')
                if trial_users_updated and trial_users_updated > 0:
                    logging.info(f"✅ Updated {trial_users_updated} users from 'trial' to 'Без тарифа'")
            
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
            'plan_name': 'Без тарифа',
            'videos_left': 0,
            'total_payments': 0,
            'language': 'en'
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

async def update_user_language(user_id: int, language: str):
    """Обновление языка пользователя"""
    if not db_pool:
        logging.warning("⚠️ Database not available, skipping language update")
        return False
        
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE users SET language = $2 WHERE user_id = $1
            ''', user_id, language)
        logging.info(f"✅ Updated user {user_id} language to {language}")
        return True
    except Exception as e:
        logging.error(f"❌ Error updating user language {user_id}: {e}")
        return False

async def update_user_tariff(user_id: int, tariff_name: str, videos_count: int, payment_amount: int):
    """Обновление тарифа пользователя после оплаты"""
    if not db_pool:
        logging.warning("⚠️ Database not available, skipping tariff update")
        return False
        
    try:
        async with db_pool.acquire() as conn:
            # Получаем текущее количество видео
            current_videos = await conn.fetchval(
                "SELECT videos_left FROM users WHERE user_id = $1", user_id
            )
            
            # Суммируем с новым количеством видео
            total_videos = (current_videos or 0) + videos_count
            
            await conn.execute('''
                UPDATE users SET 
                    plan_name = $2, 
                    videos_left = $3, 
                    total_payments = total_payments + $4 
                WHERE user_id = $1
            ''', user_id, tariff_name, total_videos, payment_amount)
        logging.info(f"✅ Updated user {user_id} tariff to {tariff_name}: {current_videos or 0} + {videos_count} = {total_videos} videos")
        return True
    except Exception as e:
        logging.error(f"❌ Error updating user tariff {user_id}: {e}")
        return False

async def create_sora_video(description: str, orientation: str, user_id: int):
    """Создание видео через Sora 2 API"""
    if not SORA_API_KEY:
        logging.warning("⚠️ SORA_API_KEY not found, using demo mode")
        return None, "demo_mode"
    
    try:
        # Подготавливаем параметры для Sora 2 API
        aspect_ratio = "9:16" if orientation == "vertical" else "16:9"
        
        payload = {
            "prompt": description,
            "aspect_ratio": aspect_ratio,
            "duration": 5,  # 5 секунд
            "quality": "hd",
            "metadata": {
                "user_id": str(user_id),
                "orientation": orientation
            }
        }
        
        headers = {
            "Authorization": f"Bearer {SORA_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "SORA2Bot/1.0"
        }
        
        logging.info(f"🎬 Creating Sora video for user {user_id}: {description[:50]}...")
        
        # Отправляем запрос к Sora 2 API
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.post(SORA_API_URL, json=payload, headers=headers) as response:
                response_text = await response.text()
                logging.info(f"🎬 Sora API response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    video_url = data.get("video_url")
                    video_id = data.get("id")
                    
                    if video_url:
                        logging.info(f"✅ Sora video created successfully: {video_id}")
                        return video_url, video_id
                    else:
                        logging.error(f"❌ No video URL in response: {data}")
                        return None, "no_url"
                else:
                    logging.error(f"❌ Sora API error: {response.status} - {response_text}")
                    return None, f"api_error_{response.status}"
                    
    except aiohttp.ClientError as e:
        logging.error(f"❌ Network error creating Sora video: {e}")
        # Если это demo режим (нет API ключа), возвращаем demo_mode
        if not SORA_API_KEY:
            return None, "demo_mode"
        return None, "network_error"
    except Exception as e:
        logging.error(f"❌ Unexpected error creating Sora video: {e}")
        return None, "unknown_error"

# === GLOBAL STATES ===
user_waiting_for_support = set()
user_waiting_for_video_orientation = {}

# === MAIN MENU ===
# Функции меню перенесены в utils/keyboards.py

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
    
    # Получаем язык пользователя
    user_language = user.get('language', 'en') if user else 'en'
    
    # Если язык не установлен, показываем выбор языка
    if not user or not user.get('language'):
        await message.answer(
            get_text('en', "choose_language"),  # Показываем на английском
            reply_markup=language_selection()
        )
        return
    
    # Безопасное извлечение имени пользователя
    safe_first_name = getattr(message.from_user, 'first_name', None) or "friend"
    
    # Проверяем, есть ли у пользователя тариф
    user_plan = user.get('plan_name', 'Без тарифа')
    user_videos_left = user.get('videos_left', 0)
    
    if user_plan == 'Без тарифа' and user_videos_left == 0:
        # Показываем мотивирующее сообщение для покупки тарифа
        await message.answer(
            get_text(user_language, "no_tariff_message"),
            reply_markup=tariff_selection(user_language)
        )
        # Также показываем основное меню
        await message.answer(
            reply_markup=main_menu(user_language)
        )
    else:
        # Обычное приветствие для пользователей с тарифом
        welcome_text = get_text(
            user_language, 
            "welcome",
            name=safe_first_name,
            plan=user_plan,
            videos_left=user_videos_left
        )
        
        await message.answer(
            welcome_text,
            reply_markup=main_menu(user_language)
        )
        
        # Показываем кнопки ориентации
        await message.answer(
            get_text(user_language, "choose_orientation"),
            reply_markup=orientation_menu(user_language)
        )

# === /help ===
@dp.message(Command("help"))
async def cmd_help_command(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    user_language = user.get('language', 'en') if user else 'en'
    
    user_waiting_for_support.add(user_id)
    await message.answer(
        get_text(user_language, "help_text"),
        reply_markup=main_menu(user_language)
    )

# === CALLBACK: Language choice ===
@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Обработка выбора языка
    if callback.data.startswith("lang_"):
        language = callback.data.replace("lang_", "")
        first_name = getattr(callback.from_user, 'first_name', None) or "friend"
        
        # Обновляем язык пользователя в БД
        await update_user_language(user_id, language)
        
        # Получаем пользователя с обновленным языком
        user = await get_user(user_id)
        user_language = user.get('language', 'en') if user else language
        
        # Отправляем подтверждение
        await callback.message.edit_text(
            get_text(user_language, "lang_selected")
        )
        
        # Отправляем приветственное сообщение на выбранном языке
        welcome_text = get_text(
            user_language, 
            "welcome",
            name=first_name,
            plan=user.get('plan_name', 'trial') if user else 'trial',
            videos_left=user.get('videos_left', 3) if user else 3
        )
        
        await callback.message.answer(
            welcome_text,
            reply_markup=main_menu(user_language)
        )
        
        # Показываем кнопки ориентации
        await callback.message.answer(
            get_text(user_language, "choose_orientation"),
            reply_markup=orientation_menu(user_language)
        )
        
        await callback.answer()
        return
    
    # Обработка выбора ориентации
    if callback.data == "orientation_vertical":
        user_waiting_for_video_orientation[user_id] = "vertical"
        user = await get_user(user_id)
        user_language = user.get('language', 'en') if user else 'en'
        
        await callback.message.edit_text(
            get_text(
                user_language, 
                "orientation_selected",
                orientation=get_text(user_language, "orientation_vertical_name")
            )
        )
    elif callback.data == "orientation_horizontal":
        user_waiting_for_video_orientation[user_id] = "horizontal"
        user = await get_user(user_id)
        user_language = user.get('language', 'en') if user else 'en'
        
        await callback.message.edit_text(
            get_text(
                user_language, 
                "orientation_selected",
                orientation=get_text(user_language, "orientation_horizontal_name")
            )
        )
    
        # Обработка покупки тарифов
        elif callback.data == "buy_trial":
            user = await get_user(user_id)
            user_language = user.get('language', 'en') if user else 'en'
            await handle_payment(callback, "trial", tariff_prices["trial"], user_language)
        elif callback.data == "buy_basic":
            user = await get_user(user_id)
            user_language = user.get('language', 'en') if user else 'en'
            await handle_payment(callback, "basic", tariff_prices["basic"], user_language)
        elif callback.data == "buy_maximum":
            user = await get_user(user_id)
            user_language = user.get('language', 'en') if user else 'en'
            await handle_payment(callback, "maximum", tariff_prices["maximum"], user_language)
        elif callback.data == "buy_foreign":
            user = await get_user(user_id)
            user_language = user.get('language', 'en') if user else 'en'
            await handle_foreign_payment(callback, user_language)
    
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

    # Получаем язык пользователя
    user = await get_user(user_id)
    user_language = user.get('language', 'en') if user else 'en'
    
    # Обработка кнопок меню (с учетом языка)
    if text in [get_text(lang, "btn_create_video") for lang in ["ru", "en", "es", "ar", "hi"]]:
        # Показываем выбор ориентации
        await message.answer(
            get_text(user_language, "choose_orientation"),
            reply_markup=orientation_menu(user_language)
        )
    elif text in [get_text(lang, "btn_examples") for lang in ["ru", "en", "es", "ar", "hi"]]:
        await handle_examples(message, user_language)
    elif text in [get_text(lang, "btn_profile") for lang in ["ru", "en", "es", "ar", "hi"]]:
        await handle_profile(message, user_language)
    elif text in [get_text(lang, "btn_help") for lang in ["ru", "en", "es", "ar", "hi"]]:
        await cmd_help(message, user_language)
    elif text in [get_text(lang, "btn_language") for lang in ["ru", "en", "es", "ar", "hi"]]:
        await handle_language_selection(message)
    elif text in [get_text(lang, "btn_buy_tariff") for lang in ["ru", "en", "es", "ar", "hi"]]:
        await handle_buy_tariff(message, user_language)
    else:
        # Если пользователь выбрал ориентацию, то это описание для видео
        if user_id in user_waiting_for_video_orientation and user_waiting_for_video_orientation[user_id]:
            await handle_video_description(message, user_language)
        else:
            await message.answer(
                get_text(user_language, "use_buttons"),
                reply_markup=main_menu(user_language)
            )

async def handle_examples(message: types.Message, user_language: str):
    """Обработка кнопки 'Примеры'"""
    await message.answer(
        get_text(user_language, "examples"),
        reply_markup=main_menu(user_language)
    )

async def handle_profile(message: types.Message, user_language: str):
    """Обработка кнопки 'Кабинет'"""
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await message.answer(get_text(user_language, "error_getting_data"))
        return
    
    # Безопасное извлечение имени
    safe_name = user.get('first_name') or getattr(message.from_user, 'first_name', None) or "Not specified"
    
    profile_text = get_text(
        user_language,
        "profile",
        name=safe_name,
        plan=user['plan_name'],
        videos_left=user['videos_left'],
        date=user['created_at'].strftime('%d.%m.%Y') if user.get('created_at') else "Unknown"
    )
    
    # Создаем inline клавиатуру с кнопками покупки тарифов
    tariff_buttons = tariff_selection(user_language)
    
    await message.answer(profile_text, reply_markup=tariff_buttons)

async def handle_video_description(message: types.Message, user_language: str):
    """Обработка описания видео"""
    user_id = message.from_user.id
    text = message.text.strip()
    orientation = user_waiting_for_video_orientation.get(user_id)
    
    logging.info(f"🎬 Starting video creation for user {user_id}: {text[:50]}... (orientation: {orientation})")
    
    # Получаем данные пользователя
    user = await get_user(user_id)
    if not user:
        await message.answer(get_text(user_language, "error_restart"))
        return
    
    if user['videos_left'] <= 0:
        # Отправляем грустное сообщение с предложением купить тариф
        await message.answer(
            get_text(user_language, "no_videos_left"),
            reply_markup=tariff_selection(user_language)
        )
        # Также показываем основное меню
        await message.answer(
            get_text(user_language, "choose_action"),
            reply_markup=main_menu(user_language)
        )
        return
    
    orientation_text = get_text(user_language, f"orientation_{orientation}_name")
    
    # Отправляем сообщение о том, что видео принято
    await message.answer(
        get_text(
            user_language,
            "video_accepted",
            description=text,
            orientation=orientation_text,
            videos_left=user['videos_left']
        ),
        reply_markup=main_menu(user_language)
    )
    
    # Отправляем сообщение о создании видео (БЕЗ клавиатуры, чтобы можно было редактировать)
    creating_msg = await message.answer(
        get_text(user_language, "video_creating")
    )
    
    # Уменьшаем количество видео ТОЛЬКО после успешного начала процесса
    await update_user_videos(user_id, user['videos_left'] - 1)
    
    try:
        # Определяем aspect_ratio для KIE.AI
        aspect_ratio = "portrait" if orientation == "vertical" else "landscape"
        
        # Создаем задачу через KIE.AI Sora-2 API
        task_id, status = await create_sora_task(
            prompt=text, 
            aspect_ratio=aspect_ratio, 
            user_id=user_id
        )
        
        if task_id and status == "success":
            # Успешно отправлено в KIE.AI
            await creating_msg.edit_text(
                f"✨ <b>Задача отправлена в Sora 2!</b>\n\n🎬 <b>ID задачи:</b> <code>{task_id}</code>\n⏳ <b>Ожидайте уведомление</b> когда видео будет готово\n\n📹 <b>Видео будет отправлено в этот чат автоматически</b>",
                parse_mode="HTML"
            )
            # Меню уже показано в предыдущем сообщении, не дублируем
            logging.info(f"✅ Sora task created for user {user_id}: {task_id}")
        else:
            # Ошибка или demo режим
            if status == "demo_mode":
                # В demo режиме симулируем создание
                await asyncio.sleep(3)
                await creating_msg.edit_text(
                    "🎬 <b>Демо режим</b>\n\n⚠️ KIE.AI API не настроен\n🔄 В реальной версии здесь будет ваше видео\n\n" +
                    get_text(user_language, "video_ready", videos_left=user['videos_left'] - 1)
                )
                # Меню уже показано в предыдущем сообщении, не дублируем
            else:
                # Ошибка создания - возвращаем видео обратно
                await update_user_videos(user_id, user['videos_left'])
                
                await creating_msg.edit_text(
                    get_text(user_language, "video_error", videos_left=user['videos_left'])
                )
                # Меню уже показано в предыдущем сообщении, не дублируем
                
    except Exception as e:
        logging.error(f"❌ Critical error in handle_video_description: {e}")
        
        # Возвращаем видео обратно при любой критической ошибке
        try:
            await update_user_videos(user_id, user['videos_left'])
            logging.info(f"✅ Returned video to user {user_id} due to critical error")
        except Exception as db_error:
            logging.error(f"❌ Failed to return video to user {user_id}: {db_error}")
        
        # Пытаемся отправить сообщение об ошибке
        try:
            await creating_msg.edit_text(
                get_text(user_language, "video_error", videos_left=user['videos_left'])
            )
            # Меню уже показано в предыдущем сообщении, не дублируем
        except Exception as msg_error:
            logging.error(f"❌ Failed to send error message: {msg_error}")
            # Последняя попытка - простое сообщение
            try:
                await message.answer(
                    f"❌ Произошла ошибка при создании видео. Видео возвращено на баланс.\n\n🎞 Осталось видео: {user['videos_left']}"
                )
            except:
                logging.error("❌ Complete failure to notify user about error")
    
    # Очищаем состояние
    if user_id in user_waiting_for_video_orientation:
        del user_waiting_for_video_orientation[user_id]

async def cmd_help(message: types.Message, user_language: str):
    """Обработка команды /help"""
    user_waiting_for_support.add(message.from_user.id)
    await message.answer(
        get_text(user_language, "help_text"),
        reply_markup=main_menu(user_language)
    )

async def handle_language_selection(message: types.Message):
    """Обработка кнопки выбора языка"""
    await message.answer(
        get_text('en', "choose_language"),  # Показываем на английском
        reply_markup=language_selection()
    )

async def handle_buy_tariff(message: types.Message, user_language: str):
    """Обработка кнопки покупки тарифа"""
    tariff_text = get_text(user_language, "tariff_selection")
    await message.answer(
        tariff_text,
        reply_markup=tariff_selection(user_language)
    )

async def create_payment(user_id: int, tariff: str, price: int, videos_count: int):
    """Создание платежа в YooKassa"""
    try:
        # Генерируем уникальный ID платежа
        payment_id = str(uuid.uuid4())
        
        # Создаем платеж
        payment = Payment.create({
            "amount": {
                "value": str(price),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"{PUBLIC_URL}/payment_success"
            },
            "capture": True,
            "description": f"Тариф {tariff} для SORA 2 бота - {videos_count} видео",
            "metadata": {
                "user_id": str(user_id),
                "tariff": tariff,
                "videos_count": str(videos_count)
            }
        }, payment_id)
        
        return payment
    except Exception as e:
        logging.error(f"❌ Error creating payment: {e}")
        return None

async def handle_payment(callback: types.CallbackQuery, tariff: str, price: int, user_language: str):
    """Обработка покупки тарифа"""
    user_id = callback.from_user.id
    
    # Получаем количество видео и цену из конфигурации
    videos_count = tariff_videos.get(tariff, 0)
    price = tariff_prices.get(tariff, price)  # Используем переданную цену как fallback
    
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        # Если YooKassa не настроен, показываем заглушку
        payment_text = f"💳 <b>Покупка тарифа</b>\n\n🎬 Тариф: <b>{tariff}</b>\n💰 Цена: <b>{price} ₽</b>\n🎞 Видео: <b>{videos_count}</b>\n\n⚠️ Система оплаты временно недоступна.\nПопробуйте позже!"
        await callback.message.edit_text(payment_text)
        await callback.answer()
        return
    
    try:
        # Создаем платеж в YooKassa
        payment = await create_payment(user_id, tariff, price, videos_count)
        
        if payment:
            # Получаем ссылку на оплату
            payment_url = payment.confirmation.confirmation_url
            
            # Получаем правильное название тарифа
            tariff_display_name = tariff_names.get(tariff, tariff)
            
            payment_text = f"💳 <b>Оплата тарифа {tariff_display_name}</b>\n\n💰 Сумма: <b>{price} ₽</b>\n🎞 Видео: <b>{videos_count}</b>\n\n📱 После оплаты ваш тариф будет автоматически активирован!"
            
            # Создаем inline кнопку для оплаты
            pay_button = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 ОПЛАТИТЬ", url=payment_url)]
            ])
            
            await callback.message.edit_text(payment_text, reply_markup=pay_button)
            await callback.answer()
        else:
            await callback.message.edit_text("❌ Ошибка создания платежа. Попробуйте позже.")
            await callback.answer()
            
    except Exception as e:
        logging.error(f"❌ Error in handle_payment: {e}")
        await callback.message.edit_text("❌ Произошла ошибка. Попробуйте позже.")
        await callback.answer()

async def handle_foreign_payment(callback: types.CallbackQuery, user_language: str):
    """Обработка оплаты через Tribute (иностранные карты)"""
    user_id = callback.from_user.id
    
    logging.info(f"🌍 Processing foreign payment for user {user_id}")
    
    if not TRIBUTE_API_KEY:
        logging.warning("⚠️ TRIBUTE_API_KEY not found")
        payment_text = f"🌍 <b>Оплата иностранной картой</b>\n\n⚠️ Система оплаты иностранными картами временно недоступна.\nПопробуйте позже!"
        await callback.message.edit_text(payment_text)
        await callback.answer()
        return
    
    try:
        # Параметры для Tribute API
        amount = 10.00  # USD
        headers = {
            "Api-Key": TRIBUTE_API_KEY, 
            "Content-Type": "application/json",
            "User-Agent": "SORA2Bot/1.0"
        }
        payload = {
            "amount": amount,
            "currency": "USD",
            "description": "SORA 2 Bot Tariff Payment - Foreign Card",
            "metadata": {"user_id": str(user_id), "tariff": "foreign"}
        }
        
        logging.info(f"🌍 Creating Tribute payment: {payload}")
        
        # Создаем платеж через Tribute API
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                "https://tribute.tg/api/v1/payments", 
                json=payload, 
                headers=headers
            ) as response:
                
                response_text = await response.text()
                logging.info(f"🌍 Tribute API response status: {response.status}")
                logging.info(f"🌍 Tribute API response: {response_text}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        payment_url = data.get("confirmation_url")
                        
                        if payment_url:
                            payment_text = f"🌍 <b>Оплата иностранной картой</b>\n\n💰 Сумма: {amount} USD\n\nПосле успешной оплаты тариф активируется автоматически."
                            
                            # Создаем inline кнопку для оплаты
                            pay_button = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="💳 ОПЛАТИТЬ", url=payment_url)]
                            ])
                            
                            await callback.message.edit_text(payment_text, reply_markup=pay_button)
                            logging.info(f"✅ Foreign payment created successfully for user {user_id}")
                        else:
                            logging.error(f"❌ No payment URL in response: {data}")
                            await callback.message.edit_text("❌ Ошибка создания платежа. Попробуйте позже.")
                    except Exception as json_error:
                        logging.error(f"❌ JSON parsing error: {json_error}")
                        await callback.message.edit_text("❌ Ошибка обработки ответа. Попробуйте позже.")
                else:
                    logging.error(f"❌ Tribute API error: {response.status} - {response_text}")
                    await callback.message.edit_text("❌ Ошибка создания платежа. Попробуйте позже.")
        
        await callback.answer()
        
    except aiohttp.ClientError as e:
        logging.error(f"❌ Network error in handle_foreign_payment: {e}")
        await callback.message.edit_text("❌ Ошибка сети. Проверьте интернет и попробуйте позже.")
        await callback.answer()
    except Exception as e:
        logging.error(f"❌ Unexpected error in handle_foreign_payment: {e}")
        await callback.message.edit_text("❌ Произошла ошибка. Попробуйте позже.")
        await callback.answer()

# === WEBHOOK HANDLERS ===
async def handle_webhook(request):
    """Обработчик webhook от Telegram"""
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return web.Response()
    except KeyError as e:
        logging.error(f"❌ Ошибка в webhook (KeyError): {e}")
        return web.Response(status=200)  # Возвращаем 200 чтобы Telegram не повторял запрос
    except Exception as e:
        logging.error(f"❌ Ошибка в webhook: {e}")
        return web.Response(status=200)  # Возвращаем 200 чтобы Telegram не повторял запрос

async def health(request):
    """Health check для Railway"""
    return web.Response(text="OK")

async def yookassa_webhook(request):
    """Обработчик webhook от YooKassa"""
    try:
        # Получаем raw данные для логирования
        raw_data = await request.text()
        logging.info(f"💳 YooKassa webhook received: {raw_data}")
        
        data = await request.json()
        logging.info(f"💳 YooKassa webhook parsed data: {data}")
        
        # Проверяем тип события
        event_type = data.get('event')
        logging.info(f"💳 YooKassa event type: {event_type}")
        
        if event_type == 'payment.succeeded':
            payment_data = data.get('object', {})
            logging.info(f"💳 Payment data: {payment_data}")
            
            # Получаем метаданные
            metadata = payment_data.get('metadata', {})
            user_id = int(metadata.get('user_id'))
            tariff = metadata.get('tariff')
            videos_count = int(metadata.get('videos_count'))
            amount = payment_data.get('amount', {}).get('value')
            
            logging.info(f"💳 Processing payment for user {user_id}, tariff {tariff}, videos {videos_count}, amount {amount}")
            
            # Обновляем тариф пользователя
            tariff_name = tariff_names.get(tariff, tariff)
            success = await update_user_tariff(user_id, tariff_name, videos_count, int(float(amount)))
            logging.info(f"💳 User tariff update result: {success}")
            
            # Отправляем уведомление пользователю
            try:
                success_text = f"✅ <b>Оплата прошла успешно!</b>\n\n🎬 Тариф: <b>{tariff_name}</b>\n🎞 Видео: <b>{videos_count}</b>\n💰 Сумма: <b>{amount} ₽</b>\n\n🎉 Теперь вы можете создавать видео!"
                await bot.send_message(user_id, success_text)
                logging.info(f"💳 Success message sent to user {user_id}")
            except Exception as e:
                logging.error(f"❌ Error sending success message to user {user_id}: {e}")
        else:
            logging.info(f"💳 YooKassa event {event_type} ignored")
        
        return web.Response(text="OK")
        
    except Exception as e:
        logging.error(f"❌ Error in YooKassa webhook: {e}")
        import traceback
        logging.error(f"❌ Traceback: {traceback.format_exc()}")
        return web.Response(text="Error", status=500)

async def tribute_webhook(request):
    """Обработчик webhook от Tribute"""
    try:
        data = await request.json()
        
        # Проверяем тип события
        if data.get('event') == 'payment.succeeded':
            # Получаем данные платежа
            metadata = data.get('metadata', {})
            user_id = int(metadata.get('user_id'))
            amount = data.get('amount')
            
            # Обновляем тариф пользователя (даем 10 видео за $10)
            await update_user_tariff(user_id, "Foreign Card", 10, int(amount))
            
            # Отправляем уведомление пользователю
            try:
                success_text = f"✅ <b>Оплата иностранной картой прошла успешно!</b>\n\n🎬 Тариф: <b>Foreign Card</b>\n🎞 Видео: <b>10</b>\n💰 Сумма: <b>{amount} USD</b>\n\n🎉 Теперь вы можете создавать видео!"
                await bot.send_message(user_id, success_text)
            except Exception as e:
                logging.error(f"❌ Error sending success message to user {user_id}: {e}")
        
        return web.Response(text="OK")
        
    except Exception as e:
        logging.error(f"❌ Error in Tribute webhook: {e}")
        return web.Response(text="Error", status=500)

async def sora_callback(request):
    """Callback от Kie.AI Sora-2 — получение готового видео"""
    try:
        data = await request.json()
        logging.info(f"🎬 Sora callback received: {data}")
        
        if data.get("code") == 200 and data["data"]["state"] == "success":
            result_json = data["data"]["resultJson"]
            param = data["data"].get("param", "")
            user_id = extract_user_from_param(param)
            
            if user_id:
                video_urls = json.loads(result_json).get("resultUrls", [])
                if video_urls:
                    # Отправляем видео пользователю
                    try:
                        await bot.send_message(
                            user_id, 
                            f"🎉 <b>Ваше видео готово!</b>\n\n🎬 Видео успешно создано через Sora 2\n📹 <a href='{video_urls[0]}'>Смотреть видео</a>\n\n💡 Для продолжения создания пришлите новое описание!",
                            parse_mode="HTML"
                        )
                        logging.info(f"✅ Video sent to user {user_id}: {video_urls[0]}")
                    except Exception as e:
                        logging.error(f"❌ Error sending video to user {user_id}: {e}")
                else:
                    logging.error(f"❌ No video URLs in result: {result_json}")
            else:
                logging.error(f"❌ Could not extract user_id from param: {param}")
        else:
            logging.warning(f"🎬 Sora callback error: {data}")
            
        return web.Response(text="OK")
        
    except Exception as e:
        logging.error(f"❌ Error in sora_callback: {e}")
        return web.Response(text="Error", status=500)

# === WEB APPLICATION ===
def create_app():
    """Создание веб-приложения"""
    app = web.Application()
    
    # Маршруты
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_post("/yookassa_webhook", yookassa_webhook)
    app.router.add_post("/webhook/yookassa", yookassa_webhook)  # Дополнительный маршрут для YooKassa
    app.router.add_post("/tribute_webhook", tribute_webhook)
    app.router.add_post("/sora_callback", sora_callback)  # Callback от Kie.AI Sora-2
    app.router.add_get("/health", health)
    
    return app

# === MAIN FUNCTION ===
async def start_bot():
    """Запуск бота в webhook или polling режиме"""
    try:
        logging.info("🚀 Launching sora2kudo-bot...")
        logging.info(f"🔧 BOT_TOKEN: {'✅ Set' if BOT_TOKEN else '❌ Missing'}")
        logging.info(f"🔧 PUBLIC_URL: {'✅ Set' if PUBLIC_URL else '❌ Missing'}")
        logging.info(f"🔧 DATABASE_URL: {'✅ Set' if DATABASE_URL else '❌ Missing'}")
        logging.info(f"🔧 TELEGRAM_MODE: {TELEGRAM_MODE}")
        
        # Инициализация базы данных
        db_ready = await init_database()
        if not db_ready:
            logging.warning("⚠️ Database initialization failed, bot will continue with limited functionality")
    except Exception as e:
        logging.error(f"❌ Error in start_bot initialization: {e}")
        raise
    
    try:
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
    except Exception as e:
        logging.error(f"❌ Critical error in start_bot: {e}")
        logging.error(f"❌ Error type: {type(e).__name__}")
        import traceback
        logging.error(f"❌ Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    asyncio.run(start_bot())