import re
from utils import TOKENS, get_price_dexscreener, get_price_coinlore, format_price, get_price_with_change, send_message

AMOUNT_PATTERN = re.compile(r"^\s*(\$?)([\d.,eE+-]+)\s*([A-Za-z0-9_-]*)\s*$")


async def handle_price_it_flow(chat_id, text):
    m = AMOUNT_PATTERN.match(text or "")
    if not m:
        return await send_message(chat_id, "🤔 Dre didn't catch that. Try something like `10 wkc` or `$5`.")
    is_usd, amt_s, sym = m.group(1) == "$", m.group(2), m.group(3).lower()
    try:
        amt = float(amt_s.replace(",", ""))
    except:
        return await send_message(chat_id, "🚫 Hmmm… Dre says that number doesn't look right.")
    if is_usd:
        lines = []
        for k, tok in TOKENS.items():
            price_data = await get_price_with_change(k)
            price = price_data.get("price", "N/A")
            # chg = price_data.get("chg_24", "—")
            # price = await (get_price_dexscreener(k) if tok.get("contract") else get_price_coinlore(k))
            try:
                n = amt/float(price)
                lines.append(
                    f"{tok['emoji']} {tok['display_name']}: `{n:,.0f}`")
            except:
                continue
        return await send_message(chat_id, "*Dre says you can get this for $%s:*\n%s" % (amt, "\n".join(lines)))
    cmap = {v["display_name"].lower(): k for k, v in TOKENS.items()}
    token = cmap.get(sym)
    if not token:
        return await send_message(chat_id, "🤷🏾‍♂️ Dre hasn't heard of that token yet.")
    price_data = await get_price_with_change(token)
    price = price_data.get("price", "N/A")
    # price = await (get_price_dexscreener(token) if TOKENS[token].get("contract") else get_price_coinlore(token))
    try:
        tot = float(price)*amt
        return await send_message(chat_id, f"💵 Dre ran the numbers: {TOKENS[token]['emoji']} *{amt:,.0f} {TOKENS[token]['display_name']}* ≈ `$ {format_price(tot)}`")
    except:
        return await send_message(chat_id, "🛠️ Dre hit a snag crunching those numbers.")


# import re
# from utils import TOKENS, get_price_coinlore, format_price, send_message

# # Pattern for matching inputs like "10 wkc" or "$5"
# AMOUNT_PATTERN = re.compile(r"^\s*(\$?)([\d.,eE+-]+)\s*([a-zA-Z-_]*)\s*$")


# async def handle_price_it_flow(chat_id, message_text):
#     match = AMOUNT_PATTERN.match(message_text or "")
#     if not match:
#         return await send_message(chat_id, "❌ Invalid format. Try `10 wkc` or `$5`.")

#     is_usd = match.group(1) == "$"
#     amount_str = match.group(2)
#     token_input = match.group(3).lower()

#     try:
#         amount = float(amount_str.replace(",", ""))
#     except ValueError:
#         return await send_message(chat_id, "❌ Invalid number. Please try again.")

#     # USD → Token
#     if is_usd:
#         conversions = []
#         for key, token in TOKENS.items():
#             price = await get_price_coinlore(key)
#             try:
#                 price_float = float(price)
#                 tokens = amount / price_float
#                 conversions.append(
#                     f"{token['emoji']} {token['display_name']}: `{tokens:,.0f}`")
#             except:
#                 continue
#         return await send_message(chat_id, f"*What {amount} can buy:*\n" + "\n".join(conversions))

#     # Token → USD
#     symbol_map = {v["display_name"].lower(): k for k, v in TOKENS.items()}
#     token_id = symbol_map.get(token_input)
#     if not token_id:
#         return await send_message(chat_id, "❌ Unknown token symbol.")

#     price = await get_price_coinlore(token_id)
#     try:
#         total = float(price) * amount
#         await send_message(chat_id,
#                            f"{TOKENS[token_id]['emoji']} *{amount:,.0f} {TOKENS[token_id]['display_name']}* is worth:\n`${format_price(total)}`"
#                            )
#     except Exception as e:
#         await send_message(chat_id, "⚠️ Could not calculate at the moment.")
