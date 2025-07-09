import re
import os
import time
import json
import traceback
import httpx
from pathlib import Path
from datetime import datetime

CHAT_IDS_FILE = Path("chat_ids.json")
CHANNEL_ID = os.getenv('CHANNEL_ID')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}"

SUBSCRIPT_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

TOKENS = {
    "wiki-cat":    {
        "display_name": "WKC",
        "emoji": "👑",
        "pairAddress": "0x933477eba23726cA95A957cB85dBB1957267EF85",
        "chain": "bsc"
    },
    "the-kingdom-coin": {
        "display_name": "TKC",
        "emoji": "🌟",
        "pairAddress": "0xBeE567474f87F7725791F2872D165FB69e0bBcDd",
        "chain": "bsc"
    },
    "defi-tiger": {
        "display_name": "DTG",
        "emoji": "🌟",
        "pairAddress": "0xD2e4a524d1a932adbC70fb41F2bEC05884d5f6C2",
        "chain": "bsc"
    },
    "ocicat":   {
        "display_name": "Ocicat",
        "emoji": "🌟",
        "pairAddress": "0x1df65d3a75AeCd000A9c17c97E99993aF01DbcD1",
        "chain": "bsc"
    },
    "watter-rabbit":   {
        "display_name": "WAR",
        "emoji": "🌟",
        "pairAddress": "0xF1C2D7d7e539a02acC3f0C46Ca1e83c0F69BAaC2",
        "chain": "bsc"
    },
    "catcoin":   {
        "display_name": "CATS",
        "emoji": "🌟",
        "pairAddress": "0x56C2723807C398a5D263C698d660165802F104a8",
        "chain": "bsc"
    },
    "yukan":   {
        "display_name": "YUKAN",
        "emoji": "🌟",
        "pairAddress": "0x0797395fcAd3F27059405f266080701A77688C7f",
        "chain": "bsc"
    },
    "bnbtiger":   {
        "display_name": "BNBTIGER",
        "emoji": "🌟",
        "pairAddress": "0x5e1AAb9d49F6C7122df7dE4d6dBd5b03C1EBB0B7",
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


async def send_message_with_buttons(chat_id, text, inline_buttons):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": {"inline_keyboard": inline_buttons}
            }
        )


def format_change(chg):
    try:
        chg_str = str(chg).replace('%', '').strip()
        val = float(chg_str)

        if val > 0:
            return f"+{val:.2f}% ↑"
        elif val < 0:
            return f"{val:.2f}% ↓"
        else:
            return f"0.00%"
    except:
        return "—"


def format_large_number(n, compact=False):
    try:
        n = float(n)
        abs_n = abs(n)

        if not compact:
            return f"{n:,.2f}"

        if abs_n >= 1e+27:
            return f"{n / 1e+27:.2f}O"  # Octillion
        elif abs_n >= 1e+24:
            return f"{n / 1e+24:.2f}S"  # Septillion
        elif abs_n >= 1e+21:
            return f"{n / 1e+21:.2f}Q"  # Sextillion
        elif abs_n >= 1e+18:
            return f"{n / 1e+18:.2f}Qi"  # Quintillion
        elif abs_n >= 1e+15:
            return f"{n / 1e+15:.2f}P"  # Quadrillion
        elif abs_n >= 1e+12:
            return f"{n / 1e+12:.2f}T"  # Trillion
        elif abs_n >= 1e+9:
            return f"{n / 1e+9:.2f}B"   # Billion
        elif abs_n >= 1e+6:
            return f"{n / 1e+6:.2f}M"   # Million
        elif abs_n >= 1e+3:
            return f"{n / 1e+3:.2f}K"   # Thousand
        else:
            return f"{n:,.2f}"
    except:
        return str(n)


def format_price(p, compact=False):
    try:
        f = float(p)
        if compact and f >= 1_000:
            return format_large_number(f, compact=True)
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


def parse_price(s):
    """Convert formatted price string (e.g. '0.0₇1234') or scientific string to float."""
    try:
        if isinstance(s, (float, int)):
            return float(s)

        s = str(s).strip()

        # Regular float or scientific notation
        if re.fullmatch(r"-?\d+(\.\d+)?([eE][-+]?\d+)?", s):
            return float(s)

        # Match format like: 0.0₇1234
        if s.startswith("0.0₍") or s.startswith("0.0₇"):
            match = re.match(r"0\.0₍?(\d+)₎?(\d+)", s)
            if match:
                leading_zeros = int(match.group(1))
                sig_digits = match.group(2)
                return float(f"0.{'0'*leading_zeros}{sig_digits}")

        return float(s)
    except Exception:
        traceback.print_exc()
        return 0.0


