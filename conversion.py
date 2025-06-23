import re
from utils import TOKENS, get_price_coinlore, format_price, send_message

# Pattern for matching inputs like "10 wkc" or "$5"
AMOUNT_PATTERN = re.compile(r"^\s*(\$?)([\d.,eE+-]+)\s*([a-zA-Z-_]*)\s*$")


async def handle_price_it_flow(chat_id, message_text):
    match = AMOUNT_PATTERN.match(message_text or "")
    if not match:
        return await send_message(chat_id, "❌ Invalid format. Try `10 wkc` or `$5`.")

    is_usd = match.group(1) == "$"
    amount_str = match.group(2)
    token_input = match.group(3).lower()

    try:
        amount = float(amount_str.replace(",", ""))
    except ValueError:
        return await send_message(chat_id, "❌ Invalid number. Please try again.")

    # USD → Token
    if is_usd:
        conversions = []
        for key, token in TOKENS.items():
            price = await get_price_coinlore(key)
            try:
                price_float = float(price)
                tokens = amount / price_float
                conversions.append(
                    f"{token['emoji']} {token['display_name']}: `{tokens:,.0f}`")
            except:
                continue
        return await send_message(chat_id, f"*What {amount} can buy:*\n" + "\n".join(conversions))

    # Token → USD
    symbol_map = {v["display_name"].lower(): k for k, v in TOKENS.items()}
    token_id = symbol_map.get(token_input)
    if not token_id:
        return await send_message(chat_id, "❌ Unknown token symbol.")

    price = await get_price_coinlore(token_id)
    try:
        total = float(price) * amount
        await send_message(chat_id,
                           f"{TOKENS[token_id]['emoji']} *{amount:,.0f} {TOKENS[token_id]['display_name']}* is worth:\n`${format_price(total)}`"
                           )
    except Exception as e:
        await send_message(chat_id, "⚠️ Could not calculate at the moment.")
