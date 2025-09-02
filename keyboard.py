from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Фіат ➝ Крипта")
    kb.button(text="Крипта ➝ Фіат")
    kb.button(text="Фіат ➝ Фіат")
    kb.button(text="Крипта ➝ Крипта")
    kb.button(text="Калькулятор депозиту крипти")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Оберіть режим…")


def fiat_keyboard():
    kb = ReplyKeyboardBuilder()
    for code in ("USD", "EUR", "UAH"):
        kb.button(text=code)
    kb.adjust(3)
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Оберіть валюту…")


def crypto_keyboard():
    kb = ReplyKeyboardBuilder()
    for code in ("BTC", "ETH", "USDT"):
        kb.button(text=code)
    kb.adjust(3)
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Оберіть криптовалюту…")


def continue_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔄 Продовжити")
    kb.button(text="⏹ Завершити")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Продовжити чи завершити?")


def deposit_currency_keyboard():
    kb = ReplyKeyboardBuilder()
    for code in ("USDT", "BTC", "ETH"):
        kb.button(text=code)
    kb.adjust(3)
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Оберіть валюту депозиту…")


def deposit_type_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Фіксований")
    kb.button(text="Гнучкий")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Оберіть тип депозиту…")


def deposit_term_keyboard():
    kb = ReplyKeyboardBuilder()
    for term in ("30 днів", "90 днів", "180 днів", "360 днів"):
        kb.button(text=term)
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Оберіть термін…")
