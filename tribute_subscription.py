# app/services/tribute_subscription.py
import aiohttp
import os
import logging

TRIBUTE_API_KEY = os.getenv("TRIBUTE_API_KEY")
TRIBUTE_API_URL = os.getenv("TRIBUTE_API_URL", "https://tribute.tg/api/v1")
PUBLIC_URL = os.getenv("PUBLIC_URL", "https://sora2kudo-bot-production.up.railway.app")

# Тарифная сетка
TARIFFS = {
    "trial": {"name": "🌱 Пробный", "price_rub": 390, "videos": 3, "price_usd": 4},
    "basic": {"name": "✨ Базовый", "price_rub": 990, "videos": 10, "price_usd": 10},
    "maximum": {"name": "💎 Максимум", "price_rub": 2190, "videos": 30, "price_usd": 22}
}

async def create_subscription(user_id: int, tariff: str):
    """Создание ежемесячной подписки Tribute"""
    if not TRIBUTE_API_KEY:
        logging.error("❌ TRIBUTE_API_KEY not found")
        return None
        
    if tariff not in TARIFFS:
        logging.error(f"❌ Unknown tariff: {tariff}")
        return None
    
    tariff_data = TARIFFS[tariff]
    
    headers = {
        "Api-Key": TRIBUTE_API_KEY, 
        "Content-Type": "application/json",
        "User-Agent": "SORA2Bot/1.0"
    }
    
    # Создаем подписку через Tribute API
    payload = {
        "subscription_name": f"{tariff_data['name']} - SORA 2 Bot",
        "amount": tariff_data["price_usd"] * 100,  # в центах
        "currency": "usd",
        "period": "monthly",
        "description": f"Ежемесячная подписка на тариф {tariff_data['name']} - {tariff_data['videos']} видео в месяц",
        "metadata": {
            "user_id": str(user_id),
            "tariff": tariff,
            "videos_count": str(tariff_data['videos']),
            "price_rub": str(tariff_data['price_rub'])
        }
    }
    
    logging.info(f"🌍 Creating Tribute subscription for user {user_id}, tariff {tariff}: {payload}")
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                f"{TRIBUTE_API_URL}/subscriptions", 
                headers=headers, 
                json=payload
            ) as response:
                
                response_text = await response.text()
                logging.info(f"🌍 Tribute subscription API response status: {response.status}")
                logging.info(f"🌍 Tribute subscription API response: {response_text}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        web_app_link = data.get("web_app_link")
                        
                        if web_app_link:
                            logging.info(f"✅ Tribute subscription created successfully for user {user_id}")
                            return web_app_link
                        else:
                            logging.error(f"❌ No web_app_link in subscription response: {data}")
                            return None
                    except Exception as json_error:
                        logging.error(f"❌ JSON parsing error in subscription: {json_error}")
                        return None
                else:
                    logging.error(f"❌ Tribute subscription API error: {response.status} - {response_text}")
                    return None
                    
    except aiohttp.ClientError as e:
        logging.error(f"❌ HTTP error in subscription creation: {e}")
        return None
    except Exception as e:
        logging.error(f"❌ Unexpected error in subscription creation: {e}")
        return None

def get_tariff_info(tariff: str):
    """Получить информацию о тарифе"""
    return TARIFFS.get(tariff)

def get_all_tariffs():
    """Получить все доступные тарифы"""
    return TARIFFS
