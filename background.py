import asyncio
from utils import TELEGRAM_API_URL, format_price, price_cache, fetch_all_coinlore_prices, TOKENS, CHANNEL_ID
import httpx
import os


async def start_price_checker():
    # print('[start_price_checker] is being called!')
    try:
        while True:
            await fetch_all_coinlore_prices()
            prices = {t: price_cache.get(t, {}).get(
                "price", "—") for t in TOKENS}
            await send_to_channel(build_message(prices))
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        # Price checker task was cancelled. Exiting gracefully
        raise
    except Exception as e:
        # print(f"[Background Error] {type(e).__name__}: {e}")
        raise  # Let the worker catch and log it too


def build_message(prices):
    l = ["*WKC Watcher 👀*\n🚀Live Token Prices🚀\n"]
    w = "wiki-cat"

    def format_line(token_id):
        token = TOKENS[token_id]
        price = prices.get(token_id, "—")
        emoji = token["emoji"]

        # Get change info
        cached = price_cache.get(token_id, {})
        chg = cached.get("chg_24")
        indicator = ""
        if chg:
            try:
                # arrow = "📈" if float(chg.replace('%', '')) >= 0 else "📉"
                indicator = "💹" if float(chg.replace('%', '')) >= 0 else "🔻"
            except:
                indicator = ""
        chg_txt = f"({chg})" if chg else ""

        return f"{emoji} *{token['display_name']}*: `${format_price(price)}` {indicator} {chg_txt} 24h"

    # Top section: WKC
    l.append(format_line(w))
    l.append("──────────────────")

    # Section: New Tokens
    l.append("*🎖 Commty Watchlist Tokens*\n")
    for k in ["the-kingdom-coin", "defi-tiger", "bnbtiger"]:
        l.append(format_line(k))
    l.append("──────────────────")

    # Section: Major Coins
    l.append("*🏅 Major Coins/Alts*\n")
    for k in ["bitcoin", "ethereum", "ripple", "binancecoin", "solana"]:
        l.append(format_line(k))

    l.append("──────────────────")
    l += [
        "🧵 *Follow:*",
        "🔗 [Creator on X](https://x.com/codeolam)",
        "🔗 [WikiCat on X](https://x.com/wikicatcoin)",
        "──────────────────",
        "\n🤖 [More market insights](https://t.me/kodOlam_bot)"
    ]

    return "\n".join(l)


async def send_to_channel(msg):
    # print('[send_to_channel] here now')
    async with httpx.AsyncClient() as c:
        await c.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "Markdown"}
        )
