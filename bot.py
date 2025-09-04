import logging
import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove

from config import BOT_TOKEN
from convert import (
    get_rates,
    crypto_to_fiat,
    fiat_to_crypto,
    fiat_to_fiat,
    crypto_to_crypto,
)
from keyboard import (
    main_menu,
    fiat_keyboard,
    crypto_keyboard,
    continue_keyboard,
    deposit_currency_keyboard,
    deposit_type_keyboard,
    deposit_term_keyboard,
)
from command import COMMANDS
from models import CRYPTO_SYMBOLS, FIATS


# ===== FSM =====
class ConvertState(StatesGroup):
    choosing_mode = State()
    entering_amount = State()
    choosing_fiat = State()
    choosing_fiat_target = State()
    choosing_crypto = State()
    choosing_crypto_target = State()
    
    # Для крипта -> фиат
    choosing_fiat_target_for_crypto = State()  # новое состояние

    # депозит
    deposit_amount = State()
    deposit_currency = State()
    deposit_type = State()
    deposit_term = State()


# ===== Bot init =====
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# ===== START / HELP =====
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    """
    Оброботка команди старт
    """
    await message.answer(
        "👋 Вітаю! Оберіть режим конвертації або калькулятор:",
        reply_markup=main_menu()
    )
    await state.set_state(ConvertState.choosing_mode)


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    """
    Оброботка хелпа тобеж инструкции
    """
    text = (
        "📖 Інструкція:\n\n"
        "1️⃣ Оберіть режим у меню:\n"
        "   • Фіат ➝ Крипта\n"
        "   • Крипта ➝ Фіат\n"
        "   • Фіат ➝ Фіат\n"
        "   • Крипта ➝ Крипта\n"
        "   • 🆕 Калькулятор депозиту WhiteBIT\n\n"
        "2️⃣ Введіть число (суму).\n"
        "3️⃣ Оберіть валюту чи план кнопками.\n\n"
        "💱 Фіати: " + ", ".join(f.upper() for f in FIATS) + "\n"
        "💰 Криптовалюти: " + ", ".join(CRYPTO_SYMBOLS.values())
    )
    await message.answer(text)


# ====== РЕЖИМЫ КОНВЕРТАЦИЙ ======
@dp.message(F.text == "Фіат ➝ Крипта")
async def choose_fiat_mode(message: types.Message, state: FSMContext):
    """
    Перехід у режим "Фіат ➝ Крипта".
    тута вводи числа
    """
    await state.update_data(mode="fiat_to_crypto")
    await state.set_state(ConvertState.entering_amount)
    await message.answer("Введіть суму у фіаті (тільки число):")


@dp.message(F.text == "Крипта ➝ Фіат")
async def choose_crypto_mode(message: types.Message, state: FSMContext):
    """
    Перехід у режим "Крипта ➝ Фіат".
    сума в крипте
    """
    await state.update_data(mode="crypto_to_fiat")
    await state.set_state(ConvertState.entering_amount)
    await message.answer("Введіть суму у криптовалюті (тільки число):")


@dp.message(F.text == "Фіат ➝ Фіат")
async def choose_fiat_to_fiat_mode(message: types.Message, state: FSMContext):
    """
    Перехід у режим "Фіат ➝ Фіат".
    фиат вводит 
    """
    await state.update_data(mode="fiat_to_fiat")
    await state.set_state(ConvertState.entering_amount)
    await message.answer("Введіть суму у фіаті (тільки число):")


@dp.message(F.text == "Крипта ➝ Крипта")
async def choose_crypto_to_crypto_mode(message: types.Message, state: FSMContext):
    """
    Перехід у режим "Крипта ➝ Крипта".
    крипту вводит
    """
    await state.update_data(mode="crypto_to_crypto")
    await state.set_state(ConvertState.entering_amount)
    await message.answer("Введіть суму у криптовалюті (тільки число):")


