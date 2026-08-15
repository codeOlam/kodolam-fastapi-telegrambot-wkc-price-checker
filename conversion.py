import re
import traceback
from utils import TOKENS, format_price, get_price_with_change, parse_price, send_message, send_message_with_buttons

AMOUNT_PATTERN = re.compile(r"^\s*(\$?)([\d.,eE+-]+)\s*([A-Za-z0-9_-]*)\s*$")


async def handle_price_it_flow(chat_id, text):
    m = AMOUNT_PATTERN.match(text or "")
    if not m:
        return await send_message(chat_id, "🤔 Dre didn't catch that. Try something like `10 wkc` or `$5`.")

    is_usd, amt_s, sym = m.group(1) == "$", m.group(2), m.group(3).lower()

    try:
        amt = float(amt_s.replace(",", ""))
    except:
        return await send_message(chat_id, "🧐 Hmmm… Dre says that number doesn't look right.")

    # USD => Token
    if is_usd:
        lines = []
        for k, tok in TOKENS.items():
            price_data = await get_price_with_change(k)
            price = price_data.get("raw_price", 0)
            if price > 0:
                try:
                    n = amt / price
                    formatted_n = f"{n:,.0f}" if n >= 1 else f"{n:.8f}"
                    lines.append(
                        f"{tok['emoji']} {tok['display_name']}: `{formatted_n}`")
                except:
                    traceback.print_exc()
                    continue
        return await send_message(chat_id, f"* Dre says you can get this for ${amt}:*\n\n" + "\n".join(lines))

    # Token => USD
    cmap = {v["display_name"].lower(): k for k, v in TOKENS.items()}
    token = cmap.get(sym)
    if not token:
        return await send_message(chat_id, "🤷🏾‍♂️ Dre hasn't heard of that token yet.")
    try:
        price_data = await get_price_with_change(token)
        price = price_data.get("raw_price", 0)
        if price > 0:
            tot = price * amt
            return await send_message(
                chat_id,
                f"*😎 Dre ran the numbers:*\n\n {TOKENS[token]['emoji']} *{amt:,.0f} {TOKENS[token]['display_name']}* ≈ `$ {format_price(tot)}`"
            )
    except:
        traceback.print_exc()
        return await send_message(chat_id, "🛠️ Dre hit a snag crunching those numbers.")


async def start_dre_flow(chat_id):
    return await send_message_with_buttons(
        chat_id,
        "🧮 Dre Price It — What do you want to convert?",
        [
            [
                {"text": "💵 USD → Tokens", "callback_data": "dre_usd_to_token"},
                {"text": "🪙 Token → USD", "callback_data": "dre_token_to_usd"}
            ]
        ]
    )
