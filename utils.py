import os
import time
import json
import traceback
import httpx
from pathlib import Path

CHAT_IDS_FILE = Path("chat_ids.json")
CHANNEL_ID = os.getenv('CHANNEL_ID')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}"

SUBSCRIPT_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

TOKENS = {
    "wiki-cat":    {
        "display_name": "WKC",
        "emoji": "👑",
        "contract": "0x933477eba23726cA95A957cB85dBB1957267EF85",
        "chain": "bsc"
    },
    "the-kingdom-coin": {
        "display_name": "TKC",
        "emoji": "🌟",
        "contract": "0xBeE567474f87F7725791F2872D165FB69e0bBcDd",
        "chain": "bsc"
    },
    "defi-tiger": {
        "display_name": "DTG",
        "emoji": "🌟",
        "contract": "0xD2e4a524d1a932adbC70fb41F2bEC05884d5f6C2",
        "chain": "bsc"
    },
    "bnbtiger":   {
        "display_name": "BNBTIGER",
        "emoji": "🌟",
        "contract": "0x5e1AAb9d49F6C7122df7dE4d6dBd5b03C1EBB0B7",
        "chain": "bsc"
    },
    "bitcoin":    {"display_name": "BTC",      "emoji": "💰", "coinlore_id": "90"},
    "ethereum":   {"display_name": "ETH",      "emoji": "💰", "coinlore_id": "80"},
    "ripple":     {"display_name": "XRP",      "emoji": "💰", "coinlore_id": "58"},
    "binancecoin": {"display_name": "BNB",      "emoji": "💰", "coinlore_id": "2710"},
    "solana":     {"display_name": "SOL",      "emoji": "💰", "coinlore_id": "48543"},
}

CACHE_TTL = 60
price_cache = {}


async def send_message(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )


def get_chat_ids():
    return json.loads(CHAT_IDS_FILE.read_text()) if CHAT_IDS_FILE.exists() else []


def register_chat_id(chat_id):
    ids = get_chat_ids()
    if chat_id not in ids:
        ids.append(chat_id)
        CHAT_IDS_FILE.write_text(json.dumps(ids))


def format_price(p):
    try:
        f = float(p)
        if f >= 0.01:
            return f"{f:,.2f}"
        elif f >= 0.00001:
            return f"{f:.10f}".rstrip("0").rstrip(".")
        else:
            parts = f"{f:.60f}".split(".")[1]
            decimals = parts.lstrip("0")
            leading = len(parts) - len(decimals)
            significant = (decimals + "0000")[:4]
            sub = str(leading).translate(SUBSCRIPT_MAP)
            return f"0.0{sub}{significant}"
    except:
        return str(p)


async def get_price_with_change(token_id):
    token = TOKENS.get(token_id)
    if not token:
        return {"price": "N/A", "chg_24": "—"}

    if "contract" in token:  # DexScreener tokens
        data = await get_token_info_dexscreener(token_id)
        return {
            "price": data.get("price", "N/A"),
            "chg_24": data.get("chg_24", "—")
        }

    # CoinLore tokens (major coins)
    now = time.time()
    if token_id in price_cache and now - price_cache[token_id]["ts"] < CACHE_TTL:
        return {
            "price": price_cache[token_id].get("price", "N/A"),
            "chg_24": price_cache[token_id].get("chg_24", "—")
        }

    await fetch_all_coinlore_prices()
    return {
        "price": price_cache.get(token_id, {}).get("price", "N/A"),
        "chg_24": price_cache.get(token_id, {}).get("chg_24", "—")
    }


############ DexScreener functions ############


async def get_dexscreener_data(token_id):
    t = TOKENS.get(token_id)
    if not t or not t.get("contract"):
        return None
    url = f"https://api.dexscreener.com/latest/dex/search?q={t['contract']}"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url)
            r.raise_for_status()
            data = r.json()
        for pair in data.get("pairs", []):
            if pair.get("quoteToken", {}).get("symbol", "").upper() == "USD":
                return pair
        return data.get("pairs", [None])[0]
    except Exception:
        traceback.print_exc()
        return None


