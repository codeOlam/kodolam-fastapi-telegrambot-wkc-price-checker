import asyncio
from utils import TELEGRAM_API_URL, format_price, price_cache, fetch_all_coinlore_prices, TOKENS, CHANNEL_ID
import httpx
import os


async def start_price_checker():
    print('[start_price_checker] is being called!')
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
        print(f"[Background Error] {type(e).__name__}: {e}")
        raise  # Let the worker catch and log it too


def build_message(prices):
    l = ["*WKC Watcher 👀*\n🚀Live Token Prices🚀\n"]
    w = "wiki-cat"
    l.append(
        f"{TOKENS[w]['emoji']} *{TOKENS[w]['display_name']}*: `${format_price(prices[w]) or prices[w]}`")
    l.append("──────────────────")
    for k, v in prices.items():
        if k == w:
            continue
        l.append(
            f"{TOKENS[k]['emoji']} *{TOKENS[k]['display_name']}*: `\t${format_price(v) or v}`")
    l.append("──────────────────")
    l += [
        "🧵 *Follow:*",
        "🔗 [Creator on X](https://x.com/codeolam)",
        "🔗 [WikiCat on X](https://x.com/wikicatcoin)",
    ]

    l.append("──────────────────")
    l.append("\n🤖 [More market insights](https://t.me/kodOlam_bot)")

    return "\n".join(l)


async def send_to_channel(msg):
    print('[send_to_channel] here now')
    async with httpx.AsyncClient() as c:
        await c.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "Markdown"}
        )
