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
    
    # Создаем рекуррентный донат через Tribute API (альтернативный подход)
    payload = {
        "donation_name": f"{tariff_data['name']} - SORA 2 Bot Subscription",
        "amount": tariff_data["price_usd"] * 100,  # в центах USD
        "currency": "usd",
        "period": "monthly",  # ежемесячное повторение
        "message": f"Monthly subscription {tariff_data['name']} - {tariff_data['videos']} videos per month",
        "anonymously": False,
        "metadata": {
            "user_id": str(user_id),
            "tariff": tariff,
            "videos_count": str(tariff_data['videos']),
            "price_usd": str(tariff_data['price_usd']),
            "type": "subscription"
        }
    }
    
    # Попробуем разные варианты endpoints
    endpoints_to_try = [
        f"{TRIBUTE_API_URL}/donations",
        f"{TRIBUTE_API_URL}/subscriptions", 
        f"{TRIBUTE_API_URL}/api/v1/donations",
        f"{TRIBUTE_API_URL}/api/v1/subscriptions",
        f"https://tribute.tg/api/v1/donations",
        f"https://tribute.tg/api/v1/subscriptions"
    ]
    
    logging.info(f"🌍 Creating Tribute subscription for user {user_id}, tariff {tariff}")
    logging.info(f"🌍 Headers: {headers}")
    logging.info(f"🌍 Payload: {payload}")
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for endpoint in endpoints_to_try:
                logging.info(f"🌍 Trying endpoint: {endpoint}")
                async with session.post(
                    endpoint, 
                    headers=headers, 
                    json=payload
                ) as response:
                    response_text = await response.text()
                    logging.info(f"🌍 Tribute API response status: {response.status} for {endpoint}")
                    logging.info(f"🌍 Tribute API response: {response_text}")
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            web_app_link = data.get("web_app_link")
                            
                            if web_app_link:
                                logging.info(f"✅ Tribute subscription created successfully for user {user_id} via {endpoint}")
                                return web_app_link
                            else:
                                logging.warning(f"⚠️ No web_app_link in response from {endpoint}: {data}")
                                continue  # Попробуем следующий endpoint
                        except Exception as json_error:
                            logging.warning(f"⚠️ JSON parsing error from {endpoint}: {json_error}")
                            continue  # Попробуем следующий endpoint
                    elif response.status == 404:
                        logging.warning(f"⚠️ Endpoint {endpoint} not found (404), trying next...")
                        continue  # Попробуем следующий endpoint
                    else:
                        logging.warning(f"⚠️ Error {response.status} from {endpoint}: {response_text}")
                        continue  # Попробуем следующий endpoint
            
            # Если дошли сюда, значит ни один endpoint не сработал
            logging.error(f"❌ All Tribute API endpoints failed for user {user_id}")
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
