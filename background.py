import asyncio
import httpx
from utils import TELEGRAM_API_URL, format_price, get_price_with_change, TOKENS, CHANNEL_ID, fetch_all_coinlore_prices


async def start_price_checker():
    while True:
        await fetch_all_coinlore_prices()  # Cache CoinLore tokens

        prices = {}
        for k in TOKENS:
            # Unified format: {"price": "...", "chg_24": "…"}
            prices[k] = await get_price_with_change(k)

        await send_to_channel(build_message(prices))
        await asyncio.sleep(60)


def build_message(prices):
    def line(k):
        t = TOKENS[k]
        token_data = prices.get(k, {})
        price = token_data.get("price", "N/A")
        chg = token_data.get("chg_24", "—")

        indicator = ""
        try:
            chg_num = float(chg.replace('%', '').strip())
            indicator = "💹" if chg_num >= 0 else "🔻"
        except:
            pass

        return f"{t['emoji']} *{t['display_name']}*: `${format_price(price)}` {indicator} ({chg}) 24h"

    lines = [
        "*WKC Watcher 👀*\n🚀Live Token Prices🚀\n",
        line("wiki-cat"), "──────────────────",
        "*🎖 Commty Watchlist*\n", *
        (line(k)
         for k in ["the-kingdom-coin", "defi-tiger", "bnbtiger", "ocicat", "watter-rabbit", "catcoin"]),
        "──────────────────", "*🏅 Major Coins*\n", *
        (line(k)
         for k in ["bitcoin", "ethereum", "ripple", "binancecoin", "solana"]),
        "──────────────────",
        "🧵 *Follow:*",
        "🔗 [Creator on X](https://x.com/codeolam)",
        "🔗 [WikiCat on X](https://x.com/wikicatcoin)",
        "──────────────────",
        "\n🤖 [More market insights](https://t.me/kodOlam_bot)"
    ]
    return "\n".join(lines)


async def send_to_channel(msg):
    async with httpx.AsyncClient() as c:
        await c.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "Markdown"})
