# app/services/tribute_subscription.py
import aiohttp
import os
import logging

TRIBUTE_API_KEY = os.getenv("TRIBUTE_API_KEY")
TRIBUTE_API_URL = os.getenv("TRIBUTE_API_URL", "https://tribute.tg/api/v1")
PUBLIC_URL = os.getenv("PUBLIC_URL", "https://sora2kudo-bot-production.up.railway.app")

# Тарифная сетка в долларах USD
TARIFFS = {
    "trial": {"name": "🌱 Trial", "price_usd": 5, "videos": 3, "price_rub": 475},
    "basic": {"name": "✨ Basic", "price_usd": 12, "videos": 10, "price_rub": 1140},
    "maximum": {"name": "💎 Premium", "price_usd": 25, "videos": 30, "price_rub": 2375}
}

async def create_subscription(user_id: int, tariff: str):
    """Создание ежемесячной подписки Tribute - ТЕПЕРЬ НЕ ИСПОЛЬЗУЕТСЯ"""
    # ВАЖНО: Эта функция больше не нужна!
    # Пользователи оплачивают по прямым ссылкам https://web.tribute.tg/p/...
    # Tribute сам отправляет webhook new_digital_product после оплаты
    
    logging.warning(f"⚠️ create_subscription() called but not used anymore - user {user_id}, tariff {tariff}")
    logging.warning("⚠️ Users now pay via direct links: https://web.tribute.tg/p/...")
    logging.warning("⚠️ Tribute sends webhook new_digital_product after payment")
    
    return None  # Возвращаем None, так как функция не используется

def get_tariff_info(tariff: str):
    """Получить информацию о тарифе"""
    return TARIFFS.get(tariff)

def get_all_tariffs():
    """Получить все доступные тарифы"""
    return TARIFFS