async def get_price_dexscreener(token_id):
    d = await get_dexscreener_data(token_id)
    return d.get("priceUsd", "N/A") if d else "N/A"


async def get_token_info_dexscreener(token_id):
    d = await get_dexscreener_data(token_id)
    if not d:
        return {
            "price": "N/A",
            "market_cap": "—",
            "vol_24": "—",
            "chg_24": "—",
            "supply": "—",
            "contract": TOKENS[token_id].get("contract"),
            "msg": "⚠️ No data"
        }

    # Parse values safely
    price_str = d.get("priceUsd", "N/A")
    market_cap_str = d.get("marketCap", "N/A")
    volume = d.get("volume", {}).get("h24", "N/A")
    price = float(price_str) if price_str not in [None, "N/A"] else 0
    market_cap = float(market_cap_str) if market_cap_str not in [
        None, "N/A"] else 0

    # Calculate estimated circulating supply
    supply = market_cap / price if price > 0 else "N/A"

    return {
        "price": format_price(d.get("priceUsd", "N/A")),
        "market_cap": format_price(market_cap_str),
        "vol_24": format_price(volume),
        "chg_24": f"{float(d.get('priceChange', {}).get('h24', 0)):.2f}%",
        "supply": format_price(supply),
        "contract": d.get("pairAddress", TOKENS[token_id].get("contract")),
        "msg": "✅ Ok 200"
    }

############ Coinbase fallback for majors ############


async def fetch_all_coinlore_prices():
    ids = ",".join([t["coinlore_id"]
                   for t in TOKENS.values() if t.get("coinlore_id")])
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://api.coinlore.net/api/ticker/?id={ids}")
            r.raise_for_status()
            data = r.json()
        now = time.time()
        id2key = {t["coinlore_id"]: k for k,
                  t in TOKENS.items() if t.get("coinlore_id")}
        for coin in data:
            key = id2key.get(coin["id"])
            if key:
                price_cache[key] = {
                    "price": coin["price_usd"],
                    "chg_24": coin.get("percent_change_24h", "")+"%",
                    "market_cap": coin.get("market_cap_usd", "?"),
                    "vol_24": coin.get("volume24", "?"),
                    "supply": coin.get("csupply", "?"),
                    "ts": now
                }
    except Exception:
        traceback.print_exc()


async def get_price_coinlore(token_id):
    now = time.time()
    token = TOKENS.get(token_id)
    if not token or not token.get("coinlore_id"):
        return "N/A"
    if token_id not in price_cache or now - price_cache[token_id]["ts"] > CACHE_TTL:
        await fetch_all_coinlore_prices()
    return price_cache.get(token_id, {}).get("price", "N/A")


async def get_token_info(token_id):
    await fetch_all_coinlore_prices()
    data = price_cache.get(token_id, {})
    return {
        "price": format_price(data.get("price", "N/A")),
        "market_cap": format_price(data.get("market_cap", "N/A")),
        "vol_24": format_price(data.get("vol_24", "N/A")),
        "chg_24": data.get("chg_24", "—"),
        "supply": format_price(data.get("supply", "N/A")),
        "contract": "N/A",
        "msg": "✅ Ok 200"
    }

########### Fear & Greed + Dominance via CoinLore ###########


async def get_fear_greed():
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://api.alternative.me/fng/")
            r.raise_for_status()
        d = r.json().get("data", [{}])[0]
        return f"{d.get('value', '?')} ({d.get('value_classification', '?')})"
    except:
        traceback.print_exc()
        return "⚠️ Unavailable"


async def get_dominance():
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://api.coinlore.net/api/global/", timeout=10)
            r.raise_for_status()
        d = r.json()[0]
        btc, eth = float(d.get("btc_d", 0)), float(d.get("eth_d", 0))
        alt = round(100 - btc - eth, 2)
        return f"\nBTC: \t{btc:.2f}%  \nETH: \t{eth:.2f}%  \nAlt: \t{alt:.2f}%"
    except:
        traceback.print_exc()
        return "⚠️ Unavailable"


