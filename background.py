import asyncio
import traceback
import httpx
from utils import TELEGRAM_API_URL, format_price, get_token_info_dexscreener, CHANNEL_ID

WKC_KEY = "wiki-cat"
ALERT_THRESHOLD_PCT = 0.5
POLL_INTERVAL_SEC = 30

_last_alert_price = None


async def start_price_checker():
    global _last_alert_price
    while True:
        try:
            data = await get_token_info_dexscreener(WKC_KEY)
            price = data.get("raw_price", 0)
            if price > 0:
                if _last_alert_price is None:
                    _last_alert_price = price
                else:
                    change_pct = (price - _last_alert_price) / _last_alert_price * 100
                    if abs(change_pct) >= ALERT_THRESHOLD_PCT:
                        await send_price_alert(data, change_pct)
                        _last_alert_price = price
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(POLL_INTERVAL_SEC)


async def send_price_alert(data, change_pct):
    direction = "🚀" if change_pct > 0 else "🔻"
    sign = "+" if change_pct > 0 else ""
    msg = (
        f"{direction} *WKC Price Alert*\n\n"
        f"👑 Price: `${data['price']}` ({sign}{change_pct:.2f}%)\n"
        f"📉 24h Change: {data['chg_24']}\n"
        f"📊 Market Cap: `${data['market_cap']}`\n"
        f"💧 Liquidity: `${data['liquidity']}`\n"
        f"📈 Vol 24h: `${data['vol_24']}`\n\n"
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