# ====== ВВОД СУММЫ ======
@dp.message(ConvertState.entering_amount)
async def process_amount(message: types.Message, state: FSMContext):
    """
    Обробник введення суми для конвертації.

    проверка что число+
    сохренение в фсм
    и юзер идет дальше по схеме
    """
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
        data = await state.get_data()
        mode = data.get("mode")

        await state.update_data(amount=amount)

        if mode == "fiat_to_crypto":
            await state.set_state(ConvertState.choosing_fiat)
            await message.answer("Оберіть вихідну фіатну валюту:", reply_markup=fiat_keyboard())

        elif mode == "crypto_to_fiat":
            await state.set_state(ConvertState.choosing_crypto)
            await message.answer("Оберіть вихідну криптовалюту:", reply_markup=crypto_keyboard())

        elif mode == "fiat_to_fiat":
            await state.set_state(ConvertState.choosing_fiat)
            await message.answer("Оберіть вихідну фіатну валюту:", reply_markup=fiat_keyboard())

        elif mode == "crypto_to_crypto":
            await state.set_state(ConvertState.choosing_crypto)
            await message.answer("Оберіть вихідну криптовалюту:", reply_markup=crypto_keyboard())

    except ValueError:
        await message.answer(" Введіть додатне число")


# ====== FIAT TO CRYPTO / FIAT TO FIAT ======
@dp.message(ConvertState.choosing_fiat)
async def process_fiat_choice(message: types.Message, state: FSMContext):
    """
    Обробник вибору вихідної фіатної валюти.

    Використовується у двох режимах:
    - Фіат ➝ Крипта → після вибору переходить до вибору криптовалюти.
    - Фіат ➝ Фіат → після вибору переходить до вибору цільової фіатної валюти.
    """
    fiat = message.text.strip().lower()
    data = await state.get_data()
    mode = data.get("mode")

    if fiat not in FIATS:
        await message.answer(" Оберіть валюту з кнопок.", reply_markup=fiat_keyboard())
        return

    if mode == "fiat_to_crypto":
        await state.update_data(fiat=fiat)
        await state.set_state(ConvertState.choosing_crypto)
        await message.answer("Оберіть цільову криптовалюту:", reply_markup=crypto_keyboard())

    elif mode == "fiat_to_fiat":
        await state.update_data(from_fiat=fiat)
        await state.set_state(ConvertState.choosing_fiat_target)
        await message.answer("Оберіть цільову фіатну валюту:", reply_markup=fiat_keyboard())


# ====== CRYPTO CHOICE ======
@dp.message(ConvertState.choosing_crypto)
async def process_crypto_choice(message: types.Message, state: FSMContext):
    """
    Обробник вибору вихідної криптовалюти.
     У режимі "Фіат ➝ Крипта" виконує конвертацію та показує результат.
     У режимі "Крипта ➝ Фіат" зберігає криптовалюту та переводить на вибір фіата.
     У режимі "Крипта ➝ Крипта" переводить на вибір цільової криптовалюти.
    """
    crypto_symbol = message.text.strip().upper()

    if crypto_symbol not in CRYPTO_SYMBOLS.values():
        await message.answer("⚠️ Оберіть криптовалюту з кнопок.", reply_markup=crypto_keyboard())
        return

    # находим ключ монетного гекона
    crypto = next(k for k, v in CRYPTO_SYMBOLS.items() if v == crypto_symbol)

    data = await state.get_data()
    mode = data.get("mode")

    if mode == "fiat_to_crypto":
        amount = data["amount"]
        fiat = data["fiat"]
        result = await fiat_to_crypto(amount, fiat, crypto)
        await message.answer(
            f"{amount} {fiat.upper()} = {result:.6f} {CRYPTO_SYMBOLS[crypto]}",
            reply_markup=continue_keyboard()
        )
        await state.set_state(ConvertState.choosing_mode)

    elif mode == "crypto_to_fiat":
        await state.update_data(crypto=crypto)
        await state.set_state(ConvertState.choosing_fiat_target_for_crypto)
        await message.answer("Оберіть цільову фіатну валюту:", reply_markup=fiat_keyboard())

    elif mode == "crypto_to_crypto":
        await state.update_data(from_crypto=crypto)
        await state.set_state(ConvertState.choosing_crypto_target)
        await message.answer("Оберіть цільову криптовалюту:", reply_markup=crypto_keyboard())


