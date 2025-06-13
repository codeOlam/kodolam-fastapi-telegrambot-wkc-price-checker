import asyncio
from utils import format_price, get_token_price, TOKENS, TELEGRAM_API_URL
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


# import asyncio
# from utils import format_price, get_token_price, TOKENS, TELEGRAM_API_URL
# import httpx

# CHANNEL_CHAT_ID = "@kodOlamWkcWatcher"
# price_cache = {}


# def build_price_message(prices):
#     lines = ["🚀 *Live Token Prices* 🚀\n"]

#     # WKC in special block
#     wkc_id = "wiki-cat"
#     if wkc_id in prices:
#         wkc = TOKENS[wkc_id]
#         lines.append(
#             f"{wkc['emoji']} *{wkc['display_name']}*: `${prices[wkc_id]}`")
#         lines.append("───────────────────")

#     for token_id, data in TOKENS.items():
#         if token_id == wkc_id:
#             continue
#         price = prices.get(token_id)
#         if price:
#             lines.append(
#                 f"{data['emoji']} *{data['display_name']}*: `${price}`")

#     lines.append("───────────────────")
#     lines.append("🧵 *Follow:*")
#     lines.append("• [Bot Creator on X](https://x.com/codeolam)")
#     lines.append("• [wikicatcoin on X](https://x.com/wikicatcoin)")
#     lines.append("• [More market insights](https://t.me/kodOlam_bot)")

#     print(f'message: {"\n".join(lines)}')
#     return "\n".join(lines)


# async def start_price_checker():
#     while True:
#         updated = False
#         new_prices = {}

#         for token_id in TOKENS:
#             price = await get_token_price(token_id)
#             if price is not None:
#                 formatted = format_price(price)
#                 new_prices[token_id] = formatted
#                 if price_cache.get(token_id) != formatted:
#                     updated = True

#         if updated:
#             price_cache.update(new_prices)
#             message = build_price_message(price_cache)
#             await send_to_channel(message)

#         await asyncio.sleep(10)


# async def send_to_channel(text):
#     async with httpx.AsyncClient() as client:
#         await client.post(
#             f"{TELEGRAM_API_URL}/sendMessage",
#             json={"chat_id": CHANNEL_CHAT_ID,
#                   "text": text, "parse_mode": "Markdown"}
#         )


# import asyncio
# import httpx
# from utils import format_price, get_token_price, TOKENS, get_chat_ids, TELEGRAM_API_URL, send_message

# price_cache = {}


# async def start_price_checker():
#     while True:
#         updated = False
#         new_prices = {}

#         # Get all token prices and compare with cache
#         for token_id in TOKENS:
#             price = await get_token_price(token_id)
#             if price is not None:
#                 formatted_price = format_price(price)
#                 new_prices[token_id] = formatted_price

#                 # If price changed from cached, mark update
#                 if price_cache.get(token_id) != formatted_price:
#                     updated = True

#         if updated:
#             # Update the cache
#             price_cache.update(new_prices)

#             # Build message with ALL current prices
#             message = build_price_message(price_cache)

#             # Send to all registered chat IDs
#             chat_ids = get_chat_ids()
#             for chat_id in chat_ids:
#                 await send_message(chat_id, message)

#         await asyncio.sleep(10)


# async def broadcast_prices(prices):
#     chat_ids = get_chat_ids()
#     message = build_price_message(prices)

#     async with httpx.AsyncClient() as client:
#         for chat_id in chat_ids:
#             await client.post(
#                 f"{TELEGRAM_API_URL}/sendMessage",
#                 json={
#                     "chat_id": chat_id,
#                     "text": message,
#                     "parse_mode": "Markdown"
#                 }
#             )


# def build_price_message(prices):
#     lines = ["🚀 *Live Token Prices* 🚀\n"]

#     # Highlight Wiki-Cat (WKC) in a special section
#     wkc_id = "wiki-cat"
#     if wkc_id in prices:
#         wkc = TOKENS[wkc_id]
#         wkc_emoji = wkc.get("emoji", "")
#         wkc_name = wkc.get("display_name", "Wiki Cat")
#         wkc_price = prices[wkc_id]
#         lines.append(f"{wkc_emoji} *{wkc_name}*: `${wkc_price}`")
#         lines.append("────────────────────")

#     # Add other tokens
#     for token_id, data in TOKENS.items():
#         if token_id == wkc_id:
#             continue  # Already printed
#         name = data.get("display_name", token_id.title())
#         emoji = data.get("emoji", "")
#         price = prices.get(token_id)
#         if price is not None:
#             lines.append(f"{emoji} *{name}*: `${price}`")

#     return "\n".join(lines)
