"""
🌍 Клавиатуры с поддержкой мультиязычности для SORA 2
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from translations import get_text, LANGUAGE_BUTTONS

def main_menu(language: str = "en") -> ReplyKeyboardMarkup:
    """Главное меню с учетом языка"""
    kb = [
        [KeyboardButton(text=get_text(language, "btn_create_video"))],
        [KeyboardButton(text=get_text(language, "btn_examples")), 
         KeyboardButton(text=get_text(language, "btn_profile"))],
        [KeyboardButton(text=get_text(language, "btn_buy_tariff"))],
        [KeyboardButton(text=get_text(language, "btn_help")),
         KeyboardButton(text=get_text(language, "btn_language"))]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def language_selection() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка"""
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=LANGUAGE_BUTTONS["ru"], callback_data="lang_ru"),
            InlineKeyboardButton(text=LANGUAGE_BUTTONS["en"], callback_data="lang_en")
        ],
        [
            InlineKeyboardButton(text=LANGUAGE_BUTTONS["es"], callback_data="lang_es"),
            InlineKeyboardButton(text=LANGUAGE_BUTTONS["ar"], callback_data="lang_ar")
        ],
        [
            InlineKeyboardButton(text=LANGUAGE_BUTTONS["hi"], callback_data="lang_hi")
        ]
    ])
    return markup

def orientation_menu(language: str = "en") -> InlineKeyboardMarkup:
    """Меню выбора ориентации видео"""
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_text(language, "orientation_vertical"), 
                callback_data="orientation_vertical"
            ),
            InlineKeyboardButton(
                text=get_text(language, "orientation_horizontal"), 
                callback_data="orientation_horizontal"
            )
        ]
    ])
    return markup

def tariff_selection(language: str = "en") -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифов для покупки"""
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_text(language, "btn_buy_trial"), 
                callback_data="buy_trial"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text(language, "btn_buy_basic"), 
                callback_data="buy_basic"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text(language, "btn_buy_maximum"), 
                callback_data="buy_maximum"
            )
        ]
    ])
    return markup
