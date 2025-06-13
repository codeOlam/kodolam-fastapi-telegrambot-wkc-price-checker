import asyncio
from utils import get_token_price, TOKENS, TELEGRAM_API_URL
import httpx


CHANNEL_CHAT_ID = "@kodOlamWkcWatcher"
price_cache = {}


def build_price_message(prices):
    lines = ["🚀 *Live Token Prices* 🚀\n"]
    wkc_id = "wiki-cat"
    if wkc_id in prices:
        wkc = TOKENS[wkc_id]
        lines.append(
            f"{wkc['emoji']} *{wkc['display_name']}*: `${prices[wkc_id]}`")
        lines.append("──────────────────")

    for token_id, data in TOKENS.items():
        if token_id == wkc_id:
            continue
        price = prices.get(token_id, "N/A")
        lines.append(f"{data['emoji']} *{data['display_name']}*: `${price}`")

    lines.append("──────────────────")
    lines.append("🧵 *Follow:*")
    lines.append("• [Bot Creator on X](https://x.com/codeolam)")
    lines.append("• [wikicatcoin on X](https://x.com/wikicatcoin)")
    lines.append("• [More market insights](https://t.me/kodOlam_bot)")

    return "\n".join(lines)


async def start_price_checker():
    print('start_price_checker is called')
    while True:
        updated = False
        new_prices = {}

        for token_id in TOKENS:
            price = await get_token_price(token_id)
            formatted = price or "N/A"
            new_prices[token_id] = formatted
            if price_cache.get(token_id) != formatted:
                updated = True

        if updated:
            price_cache.update(new_prices)
            message = build_price_message(price_cache)
            await send_to_channel(message)

        await asyncio.sleep(5)  # 30 seconds is a fair interval


async def send_to_channel(text):
    print('sending message to channel!')
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": CHANNEL_CHAT_ID,
                  "text": text, "parse_mode": "Markdown"}
        )
