import asyncio
import traceback
import httpx
import os
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from utils import (
    format_change, get_price_with_change, register_chat_id, TOKENS,
    get_token_info_dexscreener, get_token_info,
    get_fear_greed, get_dominance,
    send_message, send_message_with_buttons, TELEGRAM_API_URL
)
from background import build_message, start_price_checker
from conversion import AMOUNT_PATTERN, handle_price_it_flow, start_dre_flow
from marketOracle import (
    EmjayState, start_emjay_flow, reset_emjay
)

BOT = os.getenv("TELEGRAM_BOT_TOKEN")


async def set_commands():
    cmds = [
        {"command": "price", "description": "Show all prices"},
        {"command": "dre_price_it",
            "description": "Dre token ⇄ USD (button flow)"},
        {"command": "emjay_market_oracle",
            "description": "Emjay Market Oracle (simulate gains)"}
    ]
    cmds += [{"command": f"info_{k.replace('-', '_')}",
              "description": f"{TOKENS[k]['display_name']} info"} for k in TOKENS]
    cmds += [
        {"command": "info_fear_greed", "description": "Fear & Greed"},
        {"command": "info_dominance", "description": "Dominance"}
    ]
    async with httpx.AsyncClient() as c:
        await c.post(f"{TELEGRAM_API_URL}/setMyCommands", json={"commands": cmds})


async def set_webhook():
    webhook_url = f"https://kodolam-bot-api.onrender.com/webhook"
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API_URL}/setWebhook", data={"url": webhook_url})


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(start_price_checker())
    await set_webhook()
    await set_commands()
    yield

app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(req: Request):
    b = await req.json()
    cid = None

    if 'callback_query' in b:
        cb = b['callback_query']
        cid = cb['message']['chat']['id']
        register_chat_id(cid)
        data = cb['data']

        # Dre button flows
        if data == 'dre_open':
            return await send_message_with_buttons(
                cid,
                "🔁 *Dre Options*",
                [[{"text": "💵 Convert $ → Token", "callback_data": "dre_usd_to_token"}],
                 [{"text": "💰 Convert Token → $", "callback_data": "dre_token_to_usd"}]]
            )
        elif data in ('dre_usd_to_token', 'dre_token_to_usd'):
            return await start_dre_flow(cid, data)

        # Emjay button flows
        if data == 'emjay_open':
            return await send_message_with_buttons(
                cid,
                "📈 *Emjay Market Oracle*",
                [[{"text": "🎯 Simulate Gains", "callback_data": "emjay_start"}],
                 [{"text": "♻️ Reset Oracle", "callback_data": "emjay_reset"}]]
            )
        elif data in ('emjay_start',) or EmjayState.in_flow(cid):
            return await start_emjay_flow(cid, data)
        elif data == 'emjay_reset':
            return await reset_emjay(cid)

    elif 'message' in b:
        t = b['message'].get('text', '')
        cid = b['message']['chat']['id']
        register_chat_id(cid)

        if t == '/price':
            prices = {k: await get_price_with_change(k) for k in TOKENS}
            return await send_message(cid, build_message(prices))

        if t == '/dre_price_it':
            return await send_message_with_buttons(
                cid,
                "🔁 Tap an option for Dre:",
                [[{"text": "💵 Convert $ → Token", "callback_data": "dre_usd_to_token"}],
                 [{"text": "💰 Convert Token → $", "callback_data": "dre_token_to_usd"}]]
            )

        if t == '/emjay_market_oracle':
            return await send_message_with_buttons(
                cid,
                "📈 Tap an Emjay option:",
                [[{"text": "🎯 Simulate Gains", "callback_data": "emjay_start"}],
                 [{"text": "♻️ Reset Oracle", "callback_data": "emjay_reset"}]]
            )

        if t.startswith('/info_'):
            cmd = t.split('_', 1)[1].replace('_', '-')
            if cmd in TOKENS:
                if TOKENS[cmd].get('contract'):
                    d = await get_token_info_dexscreener(cmd)
                    return await send_message(cid, "\n".join([
                        f"*{TOKENS[cmd]['display_name']} Info*",
                        f"💡 Name: {d['name']}",
                        f"💰 Price: ${d['price']} | 📉 24h: {format_change(d['chg_24'])}",
                        f"📊 MCap: ${d['market_cap']} | 💧 Liq: ${d['liquidity']}",
                        f"📈 Vol 24h: ${d['vol_24']} | 🔢 Sup: {d['supply']}",
                        f"🔁 Txns 24h: {d['txns']}",
                        f"🚀 Lunched: {d['created_at']}",
                        f"🧾 Contract: `{d['contract']}`",
                        "\n@kodOlamWkcWatcher"
                    ]))
                else:
                    d = await get_token_info(cmd)
                    return await send_message(cid, "\n".join([
                        f"*{TOKENS[cmd]['display_name']} Info*",
                        f"💡 Name: {d['name']}",
                        f"💰 Price: ${d['price']} | 📉 24h: {format_change(d['chg_24'])}",
                        f"📊 MCap: ${d['market_cap']}",
                        f"📈 Vol 24h: ${d['vol_24']}",
                        f"🔢 Sup: {d['supply']}",
                        "\n@kodOlamWkcWatcher"
                    ]))

        if t == '/info_fear_greed':
            return await send_message(cid, f"🙀🤑 Fear & Greed\n{await get_fear_greed()}\n\n@kodOlamWkcWatcher")
        if t == '/info_dominance':
            return await send_message(cid, f"💹 Market Dominance\n{await get_dominance()}\n\n@kodOlamWkcWatcher")

    # fallback
    try:
        if AMOUNT_PATTERN.match(b.get('message', {}).get('text', '') or ""):
            return await handle_price_it_flow(cid, b['message']['text'])
    except Exception:
        traceback.print_exc()
        return await send_message(cid, "🤯 Dre broke his calculator")

    # Default
    await send_message(
        cid,
        "👋 Try `/price`, `/dre_price_it`, or `/emjay_market_oracle` to begin!"
    )
    return {"ok": True}


