import os
import time
import json
from pathlib import Path
import traceback
import httpx

CHAT_IDS_FILE = Path("chat_ids.json")
CHANNEL_ID = os.getenv('CHANNEL_ID')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}"
SUBSCRIPT_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

TOKENS = {
    "wiki-cat": {"display_name": "WKC", "emoji": "👑", "coinlore_id": "70961"},
    "the-kingdom-coin": {"display_name": "TKC", "emoji": "🌟", "coinlore_id": "133151"},
    "defi-tiger": {"display_name": "DTG", "emoji": "🌟", "coinlore_id": "82727"},
    "bnbtiger": {"display_name": "BNBTIGER", "emoji": "🌟", "coinlore_id": "85953"},
    "bitcoin": {"display_name": "BTC", "emoji": "💰", "coinlore_id": "90"},
    "ethereum": {"display_name": "ETH", "emoji": "💰", "coinlore_id": "80"},
    "ripple": {"display_name": "XRP", "emoji": "💰", "coinlore_id": "58"},
    "binancecoin": {"display_name": "BNB", "emoji": "💰", "coinlore_id": "2710"},
    "solana": {"display_name": "SOL", "emoji": "💰", "coinlore_id": "48543"},
}
CACHE_TTL = 60
price_cache = {}  # Structure: {token_id: {'price': str, 'ts': timestamp}}


def get_chat_ids():
    return json.loads(CHAT_IDS_FILE.read_text()) if CHAT_IDS_FILE.exists() else []


def register_chat_id(chat_id):
    ids = get_chat_ids()
    if chat_id not in ids:
        ids.append(chat_id)
        CHAT_IDS_FILE.write_text(json.dumps(ids))


def format_price(price):
    try:
        f = float(price)

        if f >= 0.01:
            return f"{f:,.2f}"
        elif f >= 0.00001:
            return f"{f:.10f}".rstrip("0").rstrip(".")
        else:
            # Dexscreener-style formatting with 4 digits after the subscript
            parts = f"{f:.60f}".split(".")
            decimals = parts[1].lstrip("0")
            leading_zeros = len(parts[1]) - len(decimals)

            # Pad with extra zeros if not enough digits
            significant = (decimals + "0000")[:4]
            subscript = str(leading_zeros).translate(SUBSCRIPT_MAP)
            return f"0.0{subscript}{significant}"
    except:
        return str(price)


async def send_message(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )


async def fetch_all_coinlore_prices():
    """Fetch exact prices using batch CoinLore ticker by IDs"""
    try:
        ids = ",".join([token["coinlore_id"] for token in TOKENS.values()])
        async with httpx.AsyncClient() as client:
            r = await client.get(f"https://api.coinlore.net/api/ticker/?id={ids}")
            r.raise_for_status()
            data = r.json()

        now = time.time()
        id_map = {v["coinlore_id"]: k for k, v in TOKENS.items()}

        for coin in data:
            token_key = id_map.get(coin["id"])
            if token_key:
                price_cache[token_key] = {
                    "price": coin.get("price_usd", "N/A"),
                    "chg_24": coin.get("percent_change_24h", None) + "%" if coin.get("percent_change_24h") else None,
                    "ts": now
                }

    except Exception as e:
        # print(f"[CoinLore Fetch Error] {type(e).__name__}: {e}")
        traceback.print_exc()


async def get_price_coinlore(token_id):
    now = time.time()
    token = TOKENS.get(token_id)
    if not token:
        return "N/A"
    if token_id in price_cache and now - price_cache[token_id]["ts"] < CACHE_TTL:
        return price_cache[token_id]["price"]
    await fetch_all_coinlore_prices()
    return price_cache.get(token_id, {}).get("price", "N/A")


async def get_token_info(token_id):
    # Try fetching price from CoinLore
    try:
        price = await get_price_coinlore(token_id) or "—"
    except Exception as e:
        print(f"Error fetching price from CoinLore: {e}")
        price = "—"

    # Try fetching metadata from CoinGecko
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://api.coingecko.com/api/v3/coins/{token_id}",
                params={"localization": "false"}
            )
            r.raise_for_status()  # Raise if HTTP error (4xx/5xx)
            data = r.json()

        market_data = data.get("market_data", {})
        platforms = data.get("platforms", {"N/A": None})

        return {
            "price": format_price(price),
            "market_cap": format_price(market_data.get("market_cap", {}).get("usd", 0)) if market_data else "—",
            "vol_24": format_price(market_data.get("total_volume", {}).get("usd", 0)) if market_data else "—",
            "chg_24": f"{market_data.get('price_change_percentage_24h', 0):.2f}%",
            "supply": format_price(market_data.get("circulating_supply", 0)),
            "contract": next(iter(platforms.values()), "N/A"),
            "msg": "Success!"
        }

    except Exception as e:
        traceback.print_exc()

    # If anything goes wrong, return fallback response
    return {
        "price": format_price(price),
        "market_cap": "—",
        "vol_24": "—",
        "chg_24": "—",
        "supply": "—",
        "contract": "N/A",
        "msg": f"⚠️ Could not retrieve information"
    }


async def get_fear_greed():
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.alternative.me/fng/")
            r.raise_for_status()  # Raises for 4xx/5xx errors

        data = r.json()
        fng = data.get("data", [{}])[0]
        value = fng.get("value")
        classification = fng.get("value_classification")

        if not value or not classification:
            raise ValueError("Incomplete F&G data")

        return f"{value} ({classification})"

    except Exception as e:
        traceback.print_exc()

    return f"⚠️ Fear & Greed Index: Unavailable at the moment"


async def get_dominance():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://api.coingecko.com/api/v3/global", timeout=10)
        r.raise_for_status()
        data = r.json().get("data", {}).get("market_cap_percentage", {})

        btc, eth = float(data.get("btc", 0)), float(data.get("eth", 0))
        alt = round(100 - btc - eth, 2)
        return f"BTC: \t{btc:.2f}%\nETH: \t{eth:.2f}%\nAlt: \t{alt:.2f}%"
    except Exception as error:
        traceback.print_exc()
        return f"⚠️ Could not fetch dominance at the moment"