async def get_price_with_change(token_id):
    token = TOKENS.get(token_id)
    if not token:
        return {"price": "N/A", "raw_price": 0, "chg_24": "—"}

    if "pairAddress" in token:  # DexScreener tokens
        data = await get_token_info_dexscreener(token_id)
        return {
            "price": data.get("price", "N/A"),
            "raw_price": data.get("raw_price", 0),
            "chg_24": data.get("chg_24", "—")
        }

    now = time.time()
    if token_id in price_cache and now - price_cache[token_id]["ts"] < CACHE_TTL:
        raw_price = float(price_cache[token_id].get("price", 0))
        return {
            "price": format_price(raw_price),
            "raw_price": raw_price,
            "chg_24": price_cache[token_id].get("chg_24", "—")
        }

    await fetch_all_coinlore_prices()
    raw_price = float(price_cache.get(token_id, {}).get("price", 0))
    return {
        "price": format_price(raw_price),
        "raw_price": raw_price,
        "chg_24": price_cache.get(token_id, {}).get("chg_24", "—")
    }


############ DexScreener functions ############


async def get_dexscreener_data(token_id):
    t = TOKENS.get(token_id)
    if not t or not t.get("pairAddress"):
        return None
    url = f"https://api.dexscreener.com/latest/dex/search?q={t['pairAddress']}"
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


async def get_token_info_dexscreener(token_id):
    d = await get_dexscreener_data(token_id)
    if not d:
        return {
            "name": "N/A",
            "price": "N/A",
            "raw_price": "N/A",
            "market_cap": "—",
            "liquidity": "—",
            "vol_24": "—",
            "chg_24": "—",
            "supply": "—",
            "txns": {"buys": "-", "sells": "-"},
            "created_at": "-",
            "pairAddress": TOKENS[token_id].get("pairAddress"),
            "msg": "⚠️ No data"
        }

    # Parse values safely
    price_str = d.get("priceUsd", "N/A")
    market_cap_str = d.get("marketCap", "N/A")
    volume = d.get("volume", {}).get("h24", "N/A")
    price = float(price_str) if price_str not in [None, "N/A"] else 0
    market_cap = float(market_cap_str) if market_cap_str not in [
        None, "N/A"] else 0
    created_at_ts = d.get("pairCreatedAt")
    txns = d.get("txns", {}).get("h24", {})
    txns_formatted = f"Buys: {txns.get('buys', 0)} | Sells: {txns.get('sells', 0)}"
    liquidity = d.get("liquidity", {}).get("usd", "-")

    # Calculate estimated circulating supply
    supply = market_cap / price if price > 0 else "N/A"

    return {
        "name": d.get("baseToken", {}).get("name", "N/A"),
        "price": format_price(d.get("priceUsd", "-")),
        "raw_price": float(d.get("priceUsd", 0)),
        "market_cap": format_price(market_cap_str, compact=True),
        "liquidity": format_price(liquidity, compact=True),
        "vol_24": format_price(volume, compact=True),
        "chg_24": f"{float(d.get('priceChange', {}).get('h24', 0)):.2f}%",
        "supply": format_price(supply, compact=True),
        "txns": txns_formatted,
        "created_at": datetime.fromtimestamp(created_at_ts / 1000).strftime('%Y-%m-%d') if created_at_ts else "—",
        "contract": d.get("baseToken", {}).get("address", "N/A"),
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


async def get_token_info(token_id):
    await fetch_all_coinlore_prices()
    data = price_cache.get(token_id, {})
    return {
        "name": TOKENS[token_id]['display_name'],
        "price": format_price(data.get("price", "N/A")),
        "market_cap": format_price(data.get("market_cap", "N/A"), compact=True),
        "liquidity": " N/A",
        "vol_24": format_price(data.get("vol_24", "N/A"), compact=True),
        "chg_24": data.get("chg_24", "—"),
        "supply": format_price(data.get("supply", "N/A"), compact=True),
        "txns": " N/A",
        "created_at": " N/A",
        "contract": " N/A",
        "msg": "✅ Ok 200"
    }

########### Fear & Greed + Dominance via CoinLore ###########


async def get_fear_greed():
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://api.alternative.me/fng/")
            r.raise_for_status()
        d = r.json().get("data", [{}])[0]
        return f"\nMeter: {d.get('value', '?')} ({d.get('value_classification', '?')})\n\n🔗 TG: @kodOlamWkcWatcher"
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
        return f"\nBTC: \t{btc:.2f}%  \nETH: \t{eth:.2f}%  \nAlt: \t{alt:.2f}%\n\n🔗 TG: @kodOlamWkcWatcher"
    except:
        traceback.print_exc()
        return "⚠️ Unavailable"
