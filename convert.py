import aiohttp

# CoinGecko API базовый URL
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


async def get_rates(assets, vs_currencies):
    """
    Запрос котировок с CoinGecko.
    assets: список криптовалют или фиатов (в API ключи маленькими буквами)
    vs_currencies: список валют для сравнения
    """
    url = f"{COINGECKO_URL}?ids={','.join(assets)}&vs_currencies={','.join(vs_currencies)}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Ошибка API CoinGecko: {resp.status}")
            return await resp.json()


# ===== КОНВЕРТАЦИИ =====

async def fiat_to_crypto(amount: float, fiat: str, crypto: str) -> float:
    """
    Конвертация фиата в крипту
    fiat = "usd", crypto = "bitcoin"
    """
    fiat = fiat.lower()
    crypto = crypto.lower()
    data = await get_rates([crypto], [fiat])
    rate = data[crypto][fiat]  # например: bitcoin["usd"] = 58000
    return amount / rate


async def crypto_to_fiat(amount: float, crypto: str, fiat: str) -> float:
    """
    Конвертация крипты в фиат
    crypto = "bitcoin", fiat = "usd"
    """
    fiat = fiat.lower()
    crypto = crypto.lower()
    data = await get_rates([crypto], [fiat])
    rate = data[crypto][fiat]
    return amount * rate


async def fiat_to_fiat(amount: float, from_fiat: str, to_fiat: str) -> float:
    """
    Конвертация фиат → фиат через USDT как промежуточную валюту
    """
    from_fiat = from_fiat.lower()
    to_fiat = to_fiat.lower()

    data = await get_rates(["tether"], [from_fiat, to_fiat])
    tether_rates = data["tether"]

    amount_in_usdt = amount / tether_rates[from_fiat]
    result = amount_in_usdt * tether_rates[to_fiat]
    return result


async def crypto_to_crypto(amount: float, from_crypto: str, to_crypto: str) -> float:
    """
    Конвертация крипта → крипта через USD как промежуточную валюту
    """
    from_crypto = from_crypto.lower()
    to_crypto = to_crypto.lower()

    data = await get_rates([from_crypto, to_crypto], ["usd"])
    from_rate = data[from_crypto]["usd"]   # курс 1 from_crypto → USD
    to_rate = data[to_crypto]["usd"]       # курс 1 to_crypto → USD

    amount_in_usd = amount * from_rate
    result = amount_in_usd / to_rate
    return result



