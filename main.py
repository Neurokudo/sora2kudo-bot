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
from examples import EXAMPLES, get_categories, get_examples_from_category, get_example, get_category_name
from tribute_subscription import create_subscription, get_tariff_info

# Импорт Sora client
from sora_client import create_sora_task, extract_user_from_param

# === CONFIGURATION ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")
TELEGRAM_MODE = os.getenv("TELEGRAM_MODE", "webhook")
PORT = int(os.getenv("PORT", 8080))
DATABASE_URL = os.getenv("DATABASE_URL")
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID", "-4863150171")
logging.info(f"🆘 SUPPORT_CHAT_ID initialized: {SUPPORT_CHAT_ID} (type: {type(SUPPORT_CHAT_ID)})")

if not SUPPORT_CHAT_ID:
    logging.error("❌ SUPPORT_CHAT_ID is not set!")
elif SUPPORT_CHAT_ID == "-4863150171":
    logging.warning("⚠️ SUPPORT_CHAT_ID is using default value. Check Railway environment variables!")

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
                
                # Изменяем дефолтные значения в таблице для новых пользователей
                await conn.execute('''
                    ALTER TABLE users ALTER COLUMN plan_name SET DEFAULT 'Без тарифа'
                ''')
                await conn.execute('''
                    ALTER TABLE users ALTER COLUMN videos_left SET DEFAULT 0
                ''')
                logging.info("✅ Updated default values: plan_name='Без тарифа', videos_left=0")
            
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

# Состояния для системы примеров
user_example_category = {}  # {user_id: category_name}
user_example_index = {}     # {user_id: current_index}
user_example_for_creation = {}  # {user_id: description} - пример для создания видео

# Сообщения задач для удаления при получении видео
user_task_messages = {}  # {user_id: message_id} - сообщения "Задача отправлена в Sora 2!"

# === EXAMPLES: CATEGORY PAGINATION ===
CATEGORIES_PER_PAGE = 6