@app.api_route("/ping", methods=["GET", "HEAD"])
async def ping(): return {"status": "ok"}


# import asyncio
# import traceback
# import httpx
# import os
# from fastapi import FastAPI, Request
# from contextlib import asynccontextmanager
# from utils import (
#     format_change, get_price_with_change, register_chat_id, TOKENS,
#     get_token_info_dexscreener, get_token_info,
#     get_fear_greed, get_dominance, send_message, TELEGRAM_API_URL
# )
# from background import build_message, start_price_checker
# from conversion import AMOUNT_PATTERN, handle_price_it_flow

# BOT = os.getenv("TELEGRAM_BOT_TOKEN")


# async def set_commands():
#     cmds = [
#         {"command": "price", "description": "Show all prices"},
#         {"command": "dre_price_it",
#             "description": "Dre will to advice you on token ⇄ USD"},
#     ]
#     cmds += [{"command": f"info_{k.replace('-', '_')}",
#               "description": f"{TOKENS[k]['display_name']} info"} for k in TOKENS]
#     cmds += [{"command": "info_fear_greed", "description": "Fear & Greed"},
#              {"command": "info_dominance", "description": "Dominance"}]
#     async with httpx.AsyncClient() as c:
#         await c.post(f"{TELEGRAM_API_URL}/setMyCommands", json={"commands": cmds})


# async def set_webhook():
#     webhook_url = f"https://kodolam-bot-api.onrender.com/webhook"
#     async with httpx.AsyncClient() as client:
#         await client.post(
#             f"{TELEGRAM_API_URL}/setWebhook",
#             data={"url": webhook_url}
#         )


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     asyncio.create_task(start_price_checker())
#     await set_webhook()
#     await set_commands()
#     yield

# app = FastAPI(lifespan=lifespan)


# @app.post("/webhook")
# async def webhook(req: Request):
#     b = await req.json()
#     t = b.get("message", {}).get("text", "")
#     cid = b.get("message", {}).get("chat", {}).get("id")

#     if cid:
#         register_chat_id(cid)

#     if t == "/price":
#         prices = {}
#         for k in TOKENS:
#             prices[k] = await get_price_with_change(k)
#         return await send_message(cid, build_message(prices))

#     elif t == "/dre_price_it":
#         return await send_message(
#             cid,
#             "🚀 Yo yo! Dre in the house. Tell me what you're stackin' — `1000000000 wkc` or maybe `$20`? Let me flip the math for ya 📊💰"
#         )

#     elif t.startswith("/info_"):
#         cmd = t.split("_", 1)[1].replace("_", "-")
#         if cmd in TOKENS:
#             if TOKENS[cmd].get("contract"):
#                 d = await get_token_info_dexscreener(cmd)
#                 return await send_message(cid, "\n".join([
#                     f"*{TOKENS[cmd]['display_name']} Info*\n",
#                     f"💡 Name: {d['name']}",
#                     f"💰 Price: ${d['price']} | 📉 24h: {format_change(d['chg_24'])}",
#                     f"📊 MCap: ${d['market_cap']} | 💧 Liq: ${d['liquidity']}",
#                     f"📈 Vol 24h: ${d['vol_24']} | 🔢 Sup: {d['supply']}",
#                     f"🔁 Txns 24h: {d['txns']}",
#                     f"🚀 Lunched: {d['created_at']}",
#                     f"🧾 Contract: `{d['contract']}`",
#                     f"\n@kodOlamWkcWatcher"
#                 ]))
#             else:
#                 d = await get_token_info(cmd)
#                 return await send_message(cid, "\n".join([
#                     f"*{TOKENS[cmd]['display_name']} Info*\n",
#                     f"💡 Name: {d['name']}",
#                     f"💰 Price: ${d['price']}",
#                     f"📉 Chg 24h: {format_change(d['chg_24'])}",
#                     f"📊 MCap: ${d['market_cap']}",
#                     f"📈 Vol 24h: ${d['vol_24']}",
#                     f"🔢 Sup: {d['supply']}",
#                     f"\n@kodOlamWkcWatcher"
#                 ]))
#         elif cmd == "fear-greed":
#             return await send_message(cid, f"🙀🤑 Fear & Greed\n {await get_fear_greed()}\n\n@kodOlamWkcWatcher")
#         elif cmd == "dominance":
#             return await send_message(cid, f"💹 Market Dominance\n {await get_dominance()}\n\n@kodOlamWkcWatcher")

#     try:
#         if AMOUNT_PATTERN.match(t or ""):
#             return await handle_price_it_flow(cid, t)
#     except Exception:
#         traceback.print_exc()
#         return await send_message(cid, "🤯 Dre broke his calculator")

#     # ➕ Default fallback if none of the above matched
#     await send_message(
#         cid,
#         "👋 Yo! kodOlam here. Try `/price`, `/dre_price_it`, or send Dre something like `1000000000 wkc`, `100 xrp` or `$5` and let Dre crunch the numbers. 🧠💰"
#     )
#     return {"ok": True}


# # this will work with uptimeroobot to kep render.com alive,
# # if you are using free tier else comment out
# @app.api_route("/ping", methods=["GET", "HEAD"])
# async def ping():
#     return {"status": "ok"}
