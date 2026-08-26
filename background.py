import asyncio
import traceback
import httpx
from utils import TELEGRAM_API_URL, format_price, get_price_with_change, CHANNEL_ID

WKC_KEY = "wiki-cat"
ALERT_THRESHOLD_PCT = 0.5

_last_alert_price = None


async def start_price_checker():
    global _last_alert_price
    while True:
        try:
            data = await get_price_with_change(WKC_KEY)
            price = data.get("raw_price", 0)
            if price > 0:
                if _last_alert_price is None:
                    _last_alert_price = price
                else:
                    change_pct = (price - _last_alert_price) / _last_alert_price * 100
                    if abs(change_pct) >= ALERT_THRESHOLD_PCT:
                        await send_price_alert(price, change_pct)
                        _last_alert_price = price
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(120)


async def send_price_alert(price, change_pct):
    direction = "🚀" if change_pct > 0 else "🔻"
    sign = "+" if change_pct > 0 else ""
    msg = (
        f"{direction} *WKC Price Alert*\n\n"
        f"👑 *WKC*: `${format_price(price)}` ({sign}{change_pct:.2f}%)\n\n"
        f"🔗 TG: @kodOlamWkcWatcher"
    )
    buttons = [
        [{"text": "Creator on X", "url": "https://x.com/codeolam"}],
        [{"text": "WikiCat on X", "url": "https://x.com/wikicatcoin"}],
        [{"text": "🤖 Bot Playground", "url": "https://t.me/kodOlam_bot"}],
    ]
    await send_to_channel(msg, buttons)


async def send_to_channel(msg, buttons):
    async with httpx.AsyncClient() as c:
        await c.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "Markdown",
                  "reply_markup": {"inline_keyboard": buttons}}
        )