def build_categories_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    categories = get_categories()
    start = page * CATEGORIES_PER_PAGE
    end = start + CATEGORIES_PER_PAGE
    page_items = categories[start:end]

    keyboard: list[list[InlineKeyboardButton]] = []
    for category_key in page_items:
        category_name = get_category_name(category_key)
        keyboard.append([InlineKeyboardButton(text=category_name, callback_data=f"category_{category_key}")])

    nav_row: list[InlineKeyboardButton] = []
    if start > 0:
        nav_row.append(InlineKeyboardButton(text="⏪", callback_data=f"catpage_{page-1}"))
    if end < len(categories):
        nav_row.append(InlineKeyboardButton(text="⏩", callback_data=f"catpage_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# === MAIN MENU ===
# Функции меню перенесены в utils/keyboards.py

# === /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Игнорируем команды из группы поддержки
    if message.chat.id == int(SUPPORT_CHAT_ID):
        return
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
    
    # Показываем выбор языка для всех пользователей при команде /start
    await message.answer(
        "🌍 <b>Выберите язык / Choose your language:</b>",
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
    # Игнорируем команды из группы поддержки
    if message.chat.id == int(SUPPORT_CHAT_ID):
        return
    user_id = message.from_user.id
    user = await get_user(user_id)
    user_language = user.get('language', 'en') if user else 'en'
    
    user_waiting_for_support.add(user_id)
    await message.answer(
        get_text(user_language, "help_text"),
        reply_markup=main_menu(user_language)
    )

# === /examples ===
@dp.message(Command("examples"))
async def cmd_examples(message: types.Message):
    """Обработка команды /examples"""
    # Игнорируем команды из группы поддержки
    if message.chat.id == int(SUPPORT_CHAT_ID):
        return
    
    user_id = message.from_user.id
    user = await get_user(user_id)
    user_language = user.get('language', 'en') if user else 'en'
    
    await handle_examples(message, user_language)

# === /profile ===
@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Обработка команды /profile"""
    # Игнорируем команды из группы поддержки
    if message.chat.id == int(SUPPORT_CHAT_ID):
        return
    
    user_id = message.from_user.id
    user = await get_user(user_id)
    user_language = user.get('language', 'en') if user else 'en'
    
    await handle_profile(message, user_language)

# === /language ===
@dp.message(Command("language"))
async def cmd_language(message: types.Message):
    """Обработка команды /language"""
    # Игнорируем команды из группы поддержки
    if message.chat.id == int(SUPPORT_CHAT_ID):
        return
    
    await handle_language_selection(message)

# === /create ===
@dp.message(Command("create"))
async def cmd_create(message: types.Message):
    """Обработка команды /create - показать выбор ориентации"""
    # Игнорируем команды из группы поддержки
    if message.chat.id == int(SUPPORT_CHAT_ID):
        return
    
    user_id = message.from_user.id
    user = await get_user(user_id)
    user_language = user.get('language', 'en') if user else 'en'
    
    # Показываем выбор ориентации
    await message.answer(
        get_text(user_language, "choose_orientation"),
        reply_markup=orientation_menu(user_language)
    )

# === /buy ===
@dp.message(Command("buy"))
async def cmd_buy(message: types.Message):
    """Обработка команды /buy - показать тарифы"""
    # Игнорируем команды из группы поддержки
    if message.chat.id == int(SUPPORT_CHAT_ID):
        return
    
    user_id = message.from_user.id
    user = await get_user(user_id)
    user_language = user.get('language', 'en') if user else 'en'
    
    await handle_buy_tariff(message, user_language)

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
            plan=user.get('plan_name', 'Без тарифа') if user else 'Без тарифа',
            videos_left=user.get('videos_left', 0) if user else 0
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
        
        # Проверяем, есть ли сохраненный пример для создания
        if user_id in user_example_for_creation:
            # Создаем видео из примера
            description = user_example_for_creation[user_id]
            del user_example_for_creation[user_id]  # Удаляем после использования
            await handle_video_description_from_example(callback, description)
        else:
            # Обычный выбор ориентации
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
        
        # Проверяем, есть ли сохраненный пример для создания
        if user_id in user_example_for_creation:
            # Создаем видео из примера
            description = user_example_for_creation[user_id]
            del user_example_for_creation[user_id]  # Удаляем после использования
            await handle_video_description_from_example(callback, description)
        else:
            # Обычный выбор ориентации
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
    
    # Обработка выбора подписок Tribute
    elif callback.data.startswith("sub_"):
        tariff = callback.data.replace("sub_", "")
        tariff_info = get_tariff_info(tariff)
        
        if not tariff_info:
            await callback.message.edit_text("❌ Неизвестный тариф. Попробуйте позже.")
            await callback.answer()
            return
        
        # Создаем подписку через Tribute
        web_app_link = await create_subscription(user_id, tariff)
        
        if web_app_link:
            subscription_text = (
                f"🌍 <b>Subscription plan: {tariff_info['name']}</b>\n\n"
                f"💰 <b>${tariff_info['price_usd']}</b> per month\n"
                f"🎬 {tariff_info['videos']} videos monthly\n"
                f"🔄 Auto-renewal\n\n"
                f"💳 Click the button below to proceed to payment:"
            )
            
            pay_button = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 PROCEED TO PAYMENT", url=web_app_link)],
                [InlineKeyboardButton(text="🔙 Back to subscriptions", callback_data="foreign_payment")]
            ])
            
            await callback.message.edit_text(
                subscription_text,
                reply_markup=pay_button,
                parse_mode="HTML"
            )
            logging.info(f"✅ Subscription created for user {user_id}, tariff {tariff}")
        else:
            await callback.message.edit_text("❌ Не удалось создать подписку. Попробуйте позже.")
        
        await callback.answer()
    
    # Обработка выбора категории примеров
    elif callback.data.startswith("category_"):
        category_key = callback.data.replace("category_", "")
        user_example_category[user_id] = category_key
        user_example_index[user_id] = 0
        await show_example(callback, category_key, 0)
    
    # Обработка навигации по примерам
    elif callback.data == "example_prev":
        category_key = user_example_category.get(user_id)
        if category_key:
            examples = get_examples_from_category(category_key)
            if examples:
                current_index = user_example_index.get(user_id, 0)
                prev_index = (current_index - 1) % len(examples)
                user_example_index[user_id] = prev_index
                await show_example(callback, category_key, prev_index)
    
    elif callback.data == "example_next":
        category_key = user_example_category.get(user_id)
        if category_key:
            examples = get_examples_from_category(category_key)
            if examples:
                current_index = user_example_index.get(user_id, 0)
                next_index = (current_index + 1) % len(examples)
                user_example_index[user_id] = next_index
                await show_example(callback, category_key, next_index)
    
    elif callback.data == "example_back_to_categories":
        await show_categories(callback, 0)
    
    elif callback.data.startswith("catpage_"):
        try:
            page = int(callback.data.replace("catpage_", ""))
        except Exception:
            page = 0
        await show_categories(callback, page)
    
    elif callback.data == "example_create_video":
        category_key = user_example_category.get(user_id)
        current_index = user_example_index.get(user_id, 0)
        if category_key:
            example = get_example(category_key, current_index)
            if example:
                # Сохраняем пример для создания видео
                user_example_for_creation[user_id] = example['description']
                
                # Получаем язык пользователя для отображения меню ориентации
                user = await get_user(user_id)
                user_language = user.get('language', 'en') if user else 'en'
                
                # Показываем выбор ориентации
                await callback.message.edit_text(
                    get_text(user_language, "choose_orientation"),
                    reply_markup=orientation_menu(user_language)
                )
    
    await callback.answer()

# === DEFAULT HANDLER ===
@dp.message()
async def handle_text(message: types.Message):
    # Игнорируем сообщения из группы поддержки
    if message.chat.id == int(SUPPORT_CHAT_ID):
        logging.info(f"🆘 Ignoring message from support group: {message.chat.id}")
        return
    
    user_id = message.from_user.id
    text = message.text.strip()

    # Если пользователь сейчас пишет в поддержку
    if user_id in user_waiting_for_support:
        logging.info(f"🆘 User {user_id} is writing to support. SUPPORT_CHAT_ID: {SUPPORT_CHAT_ID}")
        username = message.from_user.username or "без ника"
        full_name = message.from_user.full_name
        chat_text = (
            f"📩 <b>Новое сообщение в поддержку</b>\n\n"
            f"👤 Пользователь: @{username} ({full_name})\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"💬 Сообщение:\n{text}"
        )
        try:
            logging.info(f"🆘 Sending support message to chat ID: {SUPPORT_CHAT_ID}")
            logging.info(f"🆘 Message content: {chat_text[:100]}...")
            
            # Преобразуем в int для уверенности
            support_chat_id = int(SUPPORT_CHAT_ID)
            logging.info(f"🆘 Converted to int: {support_chat_id}")
            
            result = await bot.send_message(support_chat_id, chat_text, parse_mode="HTML")
            logging.info(f"✅ Support message sent successfully to {support_chat_id}")
            logging.info(f"✅ Message ID: {result.message_id}")
            await message.answer("✅ Сообщение отправлено. Я постараюсь ответить как можно скорее!")
        except Exception as e:
            logging.error(f"❌ Ошибка при отправке в поддержку: {e}")
            logging.error(f"❌ SUPPORT_CHAT_ID: {SUPPORT_CHAT_ID}, Type: {type(SUPPORT_CHAT_ID)}")
            logging.error(f"❌ Full error details: {str(e)}")
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
    """Обработка кнопки 'Примеры' - показывает категории"""
    markup = build_categories_keyboard(0)
    text = "🎬 <b>Готовые идеи для создания вирусных видео!</b>\n\n<b>Как использовать:</b>\n1️⃣ Выбери понравившийся пример\n2️⃣ Скопируй текст\n3️⃣ Вставь в бот и создай видео!\nИли измени под свою идею 💡\n\n<b>Кнопки с разделами и примерами 👇</b>"
    await message.answer(text, reply_markup=markup)

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
        return
    
    orientation_text = get_text(user_language, f"orientation_{orientation}_name")
    
    # Сразу отправляем сообщение о создании видео
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
            task_msg = await creating_msg.edit_text(
                f"✨ <b>Задача отправлена в Sora 2!</b>\n\n🎬 <b>Описание:</b> <i>{text}</i>\n\n🆔 <b>ID задачи:</b> <code>{task_id}</code>\n⏳ <b>Ожидайте уведомление</b> когда видео будет готово\n\n📹 <b>Видео будет отправлено в этот чат автоматически</b>",
                parse_mode="HTML"
            )
            # Сохраняем ID сообщения для последующего удаления
            user_task_messages[user_id] = task_msg.message_id
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
    user_id = message.from_user.id
    logging.info(f"🆘 User {user_id} clicked Help button. Adding to support queue.")
    user_waiting_for_support.add(user_id)
    logging.info(f"🆘 Users waiting for support: {user_waiting_for_support}")
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
    """Обработка оплаты через Tribute (иностранные карты) - выбор подписок"""
    user_id = callback.from_user.id
    
    logging.info(f"🌍 Processing foreign payment for user {user_id}")
    
    if not TRIBUTE_API_KEY:
        logging.warning("⚠️ TRIBUTE_API_KEY not found")
        payment_text = f"🌍 <b>Оплата иностранной картой</b>\n\n⚠️ Система оплаты иностранными картами временно недоступна.\nПопробуйте позже!"
        await callback.message.edit_text(payment_text)
        await callback.answer()
        return
    
    # Показываем выбор подписок в долларах
    subscription_text = "🌍 <b>Foreign Card Subscriptions</b>\n\n💳 Choose your monthly subscription plan:"
    
    subscription_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌱 Trial — $5 / month", callback_data="sub_trial")],
        [InlineKeyboardButton(text="✨ Basic — $12 / month", callback_data="sub_basic")],
        [InlineKeyboardButton(text="💎 Premium — $25 / month", callback_data="sub_maximum")],
        [InlineKeyboardButton(text="🔙 Назад к тарифам", callback_data="buy_tariff")]
    ])
    
    await callback.message.edit_text(
        subscription_text,
        reply_markup=subscription_keyboard,
        parse_mode="HTML"
    )
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
    """Обработчик webhook от Tribute для донатов"""
    try:
        data = await request.json()
        logging.info(f"🎬 Tribute donation webhook received: {data}")
        
        # Проверяем тип события согласно документации Tribute
        event_name = data.get('name')
        payload = data.get('payload', {})
        
        if event_name == 'new_donation':
            # Новый донат - активируем тариф
            telegram_user_id = payload.get('telegram_user_id')
            amount = payload.get('amount', 0)
            
            if telegram_user_id:
                # Активируем тариф (50 видео за $10)
                videos_to_add = 50
                await update_user_videos(telegram_user_id, videos_to_add)
                
                # Отправляем подтверждение пользователю
                try:
                    await bot.send_message(
                        telegram_user_id,
                        f"🎉 <b>Оплата прошла успешно!</b>\n\n✅ Тариф активирован\n🎬 Видео на балансе: {videos_to_add}\n\nСпасибо за покупку!"
                    )
                    logging.info(f"✅ Tribute donation processed for user {telegram_user_id}")
                except Exception as e:
                    logging.error(f"❌ Error sending success message to user {telegram_user_id}: {e}")
        
        elif event_name == 'recurrent_donation':
            # Регулярный донат
            telegram_user_id = payload.get('telegram_user_id')
            if telegram_user_id:
                videos_to_add = 50
                await update_user_videos(telegram_user_id, videos_to_add)
                
                try:
                    await bot.send_message(
                        telegram_user_id,
                        f"🔄 <b>Регулярный платеж обработан!</b>\n\n✅ Добавлено видео: {videos_to_add}\n\nСпасибо за поддержку!"
                    )
                except Exception as e:
                    logging.error(f"❌ Error sending recurrent payment message to user {telegram_user_id}: {e}")
        
        return web.Response(text="OK")
        
    except Exception as e:
        logging.error(f"❌ Error in Tribute donation webhook: {e}")
        return web.Response(text="Error", status=500)

async def tribute_subscription_webhook(request):
    """Webhook от Tribute для ежемесячных подписок"""
    try:
        data = await request.json()
        signature = request.headers.get("trbt-signature")
        logging.info(f"🎬 Tribute webhook received: {data}")
        logging.info(f"🧾 Tribute signature: {signature}")

        event_name = data.get("name")
        payload = data.get("payload", {})
        metadata = payload.get("metadata", {})

        logging.info(f"🎯 Event: {event_name}, payload: {payload}")

        # Новый формат Tribute событий
        if event_name == "new_subscription" or event_name == "new_digital_product":
            telegram_user_id = payload.get("telegram_user_id")
            if not telegram_user_id:
                logging.error("❌ Missing telegram_user_id in payload")
                return web.Response(text="Missing user", status=400)

            tariff = metadata.get("tariff", "unknown")
            videos_count = int(metadata.get("videos_count", 0))
            price_usd = metadata.get("price_usd", "0")

            # Обновляем пользователя
            if videos_count > 0:
                await update_user_videos(telegram_user_id, videos_count)
                try:
                    await bot.send_message(
                        telegram_user_id,
                        f"🎉 <b>Subscription activated!</b>\n\n"
                        f"✅ Plan: <b>{tariff}</b>\n"
                        f"🎬 Videos added: <b>{videos_count}</b>\n"
                        f"💰 Price: <b>${price_usd}/month</b>\n\n"
                        f"🔄 Subscription will auto-renew monthly"
                    )
                    logging.info(f"✅ Tribute subscription activated for user {telegram_user_id}")
                except Exception as e:
                    logging.error(f"❌ Error sending confirmation: {e}")

        elif event_name == "cancelled_subscription":
            telegram_user_id = payload.get("telegram_user_id")
            if telegram_user_id:
                try:
                    await bot.send_message(
                        telegram_user_id,
                        "❌ <b>Subscription cancelled</b>\n\n"
                        "Your subscription has been cancelled, but remaining videos will stay until the end of this month."
                    )
                    logging.info(f"✅ Subscription cancelled for user {telegram_user_id}")
                except Exception as e:
                    logging.error(f"❌ Error sending cancellation: {e}")

        return web.Response(text="OK")

    except Exception as e:
        logging.error(f"❌ Error in Tribute subscription webhook: {e}")
        import traceback
        logging.error(traceback.format_exc())
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
                    # Удаляем сообщение "Задача отправлена в Sora 2!" если есть
                    if user_id in user_task_messages:
                        try:
                            await bot.delete_message(user_id, user_task_messages[user_id])
                            del user_task_messages[user_id]
                        except Exception as e:
                            logging.warning(f"⚠️ Could not delete task message for user {user_id}: {e}")
                    
                    # Отправляем видео пользователю
                    try:
                        # Пробуем отправить видео напрямую по URL
                        await bot.send_video(
                            user_id, 
                            video=video_urls[0],
                            caption="🎉 <b>Ваше видео готово!</b>\n\n🎬 Видео успешно создано через Sora 2",
                            parse_mode="HTML"
                        )
                        
                        logging.info(f"✅ Video sent directly to user {user_id}: {video_urls[0]}")
                        
                    except Exception as e:
                        logging.error(f"❌ Direct video send failed for user {user_id}: {e}")
                        
                        # Пробуем скачать и отправить как файл
                        try:
                            import aiohttp
                            import tempfile
                            import os
                            
                            async with aiohttp.ClientSession() as session:
                                async with session.get(video_urls[0]) as response:
                                    if response.status == 200:
                                        # Создаем временный файл
                                        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                                            temp_file.write(await response.read())
                                            temp_file_path = temp_file.name
                                        
                                        # Отправляем как видео-файл
                                        with open(temp_file_path, 'rb') as video_file:
                                            await bot.send_video(
                                                user_id,
                                                video=video_file,
                                                caption="🎉 <b>Ваше видео готово!</b>\n\n🎬 Видео успешно создано через Sora 2",
                                                parse_mode="HTML"
                                            )
                                        
                                        # Удаляем временный файл
                                        os.unlink(temp_file_path)
                                        
                                        logging.info(f"✅ Video downloaded and sent to user {user_id}")
                                    else:
                                        raise Exception(f"Failed to download video: HTTP {response.status}")
                                        
                        except Exception as download_error:
                            logging.error(f"❌ Video download failed for user {user_id}: {download_error}")
                            
                            # Fallback - отправляем ссылку
                            try:
                                await bot.send_message(
                                    user_id, 
                                    f"🎉 <b>Ваше видео готово!</b>\n\n🎬 Видео успешно создано через Sora 2\n📹 <a href='{video_urls[0]}'>Смотреть видео</a>",
                                    parse_mode="HTML"
                                )
                                logging.info(f"✅ Fallback link sent to user {user_id}")
                            except Exception as fallback_error:
                                logging.error(f"❌ Fallback error: {fallback_error}")
                    
                    # Меню не отправляем - пользователь сам выберет действие
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
    app.router.add_post("/tribute_webhook", tribute_webhook)  # Webhook для донатов Tribute
    app.router.add_post("/tribute_subscription_webhook", tribute_subscription_webhook)  # Webhook для подписок Tribute
    app.router.add_post("/sora_callback", sora_callback)  # Callback от Kie.AI Sora-2
    app.router.add_get("/health", health)
    
    return app

# === EXAMPLES SYSTEM FUNCTIONS ===

def build_categories_keyboard(page: int = 0):
    """Создает клавиатуру с пагинацией разделов (6+6+6+2)"""
    categories = get_categories()
    categories_per_page = [6, 6, 6, 2]  # 6+6+6+2 = 20 кнопок
    total_pages = len(categories_per_page)
    
    # Определяем текущую страницу
    if page >= total_pages:
        page = 0
    
    # Создаем кнопки для текущей страницы
    start_idx = sum(categories_per_page[:page])
    end_idx = start_idx + categories_per_page[page]
    page_categories = categories[start_idx:end_idx]
    
    keyboard = []
    for category_key in page_categories:
        category_name = get_category_name(category_key)
        keyboard.append([InlineKeyboardButton(text=category_name, callback_data=f"category_{category_key}")])
    
    # Добавляем навигационные кнопки
    nav_buttons = []
    if page > 0 and page < total_pages - 1:
        # Средние страницы: Назад + Еще
        nav_buttons.append(InlineKeyboardButton(text="⏪ Назад", callback_data=f"catpage_{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text="⏩ Еще", callback_data=f"catpage_{page+1}"))
    elif page > 0:
        # Последняя страница: только Назад
        nav_buttons.append(InlineKeyboardButton(text="⏪ Назад", callback_data=f"catpage_{page-1}"))
    elif page < total_pages - 1:
        # Первая страница: только Еще примеры
        nav_buttons.append(InlineKeyboardButton(text="⏩ Еще примеры", callback_data=f"catpage_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def show_categories(callback: types.CallbackQuery, page: int = 0):
    """Показать категории примеров с пагинацией"""
    markup = build_categories_keyboard(page)
    text = "🎬 <b>Готовые идеи для создания вирусных видео!</b>\n\n<b>Как использовать:</b>\n1️⃣ Выбери понравившийся пример\n2️⃣ Скопируй текст\n3️⃣ Вставь в бот и создай видео!\nИли измени под свою идею 💡\n\n<b>Кнопки с разделами и примерами 👇</b>"
    await callback.message.edit_text(text, reply_markup=markup)

async def show_example(callback: types.CallbackQuery, category_key: str, index: int):
    """Показать конкретный пример с навигацией"""
    examples = get_examples_from_category(category_key)
    if not examples:
        await callback.message.edit_text("❌ В этом разделе пока нет примеров")
        return
        
    # Проверяем индекс
    if index >= len(examples) or index < 0:
        index = 0
        
    example = examples[index]
    category_name = get_category_name(category_key)
    
    # Создаем навигационные кнопки
    keyboard = [
        [
            InlineKeyboardButton(text="⏪ Назад", callback_data="example_prev"),
            InlineKeyboardButton(text="▶️ Создать", callback_data="example_create_video"),
            InlineKeyboardButton(text="⏩ Далее", callback_data="example_next")
        ],
        [InlineKeyboardButton(text="⏹️ Другой раздел", callback_data="example_back_to_categories")]
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    text = f"📚 <b>{category_name}</b>\n\n<b>{example['title']}</b>\n\n<code>{example['description']}</code>\n\n<i>{index + 1} из {len(examples)}</i>"
    
    await callback.message.edit_text(text, reply_markup=markup)

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


async def handle_video_description_from_example(callback: types.CallbackQuery, description: str):
    """Создать видео из примера"""
    user_id = callback.from_user.id
    
    # Проверяем пользователя и его видео
    user = await get_user(user_id)
    if not user:
        await callback.message.edit_text("❌ Ошибка получения данных пользователя")
        return
    
    user_language = user.get('language', 'en')
    
    # Проверяем количество видео
    if user['videos_left'] <= 0:
        await callback.message.edit_text(get_text(user_language, "no_videos_left"), reply_markup=tariff_selection(user_language))
        return
    
    # Устанавливаем ориентацию и создаем видео
    orientation = user_waiting_for_video_orientation.get(user_id, "vertical")
    
    try:
        # Показываем сообщение о создании
        creating_msg = await callback.message.edit_text(
            get_text(user_language, "video_creating")
        )
        
        # Списываем видео
        await update_user_videos(user_id, user['videos_left'] - 1)
        
        # Преобразуем ориентацию в aspect_ratio для Sora API
        aspect_ratio = "portrait" if orientation == "vertical" else "landscape"
        
        # Создаем задачу в Sora
        task_id, status = await create_sora_task(description, aspect_ratio, user_id=user_id)
        
        if task_id and status == "success":
            # Показываем успешное создание задачи с промптом
            task_msg = await creating_msg.edit_text(
                f"✅ <b>Задача отправлена в Sora 2!</b>\n\n🎬 <b>Описание:</b> <i>{description}</i>\n\n🆔 <b>ID задачи:</b> <code>{task_id}</code>\n\n⏳ Ожидайте уведомление когда видео будет готово"
            )
            # Сохраняем ID сообщения для последующего удаления
            user_task_messages[user_id] = task_msg.message_id
            
            # Информируем о том, что видео будет отправлено
            await callback.message.answer(
                "🎬 Видео будет отправлено в этот чат автоматически"
            )
        else:
            # Ошибка создания - возвращаем видео обратно
            await update_user_videos(user_id, user['videos_left'])
            
            error_text = get_text(user_language, "video_error", videos_left=user['videos_left'])
            await creating_msg.edit_text(error_text)
            
            # Меню уже показано в предыдущем сообщении
            
    except Exception as e:
        logging.error(f"❌ Error creating video from example: {e}")
        
        # Возвращаем видео обратно при любой ошибке
        await update_user_videos(user_id, user['videos_left'])
        
        await callback.message.edit_text("❌ Произошла ошибка при создании видео. Попробуйте позже.")

if __name__ == "__main__":
    asyncio.run(start_bot())