# import os
# import time
# import json
# from pathlib import Path
# import traceback
# import httpx

# CHAT_IDS_FILE = Path("chat_ids.json")
# CHANNEL_ID = os.getenv('CHANNEL_ID')
# TELEGRAM_API_URL = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}"
# SUBSCRIPT_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

# TOKENS = {
#     "wiki-cat": {
#         "display_name": "WKC",
#         "emoji": "👑",
#         "contract": "0x933477eba23726cA95A957cB85dBB1957267EF85",
#         "chain": "bsc"
#     },
#     "the-kingdom-coin": {
#         "display_name": "TKC",
#         "emoji": "🌟",
#         "contract": "0xBeE567474f87F7725791F2872D165FB69e0bBcDd",  # Replace with real
#         "chain": "bsc"
#     },
#     "defi-tiger": {
#         "display_name": "DTG",
#         "emoji": "🌟",
#         "contract": "0xD2e4a524d1a932adbC70fb41F2bEC05884d5f6C2",
#         "chain": "bsc"
#     },
#     "bnbtiger": {
#         "display_name": "BNBTIGER",
#         "emoji": "🌟",
#         "contract": "0x5e1AAb9d49F6C7122df7dE4d6dBd5b03C1EBB0B7",
#         "chain": "bsc"
#     },
#     "bitcoin": {"display_name": "BTC", "emoji": "💰", "coinlore_id": "90"},
#     "ethereum": {"display_name": "ETH", "emoji": "💰", "coinlore_id": "80"},
#     "ripple": {"display_name": "XRP", "emoji": "💰", "coinlore_id": "58"},
#     "binancecoin": {"display_name": "BNB", "emoji": "💰", "coinlore_id": "2710"},
#     "solana": {"display_name": "SOL", "emoji": "💰", "coinlore_id": "48543"},
# }
# # TOKENS = {
# #     "wiki-cat": {"display_name": "WKC", "emoji": "👑", "coinlore_id": "70961"},
# #     "the-kingdom-coin": {"display_name": "TKC", "emoji": "🌟", "coinlore_id": "133151"},
# #     "defi-tiger": {"display_name": "DTG", "emoji": "🌟", "coinlore_id": "82727"},
# #     "bnbtiger": {"display_name": "BNBTIGER", "emoji": "🌟", "coinlore_id": "85953"},
# #     "bitcoin": {"display_name": "BTC", "emoji": "💰", "coinlore_id": "90"},
# #     "ethereum": {"display_name": "ETH", "emoji": "💰", "coinlore_id": "80"},
# #     "ripple": {"display_name": "XRP", "emoji": "💰", "coinlore_id": "58"},
# #     "binancecoin": {"display_name": "BNB", "emoji": "💰", "coinlore_id": "2710"},
# #     "solana": {"display_name": "SOL", "emoji": "💰", "coinlore_id": "48543"},
# # }
# CACHE_TTL = 60
# price_cache = {}  # Structure: {token_id: {'price': str, 'ts': timestamp}}


# def get_chat_ids():
#     return json.loads(CHAT_IDS_FILE.read_text()) if CHAT_IDS_FILE.exists() else []


# def register_chat_id(chat_id):
#     ids = get_chat_ids()
#     if chat_id not in ids:
#         ids.append(chat_id)
#         CHAT_IDS_FILE.write_text(json.dumps(ids))


# def format_price(price):
#     try:
#         f = float(price)

#         if f >= 0.01:
#             return f"{f:,.2f}"
#         elif f >= 0.00001:
#             return f"{f:.10f}".rstrip("0").rstrip(".")
#         else:
#             # Dexscreener-style formatting with 4 digits after the subscript
#             parts = f"{f:.60f}".split(".")
#             decimals = parts[1].lstrip("0")
#             leading_zeros = len(parts[1]) - len(decimals)

