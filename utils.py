import os
import time
import json
from pathlib import Path
import traceback
import httpx

CHAT_IDS_FILE = Path("chat_ids.json")
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


# import json
# from pathlib import Path
# import httpx
# import os

# CHAT_IDS_FILE = Path("chat_ids.json")
# TELEGRAM_API_URL = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}"

# TOKENS = {
#     "wiki-cat": {"emoji": "💰👑📈", "display_name": "WKC", "logo": "https://assets.coingecko.com/coins/images/29577/thumb/wikicat.png"},
#     "bitcoin": {"emoji": "💰📈", "display_name": "BTC", "logo": "https://assets.coingecko.com/coins/images/1/thumb/bitcoin.png"},
#     "ethereum": {"emoji": "💰📈", "display_name": "ETH", "logo": "https://assets.coingecko.com/coins/images/279/thumb/ethereum.png"},
#     "ripple": {"emoji": "💰📈", "display_name": "XRP", "logo": "https://assets.coingecko.com/coins/images/44/thumb/xrp-symbol-white-128.png"},
#     "binancecoin": {"emoji": "💰📈", "display_name": "BNB", "logo": "https://assets.coingecko.com/coins/images/825/thumb/bnb-icon2_2x.png"},
#     "solana": {"emoji": "💰📈", "display_name": "SOL", "logo": "https://assets.coingecko.com/coins/images/4128/thumb/solana.png"},
# }


# def get_chat_ids():
#     if not CHAT_IDS_FILE.exists():
#         return []
#     with open(CHAT_IDS_FILE) as f:
#         return json.load(f)


# def register_chat_id(chat_id):
#     ids = get_chat_ids()
#     if chat_id not in ids:
#         ids.append(chat_id)
#         with open(CHAT_IDS_FILE, "w") as f:
#             json.dump(ids, f)


# async def send_message(chat_id, text):
#     async with httpx.AsyncClient() as client:
#         await client.post(
#             f"{TELEGRAM_API_URL}/sendMessage",
#             json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
#         )


# async def send_token_info(chat_id, token_id):
#     data = TOKENS[token_id]
#     emoji = data["emoji"]
#     logo = data["logo"]
#     info = await get_token_info(token_id)

#     # Check if info is a dict; if not, it's an error string
#     if not isinstance(info, dict):
#         await send_message(chat_id, f"{info}")
#         return

#     caption = (
#         f"{emoji} *{data['display_name']}*\n"
#         f"📊 Info for {info.get('name', token_id.upper())}\n\n"
#         f"💵 Price: ${info.get('price', 'N/A')}\n"
#         f"📈 24h Change: {info.get('change_24h', 'N/A')}%\n"
#         f"💰 Market Cap: ${info.get('market_cap', 'N/A')}\n"
#         f"💧 Volume (24h): ${info.get('volume_24h', 'N/A')}\n"
#         f"🔁 Circulating Supply: {info.get('circulating_supply', 'N/A')}\n"
#         f"🪙 Contract Address: {info.get('contract_address', 'N/A')} ({info.get('platform', 'N/A')})"
#     )

#     async with httpx.AsyncClient() as client:
#         await client.post(
#             f"{TELEGRAM_API_URL}/sendPhoto",
#             json={
#                 "chat_id": chat_id,
#                 "photo": logo,
#                 "caption": caption,
#                 "parse_mode": "Markdown"
#             }
#         )


# async def get_token_info(token_id):
#     try:
#         async with httpx.AsyncClient() as client:
#             r = await client.get(
#                 f"https://api.coingecko.com/api/v3/coins/{token_id}",
#                 params={"localization": "false"},
#                 timeout=10
#             )
#             data = r.json()

#             # Debug log
#             if "market_data" not in data:
#                 print(f"[WARN] Unexpected response for {token_id}: {data}")
#                 return f"🚧 Could not fetch information for {token_id}."

#             market_data = data.get("market_data", {})
#             platforms = data.get("platforms", {})

#             if platforms:
#                 platform_name, contract_address = next(iter(platforms.items()))
#             else:
#                 platform_name, contract_address = "N/A", "N/A"

#             return {
#                 "price": format_price(market_data.get("current_price", {}).get("usd")),
#                 "market_cap": market_data.get("market_cap", {}).get("usd", "N/A"),
#                 "volume": market_data.get("total_volume", {}).get("usd", "N/A"),
#                 "percent_change": market_data.get("price_change_percentage_24h", "N/A"),
#                 "circulating_supply": market_data.get("circulating_supply", "N/A"),
#                 "contract_address": contract_address,
#                 "platform_name": platform_name,
#             }
#     except Exception as e:
#         print(f"[ERROR] Fetching token info for {token_id}: {e}")
#         return f"🚧 An error occured! Could not fetch information for {token_id}."


# async def get_token_price(token_id):
#     try:
#         async with httpx.AsyncClient() as client:
#             r = await client.get(
#                 "https://api.coingecko.com/api/v3/simple/price",
#                 params={"ids": token_id, "vs_currencies": "usd"},
#                 timeout=10
#             )
#             return format_price(r.json().get(token_id, {}).get("usd"))
#     except Exception as e:
#         print(f"Error fetching {token_id}: {e}")
#         return None


# def format_price(price):
#     try:
#         price = float(price)
#     except (TypeError, ValueError):
#         return "N/A"

#     if price >= 1:
#         return f"{price:,.2f}"
#     elif price >= 0.01:
#         return f"{price:.4f}"
#     elif price >= 0.0001:
#         return f"{price:.6f}"
#     else:
#         return f"{price:.15f}".rstrip("0").rstrip(".")


# async def get_fear_and_greed_index():
#     try:
#         async with httpx.AsyncClient() as client:
#             r = await client.get("https://api.alternative.me/fng/")
#             data = r.json()["data"][0]
#             return f"🙀🤑 *Fear & Greed Index*: {data['value']} ({data['value_classification']})"
#     except:
#         return "🚧 Could not fetch index."


# async def get_market_dominance():
#     try:
#         async with httpx.AsyncClient() as client:
#             r = await client.get("https://api.coingecko.com/api/v3/global")
#             market_data = r.json().get("data", {})
#             btc = market_data["market_cap_percentage"]["btc"]
#             eth = market_data["market_cap_percentage"]["eth"]
#             alt = 100 - btc
#             return f"📈 *Market Dominance*\n• BTC: {btc:.2f}%\n• ETH: {eth:.2f}%\n• Altcoins: {alt:.2f}%"
#     except Exception as error:
#         print(f'error: {error}')
#         return f"🚧 Could not fetch dominance."


# def get_token_id_from_command(command_name: str) -> str:
#     """
#     Converts a command like 'wiki_cat' to the real token ID 'wiki-cat'.
#     """
#     for token_id in TOKENS:
#         if command_name == token_id.replace("-", "_"):
#             return token_id
#     return None
