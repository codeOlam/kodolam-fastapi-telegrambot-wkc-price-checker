import asyncio
import httpx
import os
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from utils import (
    get_price_with_change, register_chat_id, TOKENS,
    get_price_dexscreener, get_price_coinlore,
    get_token_info_dexscreener, get_token_info,
    get_fear_greed, get_dominance,
    format_price, send_message, TELEGRAM_API_URL
)
from background import build_message, start_price_checker
from conversion import AMOUNT_PATTERN, handle_price_it_flow

BOT = os.getenv("TELEGRAM_BOT_TOKEN")


async def set_commands():
    cmds = [
        {"command": "price", "description": "Show all prices"},
        {"command": "Dre_price_it", "description": "Dre will to advice you on token ⇄ USD"}
    ]
    cmds += [{"command": f"info_{k.replace('-', '_')}",
              "description": f"{TOKENS[k]['display_name']} info"} for k in TOKENS]
    cmds += [{"command": "info_fear_greed", "description": "Fear & Greed"},
             {"command": "info_dominance", "description": "Dominance"}]
    async with httpx.AsyncClient() as c:
        await c.post(f"{TELEGRAM_API_URL}/setMyCommands", json={"commands": cmds})


async def set_webhook():
    url = f"https://{os.getenv('RENDER_SERVICE')}.onrender.com/webhook"
    async with httpx.AsyncClient() as c:
        await c.post(f"{TELEGRAM_API_URL}/setWebhook", data={"url": url})


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
    t = b.get("message", {}).get("text", "")
    cid = b.get("message", {}).get("chat", {}).get("id")
    if cid:
        register_chat_id(cid)

    resp = "👋 Use /price or /Dre_price_it"
    if t == "/price":
        prices = {}
        for k in TOKENS:
            prices[k] = await get_price_with_change(k)
            # prices[k] = await (get_price_dexscreener(k) if TOKENS[k].get("contract") else get_price_coinlore(k))
        resp = build_message(prices)
    elif t == "/Dre_price_it":
        return await send_message(cid, "🚀 Yo yo! Dre in the house. Tell me what you're stackin' — `10 wkc` or maybe `$20`? Let me flip the math for ya 📊💰"
                                  )
    elif AMOUNT_PATTERN.match(t or ""):
        return await handle_price_it_flow(cid, t)
    elif t.startswith("/info_"):
        cmd = t.split("_", 1)[1].replace("_", "-")
        if cmd in TOKENS:
            d = await (get_token_info_dexscreener(cmd) if TOKENS[cmd].get("contract") else get_token_info(cmd))
            resp = "\n".join([
                f"*{TOKENS[cmd]['display_name']} Info*",
                f"Price: ${d['price']}",
                f"Market Cap: ${d['market_cap']}",
                f"Vol 24h: ${d['vol_24']}",
                f"Change 24h: {d['chg_24']}",
                f"Supply: {d['supply']}",
                f"Contract: `{d['contract']}`",
                f"Note: {d['msg']}"
            ])
        elif cmd == "fear":
            resp = f"🙀🤑 Fear & Greed: {await get_fear_greed()}"
        elif cmd == "dominance":
            resp = f"💹 Market Dominance: {await get_dominance()}"
    await send_message(cid, resp)
    return {"ok": True}


@app.api_route("/ping", methods=["GET", "HEAD"])
async def ping():
    return {"status": "ok"}

# import asyncio
# from fastapi import FastAPI, Request
# from contextlib import asynccontextmanager
# import httpx
# import os
# from conversion import AMOUNT_PATTERN, handle_price_it_flow
# from utils import (
#     get_price_dexscreener, get_token_info_dexscreener, register_chat_id, TOKENS, get_price_coinlore, get_token_info,
#     get_fear_greed, get_dominance, format_price, send_message, TELEGRAM_API_URL
# )
# from background import build_message, start_price_checker

# BOT = os.getenv("TELEGRAM_BOT_TOKEN")


# async def set_commands():
#     cmds = [{"command": "price", "description": "Show all prices"}, {
#         "command": "price_it", "description": "Convert token ⇄ USD"}]
#     cmds += [{"command": f"info_{k.replace('-', '_')}",
#               "description": f"Info on {v['display_name']}"} for k, v in TOKENS.items()]
#     cmds += [
#         {"command": "info_fear_greed", "description": "Fear & Greed index"},
#         {"command": "info_dominance", "description": "Market dominance"},

#     ]
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
#     # print('[lifespan] running now')
#     asyncio.create_task(start_price_checker())
#     await set_webhook()
#     await set_commands()
#     yield

# app = FastAPI(lifespan=lifespan)


# @app.post("/webhook")
# async def webhook(req: Request):
#     b = await req.json()
#     msg = b.get("message", {})
#     t, cid = msg.get("text", ""), msg.get("chat", {}).get("id")
#     if cid:
#         register_chat_id(cid)

#     resp = "👋 Send /price to get chart prices."
#     if t == "/price":
#         # prices = {k: (await get_price_coinlore(k)) or format_price(msg) for k in TOKENS}
#         prices = {k: (await get_price_dexscreener(k)) for k in TOKENS}
#         resp = build_message(prices)
#     elif t == "/price_it":
#         return await send_message(
#             cid, "💱 Send a token amount like `10 wkc` or a USD value like `$5`. I'll price it for you!"
#         )

#     elif AMOUNT_PATTERN.match(t or ""):
#         return await handle_price_it_flow(cid, t)
#     elif t.startswith("/info_"):
#         cmd = t[6:].replace("_", "-")
#         if cmd in TOKENS:
#             # d = await get_token_info(cmd)
#             d = await get_token_info_dexscreener(cmd)
#             resp = "\n".join([
#                 f"*{TOKENS[cmd]['display_name']} Info*",
#                 f"Price: ${d['price']}",
#                 f"Market Cap: ${d['market_cap']}",
#                 f"Vol 24h: ${d['vol_24']}",
#                 f"Change 24h: {d['chg_24']}",
#                 f"Supply: {d['supply']}",
#                 f"Contract: `{d['contract']}`",
#                 f"Msg: `{d['msg']}`"
#             ])
#         elif cmd == "fear-greed":
#             resp = f"🙀🤑 Fear & Greed:\n\n{await get_fear_greed()}"
#         elif cmd == "dominance":
#             resp = f"💹 Dominance:\n\n{await get_dominance()}"
#     await send_message(cid, resp)
#     return {"ok": True}


# # this will work with uptimeroobot to kep render.com alive,
# # if you are using free tier else comment out
# @app.api_route("/ping", methods=["GET", "HEAD"])
# async def ping():
#     return {"status": "ok"}
