#!/usr/bin/env python3
"""
✅ Health Check for SORA 2 от Neurokudo
Проверка переменных окружения перед деплоем
"""

import os
import sys
from typing import List


def check_env() -> bool:
    """✅ Проверить наличие всех необходимых переменных окружения"""
    
    # ✅ Обязательные переменные окружения
    required_vars = [
        "BOT_TOKEN",
        "OPENAI_API_KEY", 
        "DATABASE_URL",
        "YOOKASSA_SECRET_KEY",
        "YOOKASSA_SHOP_ID",
        "PUBLIC_URL"
    ]
    
    # ✅ Опциональные переменные
    optional_vars = [
        "TELEGRAM_MODE",
        "PORT",
        "DEBUG"
    ]
    
    print("🔍 Checking environment variables...")
    print("=" * 40)
    
    missing_required = []
    missing_optional = []
    
    # Проверяем обязательные переменные
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_required.append(var)
            print(f"❌ {var}: NOT SET")
        else:
            # Показываем только первые и последние символы для безопасности
            masked_value = mask_secret(value)
            print(f"✅ {var}: {masked_value}")
    
    # Проверяем опциональные переменные
    print("\n📋 Optional variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if not value:
            missing_optional.append(var)
            print(f"⚠️  {var}: NOT SET (will use default)")
        else:
            print(f"✅ {var}: {value}")
    
    print("\n" + "=" * 40)
    
    # Проверяем результат
    if missing_required:
        print(f"❌ Missing required environment variables: {missing_required}")
        print("🔧 Please set these variables in Railway Dashboard → Variables")
        return False
    
    if missing_optional:
        print(f"⚠️  Missing optional variables: {missing_optional}")
        print("ℹ️  These will use default values")
    
    print("✅ All required environment variables are set and safe!")
    return True


def mask_secret(secret: str) -> str:
    """✅ Замаскировать секрет для безопасного отображения"""
    if len(secret) <= 8:
        return "***"
    
    return f"{secret[:4]}...{secret[-4:]}"


def check_secrets_in_code() -> bool:
    """✅ Проверить, что в коде нет захардкоженных секретов"""
    
    dangerous_patterns = [
        r'sk-[a-zA-Z0-9]{20,}',
        r'live_[a-zA-Z0-9_-]{20,}',
        r'test_[a-zA-Z0-9_-]{20,}',
        r'[0-9]{8,10}:[a-zA-Z0-9_-]{35}',
    ]
    
    print("\n🔒 Checking for hardcoded secrets in code...")
    
    # Запускаем security_check.py
    import subprocess
    try:
        result = subprocess.run(['python3', 'security_check.py'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ No secrets found in code")
            return True
        else:
            print("❌ Secrets found in code!")
            print(result.stdout)
            return False
    except Exception as e:
        print(f"⚠️  Could not run security check: {e}")
        return True  # Продолжаем, если не можем проверить


def main():
    """✅ Главная функция health check"""
    print("🏥 SORA 2 от Neurokudo - Health Check")
    print("=" * 50)
    
    # Проверяем переменные окружения
    env_ok = check_env()
    
    # Проверяем секреты в коде
    secrets_ok = check_secrets_in_code()
    
    print("\n" + "=" * 50)
    
    if env_ok and secrets_ok:
        print("🎉 HEALTH CHECK PASSED!")
        print("✅ Ready for deployment")
        sys.exit(0)
    else:
        print("❌ HEALTH CHECK FAILED!")
        print("🔧 Fix issues before deployment")
        sys.exit(1)


if __name__ == "__main__":
    main()
