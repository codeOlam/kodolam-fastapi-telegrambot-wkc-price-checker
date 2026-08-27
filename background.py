import asyncio
import time
import traceback
import httpx
from utils import (
    TELEGRAM_API_URL, format_price, get_token_info_dexscreener, get_holder_count,
    get_token_security_stats, load_digest_state, save_digest_state,
    get_latest_block, get_wkc_swaps, get_whale_threshold, load_whale_state, save_whale_state,
    CHANNEL_ID, CHANNEL_HANDLE
)

WKC_KEY = "wiki-cat"
ALERT_THRESHOLD_PCT = 0.2
POLL_INTERVAL_SEC = 15
HOURLY_REPORT_INTERVAL_SEC = 60 * 60
DIGEST_CHECK_INTERVAL_SEC = 15 * 60
DAILY_PERIOD_SEC = 24 * 60 * 60
WEEKLY_PERIOD_SEC = 7 * 24 * 60 * 60
WHALE_CHECK_INTERVAL_SEC = 45

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


async def start_hourly_pressure_report():
    while True:
        await asyncio.sleep(HOURLY_REPORT_INTERVAL_SEC)
        try:
            data = await get_token_info_dexscreener(WKC_KEY)
            await send_hourly_pressure_report(data)
        except Exception:
            traceback.print_exc()


async def send_price_alert(data):
    try:
        chg24_val = float(
            str(data.get('chg_24', '0')).replace('%', '').strip())
    except (TypeError, ValueError):
        chg24_val = 0
    direction = "🚀" if chg24_val >= 0 else "🔻"

    holders = await get_holder_count(data.get('contract'))
    holders_line = f"👥 Holders: `{holders:,}`\n" if holders else ""

    msg = (
        f"👑 Price: `${data['price']}` {direction}\n"
        f"📉 24h Change: {data['chg_24']}\n"
        f"📊 Market Cap: `${data['market_cap']}`\n"
        f"{holders_line}"
        f"📈 Vol 24h: `${data['vol_24']}`\n\n"
        f"🔗 TG: {CHANNEL_HANDLE}"
    )
    buttons = [
        [{"text": "🤖 Bot Playground", "url": "https://t.me/kodOlam_bot"}],
    ]
    await send_to_channel(msg, buttons)


async def send_hourly_pressure_report(data):
    buys_h1 = data.get('buys_h1', 0)
    sells_h1 = data.get('sells_h1', 0)
    vol_h1 = data.get('vol_h1', 0)
    total = buys_h1 + sells_h1
    buy_pct = (buys_h1 / total * 100) if total else 0

    msg = (
        f"⏱ *WKC Hourly Pulse*\n\n"
        f"🟢 Buys: `{buys_h1}` | 🔴 Sells: `{sells_h1}`\n"
        f"⚖️ Buy Pressure: `{buy_pct:.0f}%`\n"
        f"📈 Volume (1h): `${format_price(vol_h1, compact=True)}`\n\n"
        f"🔗 TG: {CHANNEL_HANDLE}"
    )
    buttons = [
        [{"text": "🤖 Bot Playground", "url": "https://t.me/kodOlam_bot"}],
    ]
    await send_to_channel(msg, buttons)


async def start_digest_checker():
    while True:
        try:
            await check_and_send_digest("daily", DAILY_PERIOD_SEC, "📅 *WKC Daily Recap*")
            await check_and_send_digest("weekly", WEEKLY_PERIOD_SEC, "🗓 *WKC Weekly Recap*")
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(DIGEST_CHECK_INTERVAL_SEC)


async def check_and_send_digest(period_key, period_sec, title):
    state = load_digest_state()
    baseline = state.get(period_key)
    now = time.time()

    if baseline is None:
        await _reset_digest_baseline(state, period_key, now)
        return

    if now - baseline["ts"] < period_sec:
        return

    data = await get_token_info_dexscreener(WKC_KEY)
    stats = await get_token_security_stats(data.get('contract')) or {}
    await send_digest(title, baseline, data, stats)
    await _reset_digest_baseline(state, period_key, now, data, stats)


