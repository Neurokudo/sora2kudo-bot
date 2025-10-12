# app/services/sora_client.py
import aiohttp
import os
import logging
import json

KIE_API_URL = os.getenv("KIE_API_URL", "https://api.kie.ai/api/v1/jobs/createTask")
KIE_API_KEY = os.getenv("KIE_API_KEY")
PUBLIC_URL = os.getenv("PUBLIC_URL")

async def create_sora_task(prompt: str, aspect_ratio: str = "portrait", remove_watermark: bool = True, user_id: int = None):
    """
    Создаёт задачу генерации видео через Kie.AI (Sora-2)
    Возвращает taskId или None при ошибке
    """
    if not KIE_API_KEY:
        logging.warning("⚠️ KIE_API_KEY not found, using demo mode")
        return None, "demo_mode"
    
    if not PUBLIC_URL:
        logging.error("❌ PUBLIC_URL not found for callback")
        return None, "no_callback_url"
    
    headers = {
        "Authorization": f"Bearer {KIE_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "SORA2Bot/1.0"
    }
    
    # Параметр для callback - передаем user_id
    param = {
        "input": {
            "user_id": str(user_id) if user_id else "unknown"
        }
    }
    
    payload = {
        "model": "sora-2-text-to-video",
        "callBackUrl": f"{PUBLIC_URL}/sora_callback",
        "param": json.dumps(param),  # Передаем user_id в параметрах
        "input": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "remove_watermark": remove_watermark
        }
    }

    try:
        logging.info(f"🎬 Creating Sora task for user {user_id}: {prompt[:50]}...")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
            async with session.post(KIE_API_URL, headers=headers, json=payload) as response:
                response_text = await response.text()
                logging.info(f"🎬 Sora API response status: {response.status}")
                logging.info(f"🎬 Sora API response: {response_text}")
                
                if response.status == 200:
                    data = await response.json()
                    if data.get("code") == 200:
                        task_id = data["data"]["taskId"]
                        logging.info(f"✅ Sora task created successfully: {task_id}")
                        return task_id, "success"
                    else:
                        logging.error(f"❌ Sora API error: {data}")
                        return None, f"api_error_{data.get('code', 'unknown')}"
                else:
                    logging.error(f"❌ Sora API HTTP error: {response.status} - {response_text}")
                    return None, f"http_error_{response.status}"
                    
    except aiohttp.ClientError as e:
        logging.error(f"❌ Network error creating Sora task: {e}")
        return None, "network_error"
    except Exception as e:
        logging.error(f"❌ Unexpected error creating Sora task: {e}")
        return None, "unknown_error"

def extract_user_from_param(param_str: str):
    """Извлекает user_id из строки JSON, хранящейся в param"""
    try:
        param = json.loads(param_str)
        return int(param["input"].get("user_id")) if "user_id" in param["input"] else None
    except Exception as e:
        logging.error(f"❌ Error extracting user_id from param: {e}")
        return None
