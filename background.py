import asyncio
import os
import httpx
from utils import TELEGRAM_API_URL, format_price, get_price_with_change, TOKENS, CHANNEL_ID, fetch_all_coinlore_prices


async def start_price_checker():
    while True:
        await fetch_all_coinlore_prices()
        prices = {k: await get_price_with_change(k) for k in TOKENS}
        msg = build_message(prices)
        buttons = [
            [{"text": "Creator on X",
                "url": "https://x.com/codeolam"}],
            [{"text": "WikiCat on X",
                "url": "https://x.com/wikicatcoin"}],
            [{"text": "🤖 Bot Playground",
                "url": "https://t.me/kodOlam_bot"}],
        ]
        await send_to_channel(msg, buttons)
        await asyncio.sleep(120)


def build_message(prices):
    def line(k):
        t = TOKENS[k]
        data = prices.get(k, {})
        price = data.get("price", "N/A")
        chg = data.get("chg_24", "—")
        fdv = data.get("fdv", "")
        ind = ""
        try:
            ind = "💹" if float(chg.replace('%', '').strip()) >= 0 else "🔻"
        except:
            pass
        if t.get('pairAddress'):
            return f"{t['emoji']} *{t['display_name']}*: `${format_price(price)}` {ind}{fdv} ({chg})"
        return f"{t['emoji']} *{t['display_name']}*: `${format_price(price)}` {ind} ({chg}) 24h"

    sections = [
        "*WKC Watcher 👀*\n🚀Live Token Prices🚀\n",
        line("wiki-cat"), "──────────────────",
        "*🎖 Commty Watchlist*\n", *
        (line(k)
         for k in [
             "the-kingdom-coin",
             "ocicat",
             "crepe",
             "defi-tiger",
             "watter-rabbit",
             "phoenix",
             "yukan",
             "zedek",
             "the-word-token",
             "btc-dragon",
             "bnbtiger"]),
        "──────────────────", "*🏅 Major Coins*\n", *
        (line(k)
         for k in ["bitcoin", "ethereum", "ripple", "binancecoin", "solana"]),
        "",
        "🧵 Follow along!"
    ]
    return "\n".join(sections)


async def send_to_channel(msg, buttons):
    async with httpx.AsyncClient() as c:
        await c.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "Markdown",
                  "reply_markup": {"inline_keyboard": buttons}}
        )