# ====== FIAT TARGET CHOICE ======
@dp.message(ConvertState.choosing_fiat_target)
async def process_fiat_target_choice(message: types.Message, state: FSMContext):
    """
    Обробник вибору цільової фіатної валюти для режиму "Фіат ➝ Фіат".
    конец обсчета и показ того що ввийшло
    """
    to_fiat = message.text.strip().lower()
    data = await state.get_data()

    if to_fiat not in FIATS:
        await message.answer("⚠️ Оберіть валюту з кнопок.", reply_markup=fiat_keyboard())
        return

    amount = data["amount"]
    from_fiat = data["from_fiat"]

    result = await fiat_to_fiat(amount, from_fiat, to_fiat)
    await message.answer(
        f"{amount} {from_fiat.upper()} = {result:.2f} {to_fiat.upper()}",
        reply_markup=continue_keyboard()
    )
    await state.set_state(ConvertState.choosing_mode)


# ====== CRYPTO TARGET CHOICE ======
@dp.message(ConvertState.choosing_crypto_target)
async def process_crypto_target_choice(message: types.Message, state: FSMContext):
    """
    Обробник вибору цільової криптовалюти для режиму "Крипта ➝ Крипта".
    конец обсчета и показ того що ввийшло
    """
    crypto_symbol = message.text.strip().upper()

    if crypto_symbol not in CRYPTO_SYMBOLS.values():
        await message.answer("⚠️ Оберіть криптовалюту з кнопок.", reply_markup=crypto_keyboard())
        return

    to_crypto = next(k for k, v in CRYPTO_SYMBOLS.items() if v == crypto_symbol)
    data = await state.get_data()

    amount = data["amount"]
    from_crypto = data["from_crypto"]

    result = await crypto_to_crypto(amount, from_crypto, to_crypto)
    await message.answer(
        f"{amount} {CRYPTO_SYMBOLS[from_crypto]} = {result:.6f} {CRYPTO_SYMBOLS[to_crypto]}",
        reply_markup=continue_keyboard()
    )
    await state.set_state(ConvertState.choosing_mode)


# ====== CRYPTO TO FIAT FINAL ======
@dp.message(ConvertState.choosing_fiat_target_for_crypto)
async def process_crypto_to_fiat_final(message: types.Message, state: FSMContext):
    """
    Обробник фінального вибору фіатної валюти для режиму "Крипта ➝ Фіат".
    конец обсчета и показ того що ввийшло
    """
    fiat = message.text.strip().lower()
    data = await state.get_data()

    if fiat not in FIATS:
        await message.answer("⚠️ Оберіть валюту з кнопок.", reply_markup=fiat_keyboard())
        return

    amount = data["amount"]
    crypto = data["crypto"]

    result = await crypto_to_fiat(amount, crypto, fiat)
    await message.answer(
        f"{amount} {CRYPTO_SYMBOLS[crypto]} = {result:.2f} {fiat.upper()}",
        reply_markup=continue_keyboard()
    )
    await state.set_state(ConvertState.choosing_mode)


# ====== ДЕПОЗИТ ======
@dp.message(F.text == "Калькулятор депозиту крипти")
async def deposit_calc_start(message: types.Message, state: FSMContext):
    """
    Початок роботи калькулятора депозиту.
    Користувач вводить суму депозиту.
    """
    await state.set_state(ConvertState.deposit_amount)
    await message.answer("Введіть суму депозиту (наприклад: 1000):")


@dp.message(ConvertState.deposit_amount)
async def deposit_amount(message: types.Message, state: FSMContext):
    """
    Обробник введення суми депозиту.
    Перевіряє коректність числа та переходить до вибору валюти депозиту.
    """
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
        await state.update_data(deposit_amount=amount)
        await state.set_state(ConvertState.deposit_currency)
        await message.answer("Оберіть валюту депозиту:", reply_markup=deposit_currency_keyboard())
    except ValueError:
        await message.answer("⚠️ Введіть додатне число")


@dp.message(ConvertState.deposit_currency)
async def deposit_choose_currency(message: types.Message, state: FSMContext):
    """
    Обробник вибору валюти депозиту.
    Доступні варіанти: USDT, BTC, ETH.
    """
    currency = message.text.strip().upper()
    if currency not in ("USDT", "BTC", "ETH"):
        await message.answer("⚠️ Оберіть валюту з кнопок.", reply_markup=deposit_currency_keyboard())
        return
    await state.update_data(deposit_currency=currency)
    await state.set_state(ConvertState.deposit_type)
    await message.answer("Оберіть тип депозиту:", reply_markup=deposit_type_keyboard())