#             # Pad with extra zeros if not enough digits
#             significant = (decimals + "0000")[:4]
#             subscript = str(leading_zeros).translate(SUBSCRIPT_MAP)
#             return f"0.0{subscript}{significant}"
#     except:
#         return str(price)


# async def send_message(chat_id, text):
#     async with httpx.AsyncClient() as client:
#         await client.post(
#             f"{TELEGRAM_API_URL}/sendMessage",
#             json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
#         )


# async def get_dexscreener_data(token_id):
#     token = TOKENS.get(token_id)
#     if not token:
#         return None

#     contract = token.get("contract")
#     if not contract:
#         return None

#     url = f"https://api.dexscreener.com/latest/dex/search?q={contract}"
#     try:
#         async with httpx.AsyncClient(timeout=10) as client:
#             r = await client.get(url)
#             r.raise_for_status()
#             data = r.json()
#             pairs = data.get("pairs", [])

#             # Find the one with USD quote
#             pair = next((p for p in pairs if p.get("quoteToken", {}).get(
#                 "symbol", "").upper() == "USD"), None)
#             if not pair and pairs:
#                 pair = pairs[0]  # fallback to first

#             return pair
#     except Exception as e:
#         traceback.print_exc()
#         return None


# async def get_price_dexscreener(token_id):
#     data = await get_dexscreener_data(token_id)
#     if not data:
#         return "N/A"
#     return data.get("priceUsd", "N/A")


# async def get_token_info_dexscreener(token_id):
#     try:
#         data = await get_dexscreener_data(token_id)
#         if not data:
#             return {
#                 "price": "N/A",
#                 "market_cap": "—",
#                 "vol_24": "—",
#                 "chg_24": "—",
#                 "supply": "—",
#                 "contract": TOKENS[token_id].get("contract", "N/A"),
#                 "msg": "⚠️ Ooops Could not retrieve data!"
#             }

#         return {
#             "price": format_price(data.get("priceUsd", "N/A")),
#             "market_cap": format_price(data.get("fdv", "N/A")),
#             "vol_24": format_price(data.get("volume", "N/A")),
#             "chg_24": f"{float(data.get('priceChange', 0)):.2f}%",
#             "supply": format_price(data.get("liquidity", {}).get("base", "N/A")),
#             "contract": data.get("pairAddress", TOKENS[token_id].get("contract")),
#             "msg": "✅ Ok 200"
#         }

#     except Exception as e:
#         traceback.print_exc()
#         return {
#             "price": "N/A",
#             "market_cap": "—",
#             "vol_24": "—",
#             "chg_24": "—",
#             "supply": "—",
#             "contract": TOKENS[token_id].get("contract", "N/A"),
#             "msg": f"⚠️ Error:\nReason: {e}"
#         }


# # async def fetch_all_coinlore_prices():
# #     """Fetch exact prices using batch CoinLore ticker by IDs"""
# #     try:
# #         ids = ",".join([token["coinlore_id"] for token in TOKENS.values()])
# #         async with httpx.AsyncClient() as client:
# #             r = await client.get(f"https://api.coinlore.net/api/ticker/?id={ids}")
# #             r.raise_for_status()
# #             data = r.json()

# #         now = time.time()
# #         id_map = {v["coinlore_id"]: k for k, v in TOKENS.items()}

# #         for coin in data:
# #             token_key = id_map.get(coin["id"])
# #             if token_key:
# #                 price_cache[token_key] = {
# #                     "price": coin.get("price_usd", "N/A"),
# #                     "chg_24": coin.get("percent_change_24h", None) + "%" if coin.get("percent_change_24h") else None,
# #                     "ts": now
# #                 }

# #     except Exception as e:
# #         # print(f"[CoinLore Fetch Error] {type(e).__name__}: {e}")
# #         traceback.print_exc()


