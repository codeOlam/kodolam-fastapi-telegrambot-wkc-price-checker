from utils import (
    CHANNEL_HANDLE, TOKENS, format_change, get_token_info, get_token_info_dexscreener,
    send_message
)


async def handle_token_info(chat_id, key):
    token = TOKENS[key]
    if token.get("pairAddress"):
        d = await get_token_info_dexscreener(key)
        return await send_message(chat_id, "\n".join([
            f"*{token['display_name']} Info*\n",
            f"💡 Name: {d['name']}",
            f"💰 Price: ${d['price']} | 📉 24h: {format_change(d['chg_24'], True)}",
            f"📊 MCap: ${d['market_cap']} | 📊 FDV: ${d['fdv']}",
            f"💧 Liq: ${d['liquidity']}",
            f"📈 Vol 24h: ${d['vol_24']} | 🔢 Sup: {d['supply']}",
            f"🔁 Txns 24h: {d['txns']}",
            f"🧾 Contract: `{d['contract']}`",
            f"📅 {d['queried_at']}",
            f"\n🔗 TG: {CHANNEL_HANDLE}"
        ]))
    else:
        d = await get_token_info(key)
        return await send_message(chat_id, "\n".join([
            f"*{token['display_name']} Info*\n",
            f"💡 Name: {d['name']}",
            f"💰 Price: ${d['price']}",
            f"📉 Chg 24h: {format_change(d['chg_24'], True)}",
            f"📊 MCap: ${d['market_cap']}",
            f"📈 Vol 24h: ${d['vol_24']}",
            f"🔢 Sup: {d['supply']}",
            f"📅 {d['queried_at']}",
            f"\n🔗 TG: {CHANNEL_HANDLE}"
        ]))