async def _reset_digest_baseline(state, period_key, now, data=None, stats=None):
    if data is None:
        data = await get_token_info_dexscreener(WKC_KEY)
    if stats is None:
        stats = await get_token_security_stats(data.get('contract')) or {}
    state[period_key] = {
        "price": data.get("raw_price", 0),
        "market_cap": data.get("raw_market_cap", 0),
        "holders": stats.get("holder_count") or 0,
        "burned": stats.get("burned_balance") or 0,
        "ts": now,
    }
    save_digest_state(state)


async def send_digest(title, baseline, data, stats):
    def pct_change(old, new):
        return None if not old else (new - old) / old * 100

    def fmt_pct(v):
        if v is None:
            return "N/A"
        return f"{'+' if v >= 0 else ''}{v:.2f}%"

    price_now = data.get("raw_price", 0)
    mc_now = data.get("raw_market_cap", 0)
    holders_now = stats.get("holder_count") or 0
    burned_now = stats.get("burned_balance") or 0

    price_chg = pct_change(baseline["price"], price_now)
    mc_chg = pct_change(baseline["market_cap"], mc_now)
    holders_chg = holders_now - baseline.get("holders", 0)
    holders_chg_str = f"{'+' if holders_chg >= 0 else ''}{holders_chg:,}"
    burned_chg = burned_now - baseline.get("burned", 0)

    msg = (
        f"{title}\n\n"
        f"👑 Price: `${format_price(price_now)}` ({fmt_pct(price_chg)})\n"
        f"📊 Market Cap: `${format_price(mc_now, compact=True)}` ({fmt_pct(mc_chg)})\n"
        f"👥 Holders: `{holders_now:,}` ({holders_chg_str})\n"
        f"🔥 Burned: `{format_price(burned_now, compact=True)} WKC` (+{format_price(burned_chg, compact=True)})\n\n"
        f"🔗 TG: {CHANNEL_HANDLE}"
    )
    buttons = [
        [{"text": "🤖 Bot Playground", "url": "https://t.me/kodOlam_bot"}],
    ]
    await send_to_channel(msg, buttons)


async def start_whale_watcher():
    state = load_whale_state()
    if "last_block" not in state:
        try:
            state["last_block"] = await get_latest_block()
            save_whale_state(state)
        except Exception:
            traceback.print_exc()

    while True:
        await asyncio.sleep(WHALE_CHECK_INTERVAL_SEC)
        try:
            state = load_whale_state()
            last_block = state.get("last_block")
            latest = await get_latest_block()

            if last_block is None:
                state["last_block"] = latest
                save_whale_state(state)
                continue
            if latest <= last_block:
                continue

            swaps = await get_wkc_swaps(last_block + 1, latest)
            if swaps:
                data = await get_token_info_dexscreener(WKC_KEY)
                wkc_price = data.get("raw_price", 0)
                threshold = get_whale_threshold()
                for s in swaps:
                    usd_value = s["wkc_amount"] * wkc_price
                    if usd_value >= threshold:
                        await send_whale_alert(s, usd_value)

            state["last_block"] = latest
            save_whale_state(state)
        except Exception:
            traceback.print_exc()


async def send_whale_alert(swap, usd_value):
    emoji = "🟢🐋" if swap["side"] == "buy" else "🔴🐋"
    verb = "Buy" if swap["side"] == "buy" else "Sell"
    msg = (
        f"{emoji} *WKC Whale {verb}*\n\n"
        f"💰 `${usd_value:,.0f}`\n"
        f"👑 `{swap['wkc_amount']:,.0f} WKC`\n"
        f"💎 `{swap['bnb_amount']:.4f} BNB`\n"
        f"🔗 [View Tx](https://bscscan.com/tx/{swap['tx_hash']})\n\n"
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