# # async def get_price_coinlore(token_id):
# #     now = time.time()
# #     token = TOKENS.get(token_id)
# #     if not token:
# #         return "N/A"
# #     if token_id in price_cache and now - price_cache[token_id]["ts"] < CACHE_TTL:
# #         return price_cache[token_id]["price"]
# #     await fetch_all_coinlore_prices()
# #     return price_cache.get(token_id, {}).get("price", "N/A")


# # async def get_token_info(token_id):
# #     # Try fetching price from CoinLore
# #     try:
# #         price = await get_price_coinlore(token_id) or "—"
# #     except Exception as e:
# #         print(f"Error fetching price from CoinLore: {e}")
# #         price = "—"

# #     # Try fetching metadata from CoinGecko
# #     try:
# #         async with httpx.AsyncClient(timeout=10) as client:
# #             r = await client.get(
# #                 f"https://api.coingecko.com/api/v3/coins/{token_id}",
# #                 params={"localization": "false"}
# #             )
# #             r.raise_for_status()  # Raise if HTTP error (4xx/5xx)
# #             data = r.json()

# #         market_data = data.get("market_data", {})
# #         platforms = data.get("platforms", {"N/A": None})

# #         return {
# #             "price": format_price(price),
# #             "market_cap": format_price(market_data.get("market_cap", {}).get("usd", 0)) if market_data else "—",
# #             "vol_24": format_price(market_data.get("total_volume", {}).get("usd", 0)) if market_data else "—",
# #             "chg_24": f"{market_data.get('price_change_percentage_24h', 0):.2f}%",
# #             "supply": format_price(market_data.get("circulating_supply", 0)),
# #             "contract": next(iter(platforms.values()), "N/A"),
# #             "msg": "Success!"
# #         }

# #     except Exception as e:
# #         traceback.print_exc()

# #     # If anything goes wrong, return fallback response
# #     return {
# #         "price": format_price(price),
# #         "market_cap": "—",
# #         "vol_24": "—",
# #         "chg_24": "—",
# #         "supply": "—",
# #         "contract": "N/A",
# #         "msg": f"⚠️ Could not retrieve information"
# #     }


# async def get_fear_greed():
#     try:
#         async with httpx.AsyncClient(timeout=10) as client:
#             r = await client.get("https://api.alternative.me/fng/")
#             r.raise_for_status()  # Raises for 4xx/5xx errors

#         data = r.json()
#         fng = data.get("data", [{}])[0]
#         value = fng.get("value")
#         classification = fng.get("value_classification")

#         if not value or not classification:
#             raise ValueError("Incomplete F&G data")

#         return f"{value} ({classification})"

#     except Exception as e:
#         traceback.print_exc()

#     return f"⚠️ Fear & Greed Index: Unavailable at the moment"


# async def get_dominance():
#     try:
#         async with httpx.AsyncClient() as client:
#             r = await client.get("https://api.coinlore.net/api/global/")
#             r.raise_for_status()
#             d = r.json()[0]

#         btc = float(d.get("btc_d", 0))
#         eth = float(d.get("eth_d", 0))
#         alt = round(100 - btc - eth, 2)
#         return f"BTC: \t{btc:.2f}%\nETH: \t{eth:.2f}%\nAlt: \t{alt:.2f}%"

#     except Exception:
#         traceback.print_exc()
#         return "⚠️ Could not fetch dominance info right now"

# # async def get_dominance():
# #     try:
# #         async with httpx.AsyncClient() as client:
# #             r = await client.get("https://api.coingecko.com/api/v3/global", timeout=10)
# #         r.raise_for_status()
# #         data = r.json().get("data", {}).get("market_cap_percentage", {})

# #         btc, eth = float(data.get("btc", 0)), float(data.get("eth", 0))
# #         alt = round(100 - btc - eth, 2)
# #         return f"BTC: \t{btc:.2f}%\nETH: \t{eth:.2f}%\nAlt: \t{alt:.2f}%"
# #     except Exception as error:
# #         traceback.print_exc()
# #         return f"⚠️ Could not fetch dominance at the moment"
