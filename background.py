import asyncio
import traceback
import httpx
from utils import TELEGRAM_API_URL, format_price, get_token_info_dexscreener, get_holder_count, CHANNEL_ID, CHANNEL_HANDLE

WKC_KEY = "wiki-cat"
ALERT_THRESHOLD_PCT = 0.2
POLL_INTERVAL_SEC = 15

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
                    change_pct = (price - _last_alert_price) / \
                        _last_alert_price * 100
                    if abs(change_pct) >= ALERT_THRESHOLD_PCT:
                        await send_price_alert(data)
                        _last_alert_price = price
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(POLL_INTERVAL_SEC)


async def send_price_alert(data):
    try:
        chg24_val = float(
            str(data.get('chg_24', '0')).replace('%', '').strip())
    except (TypeError, ValueError):
        chg24_val = 0
    direction = "🚀" if chg24_val >= 0 else "🔻"

    holders = await get_holder_count(data.get('contract'))
    holders_line = f"👥 Holders: `{holders:,}`\n" if holders else ""

    buys_h1 = data.get('buys_h1', 0)
    sells_h1 = data.get('sells_h1', 0)
    pressure_line = f"🟢 {buys_h1} buys / 🔴 {sells_h1} sells (1h)\n" if (buys_h1 or sells_h1) else ""

    msg = (
        f"👑 Price: `${data['price']}` {direction}\n"
        f"📉 24h Change: {data['chg_24']}\n"
        f"📊 Market Cap: `${data['market_cap']}`\n"
        f"{holders_line}"
        f"📈 Vol 24h: `${data['vol_24']}`\n"
        f"{pressure_line}\n"
        f"🔗 TG: {CHANNEL_HANDLE}"
    )
    buttons = [
        [{"text": "🤖 Bot Playground", "url": "https://t.me/kodOlam_bot"}],
    ]
    await send_to_channel(msg, buttons)


async def send_to_channel(msg, buttons):
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "Markdown",
                  "reply_markup": {"inline_keyboard": buttons}}
        )
        r.raise_for_status()
        body = r.json()
        if not body.get("ok"):
            raise RuntimeError(f"Telegram sendMessage failed: {body}")