@dp.message(ConvertState.deposit_type)
async def deposit_choose_type(message: types.Message, state: FSMContext):
    """
    Обробник вибору типу депозиту.
    - Фіксований → переходить до вибору терміну.
    - Гнучкий → одразу показує розрахунок.
    """
    plan_type = message.text.strip()
    await state.update_data(deposit_type=plan_type)

    if plan_type == "Фіксований":
        await state.set_state(ConvertState.deposit_term)
        await message.answer("Оберіть термін депозиту:", reply_markup=deposit_term_keyboard())

    elif plan_type == "Гнучкий":
        data = await state.get_data()
        amount = data["deposit_amount"]
        currency = data["deposit_currency"]

        flexible_rates = {
            "USDT": 0.0221,
            "BTC": 0.0156,
            "ETH": 0.0168,
        }

        apr = flexible_rates.get(currency, 0.05)
        income = amount * apr
        total = amount + income

        await message.answer(
            f"Гнучкий депозит ({currency}):\n"
            f"Сума: {amount} {currency}\n"
            f"Ставка: {apr*100:.2f}% річних\n"
            f"Прибуток за рік: {income:.2f} {currency}\n"
            f"Разом: {total:.2f} {currency}",
            reply_markup=continue_keyboard()
        )
        await state.set_state(ConvertState.choosing_mode)


@dp.message(ConvertState.deposit_term)
async def deposit_choose_term(message: types.Message, state: FSMContext):
    """
    Обробник вибору терміну для фіксованого депозиту.
    Виконує розрахунок доходу залежно від валюти та терміну.(перепроверить работает ли)
    """
    try:
        term_days = int(message.text.split()[0])
        data = await state.get_data()
        amount = data["deposit_amount"]
        currency = data["deposit_currency"]

        rates = {
            "USDT": {30: 0.1296, 90: 0.1492, 180: 0.1612, 360: 0.1864},
            "BTC": {30: 0.1212, 90: 0.1388, 180: 0.1506, 360: 0.1739},
            "ETH": {30: 0.1212, 90: 0.1388, 180: 0.1506, 360: 0.1739},
        }

        apr = rates.get(currency, {}).get(term_days, 0)
        if apr == 0:
            await message.answer("⚠️ Для цього терміну немає ставки.", reply_markup=deposit_term_keyboard())
            return

        income = amount * apr * (term_days / 365)
        total = amount + income

        await message.answer(
            f"Біржа WhiteBit: Фіксований депозит {currency} на {term_days} днів під {apr*100:.2f}% річних:\n"
            f"Прибуток: {income:.2f} {currency}\n"
            f"Разом: {total:.2f} {currency}",
            reply_markup=continue_keyboard()
        )
        await state.set_state(ConvertState.choosing_mode)
    except Exception:
        await message.answer("⚠️ Оберіть термін з кнопок.")


# ====== КНОПКИ ПРОДОЛЖИТЬ / ЗАВЕРШИТИ ======
@dp.message(F.text == "🔄 Продовжити")
async def continue_handler(message: types.Message, state: FSMContext):
    """
    Обробник кнопки "Продовжити".
    Повертає користувача у головне меню.
    """
    await message.answer("Оберіть режим:", reply_markup=main_menu())
    await state.set_state(ConvertState.choosing_mode)


@dp.message(F.text == "⏹ Завершити")
async def stop_handler(message: types.Message, state: FSMContext):
    """
    Обробник кнопки "Завершити".
     виводить повідомлення про завершення роботи.
    """
    await state.clear()
    await message.answer(
        "✅ Дякуємо за використання бота! Щоб почати знову, натисніть /start",
        reply_markup=ReplyKeyboardRemove()
    )


# ====== MAIN ======
async def main():
    """
    Точка входу для запуску Telegram-бота.
    """
    logging.basicConfig(level=logging.INFO)
    await bot.set_my_commands(COMMANDS)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
