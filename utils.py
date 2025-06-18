import os
import time
import json
from pathlib import Path
import traceback
import httpx

CHAT_IDS_FILE = Path("chat_ids.json")
CHANNEL_ID = os.getenv('CHANNEL_ID')
# CHANNEL_ID = "-1002703612913"  # This is your @kodOlamWkcWatcher channel ID
# CHANNEL_ID = "@kodOlamWkcWatcher"  # This is your @kodOlamWkcWatcher channel ID
TELEGRAM_API_URL = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}"

TOKENS = {
    "wiki-cat": {"display_name": "WKC", "emoji": "💰👑📈", "coinlore_id": "70961"},
    "bitcoin": {"display_name": "BTC", "emoji": "💰📈", "coinlore_id": "90"},
    "ethereum": {"display_name": "ETH", "emoji": "💰📈", "coinlore_id": "80"},
    "ripple": {"display_name": "XRP", "emoji": "💰📈", "coinlore_id": "58"},
    "binancecoin": {"display_name": "BNB", "emoji": "💰📈", "coinlore_id": "2710"},
    "solana": {"display_name": "SOL", "emoji": "💰📈", "coinlore_id": "48543"},
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


def format_price(num):
    try:
        price = float(num)
    except:
        return None
    if price >= 1:
        return f"{price:,.2f}"
    elif price >= 0.01:
        return f"{price:.4f}"
    return f"{price:.10f}".rstrip("0")


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
                    "ts": now
                }

    except Exception as e:
        print(f"[CoinLore Fetch Error] {type(e).__name__}: {e}")
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
    price = await get_price_coinlore(token_id) or "—"
    # fetch metadata from CoinGecko for extras
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://api.coingecko.com/api/v3/coins/{token_id}", params={"localization": "false"})
    if r.status_code != 200:
        return {"price": format_price(price), "msg": "Metadata unavailable."}
    d = r.json().get("market_data", {})
    return {
        "price": format_price(price),
        "market_cap": format_price(d["market_cap"]["usd"]) if d.get("market_cap") else "—",
        "vol_24": format_price(d["total_volume"]["usd"]) if d.get("total_volume") else "—",
        "chg_24": f"{d.get('price_change_percentage_24h', 0):.2f}%",
        "supply": format_price(d.get("circulating_supply", 0)),
        "contract": next(iter(r.json().get("platforms", {"N/A": None}).values()), None)
    }


async def get_fear_greed():
    async with httpx.AsyncClient() as client:
        r = await client.get("https://api.alternative.me/fng/")
    if r.status_code != 200:
        return "Unavailable"
    d = r.json()["data"][0]
    return f"{d['value']} ({d['value_classification']})"


async def get_dominance():
    async with httpx.AsyncClient() as client:
        r = await client.get("https://api.coingecko.com/api/v3/global")
    d = r.json()["data"]["market_cap_percentage"]
    btc, eth = d.get("btc", 0), d.get("eth", 0)
    return f"BTC: \t{btc:.2f}%\nETH: \t{eth:.2f}%\nAlt: \t{100-btc-eth:.2f}%"
