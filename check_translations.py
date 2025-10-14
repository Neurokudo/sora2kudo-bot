#!/usr/bin/env python3
"""
Скрипт для проверки полноты переводов на всех языках
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from translations import LANG

def check_translations():
    """Проверяет полноту переводов на всех языках"""
    
    # Получаем все ключи из русского языка (эталон)
    russian_keys = set(LANG["ru"].keys())
    
    # Языки для проверки
    languages = ["ru", "en", "es", "ar", "hi"]
    language_names = {
        "ru": "🇷🇺 Русский",
        "en": "🇺🇸 Английский", 
        "es": "🇪🇸 Испанский",
        "ar": "🇸🇦 Арабский",
        "hi": "🇮🇳 Хинди"
    }
    
    print("🔍 Проверка полноты переводов...")
    print("=" * 50)
    
    all_good = True
    
    for lang_code in languages:
        lang_name = language_names[lang_code]
        lang_keys = set(LANG[lang_code].keys())
        
        # Находим недостающие ключи
        missing_keys = russian_keys - lang_keys
        extra_keys = lang_keys - russian_keys
        
        print(f"\n{lang_name}:")
        
        if missing_keys:
            print(f"  ❌ Недостающие ключи ({len(missing_keys)}):")
            for key in sorted(missing_keys):
                print(f"    - {key}")
            all_good = False
        else:
            print(f"  ✅ Все ключи присутствуют ({len(lang_keys)})")
            
        if extra_keys:
            print(f"  ⚠️ Лишние ключи ({len(extra_keys)}):")
            for key in sorted(extra_keys):
                print(f"    + {key}")
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 Все переводы полные!")
    else:
        print("⚠️ Есть проблемы с переводами")
    
    # Статистика
    print(f"\n📊 Статистика:")
    for lang_code in languages:
        lang_name = language_names[lang_code]
        count = len(LANG[lang_code])
        print(f"  {lang_name}: {count} ключей")

if __name__ == "__main__":
    check_translations()
