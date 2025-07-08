import asyncio
import httpx
import os
import time
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from background import start_price_checker
from conversion import AMOUNT_PATTERN, handle_price_it_flow
from tokenInfo import handle_token_info
from marketOracle import EmjayState, start_emjay_oracle
from utils import (
    get_dominance, get_fear_greed, register_chat_id, TOKENS,
    send_message_with_buttons, send_message, TELEGRAM_API_URL
)

BOT = os.getenv("TELEGRAM_BOT_TOKEN")

MAIN_MENU = [
    [{"text": "🧮 Dre Price Calculator", "callback_data": "dre_price_it"}],
    [{"text": "🥷 Emjay Market Ninja", "callback_data": "emjay_market_oracle"}],
    [{"text": "🧠 Token Info", "callback_data": "token_info_menu"}],
    [{"text": "🙀🤑 Fear & Greed", "callback_data": "info_fear_greed"}],
    [{"text": "🦾 BTC/ETH Dominance", "callback_data": "info_dominance"}],
]

DRE_ACTIVE_USERS = {}  # {chat_id: timestamp}


async def set_commands():
    cmds = [{"command": "start", "description": "Open menu"}]
    async with httpx.AsyncClient() as c:
        await c.post(f"{TELEGRAM_API_URL}/setMyCommands", json={"commands": cmds})


async def set_webhook():
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API_URL}/setWebhook",
                          data={"url": os.getenv("WEBHOOK_URL")})


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(start_price_checker())
    await set_webhook()
    await set_commands()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    cid = (
        data.get("message", {}).get("chat", {}).get("id") or
        data.get("callback_query", {}).get(
            "message", {}).get("chat", {}).get("id")
    )
    msg = data.get("message", {}).get("text", "")
    cb = data.get("callback_query")

    if not cid:
        return {"ok": True}

    register_chat_id(cid)

    # Handle callback queries (button taps)
    if cb:
        data_cb = cb["data"]

        if data_cb == "dre_price_it":
            DRE_ACTIVE_USERS[cid] = time.time()
            EmjayState.pop(cid, None)  # Clear Emjay flow
            return await send_message_with_buttons(
                cid,
                "🚀 Dre's Price Tool activated! Send something like `10 wkc` or `$5`. I’ll run the numbers. (Session lasts 2 min)",
                [[{"text": "Cancel", "callback_data": "cancel"}]]
            )

        elif data_cb == "token_info_menu":
            buttons = []
            row = []
            for k, v in TOKENS.items():
                row.append(
                    {"text": f"{v['emoji']} {v['display_name']}", "callback_data": f"info|{k}"})
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)
            return await send_message_with_buttons(cid, "🧠 Select a token to get details:", buttons)

        elif data_cb.startswith("info|"):
            _, key = data_cb.split("|", 1)
            return await handle_token_info(cid, key)

        elif data_cb == "emjay_market_oracle":
            DRE_ACTIVE_USERS.pop(cid, None)  # Clear Dre flow
            buttons = []
            row = []
            for k, v in TOKENS.items():
                if "contract" not in v:
                    continue
                row.append(
                    {"text": f"{v['emoji']} {v['display_name']}", "callback_data": f"oracle|{k}"})
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)
            return await send_message_with_buttons(cid, "🥷 Emjay says: pick any token", buttons)

        elif data_cb.startswith("oracle|"):
            DRE_ACTIVE_USERS.pop(cid, None)  # Clear Dre flow
            return await start_emjay_oracle(cid, data_cb)

        elif data_cb == "info_fear_greed":
            return await send_message(cid, f"🙀🤑 Fear & Greed Index\n{await get_fear_greed()}")

        elif data_cb == "info_dominance":
            return await send_message(cid, f"💪🦾 BTC/ETH Market Dominance\n{await get_dominance()}")

        elif data_cb == "cancel":
            DRE_ACTIVE_USERS.pop(cid, None)
            EmjayState.pop(cid, None)
            return await send_message_with_buttons(cid, "❌ Operation canceled.", MAIN_MENU)

    if msg == "/start":
        return await send_message_with_buttons(cid, "👋 Welcome! Choose an option:", MAIN_MENU)

    # Route to Emjay if active
    if cid in EmjayState:
        return await start_emjay_oracle(cid, msg)

    # Handle Dre
    if AMOUNT_PATTERN.match(msg or ""):
        ts = DRE_ACTIVE_USERS.get(cid)
        if ts and time.time() - ts < 120:
            return await handle_price_it_flow(cid, msg)
        else:
            return await send_message(cid, "❌ Dre ain't listening unless you start with 🧮 Dre Price Calculator.")

    return await send_message_with_buttons(cid, "👋 Hello! Press /start to begin.", MAIN_MENU)


@app.api_route("/ping", methods=["GET", "HEAD"])
async def ping():
    return {"status": "ok"}


# This is the

# import asyncio
# import traceback
# import httpx
# import os
# import time
# from fastapi import FastAPI, Request
# from contextlib import asynccontextmanager

# from background import start_price_checker
# from conversion import AMOUNT_PATTERN, handle_price_it_flow
# from tokenInfo import handle_token_info
# from marketOracle import EmjayState, start_emjay_oracle
# from utils import (
#     get_dominance, get_fear_greed, register_chat_id, TOKENS,
#     send_message_with_buttons, send_message, TELEGRAM_API_URL
# )

# BOT = os.getenv("TELEGRAM_BOT_TOKEN")

# MAIN_MENU = [
#     [{"text": "🧮 Dre The Price Calculator", "callback_data": "dre_price_it"}],
#     [{"text": "🥷 Emjay The Market Ninja", "callback_data": "emjay_market_oracle"}],
#     [{"text": "🧠 Token Info", "callback_data": "token_info_menu"}],
#     [{"text": "🙀🤑 Fear & Greed", "callback_data": "info_fear_greed"}],
#     [{"text": "🦾 BTC/ETH Dominance", "callback_data": "info_dominance"}],
# ]

# DRE_ACTIVE_USERS = {}  # {chat_id: timestamp}


# async def set_commands():
#     cmds = [{"command": "start", "description": "Open menu"}]
#     async with httpx.AsyncClient() as c:
#         await c.post(f"{TELEGRAM_API_URL}/setMyCommands", json={"commands": cmds})


# async def set_webhook():
#     async with httpx.AsyncClient() as client:
#         await client.post(f"{TELEGRAM_API_URL}/setWebhook",
#                           data={"url": os.getenv("WEBHOOK_URL")})


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     asyncio.create_task(start_price_checker())
#     await set_webhook()
#     await set_commands()
#     yield


# app = FastAPI(lifespan=lifespan)


# @app.post("/webhook")
# async def webhook(req: Request):
#     data = await req.json()
#     cid = (
#         data.get("message", {}).get("chat", {}).get("id") or
#         data.get("callback_query", {}).get(
#             "message", {}).get("chat", {}).get("id")
#     )
#     msg = data.get("message", {}).get("text", "")
#     cb = data.get("callback_query")

#     if not cid:
#         return {"ok": True}

#     register_chat_id(cid)

#     # Handle callback queries (button taps)
#     if cb:
#         data_cb = cb["data"]

#         if data_cb == "dre_price_it":
#             # Start Dre flow and timestamp it
#             DRE_ACTIVE_USERS[cid] = time.time()
#             return await send_message_with_buttons(
#                 cid,
#                 "🚀 Dre's Price Tool activated! Send something like `10 wkc` or `$5`. I’ll run the numbers. (Session lasts 2 min)",
#                 [[{"text": "Cancel", "callback_data": "cancel"}]]
#             )

#         if cid in EmjayState:
#             return await start_emjay_oracle(cid, msg)

#         elif data_cb == "token_info_menu":
#             # 🧠 Build token info buttons in grid (2 per row)
#             buttons = []
#             row = []
#             for i, (k, v) in enumerate(TOKENS.items()):
#                 row.append(
#                     {"text": f"{v['emoji']} {v['display_name']}", "callback_data": f"info|{k}"})
#                 if len(row) == 2:
#                     buttons.append(row)
#                     row = []
#             if row:
#                 buttons.append(row)
#             return await send_message_with_buttons(cid, "🔍 Select a token to get details:", buttons)

#         elif data_cb.startswith("info|"):
#             _, key = data_cb.split("|", 1)
#             return await handle_token_info(cid, key)

#         elif data_cb == "emjay_market_oracle":
#             # 🔢 Emjay Oracle Grid (DexScreener only)
#             buttons = []
#             row = []
#             for k, v in TOKENS.items():
#                 if "contract" not in v:
#                     continue  # skip non-dex tokens
#                 row.append(
#                     {"text": f"{v['emoji']} {v['display_name']}", "callback_data": f"oracle|{k}"})
#                 if len(row) == 2:
#                     buttons.append(row)
#                     row = []
#             if row:
#                 buttons.append(row)
#             return await send_message_with_buttons(cid, "🎯 Emjay says: pick any token", buttons)

#         elif data_cb.startswith("oracle|"):
#             DRE_ACTIVE_USERS.pop(cid, None)  # 🧹 Stop Dre flow

#             _, key = data_cb.split("|", 1)
#             return await start_emjay_oracle(cid, key)

#         elif data_cb == "info_fear_greed":
#             return await send_message(cid, f"🙀🤑 Fear & Greed Index\n{await get_fear_greed()}")

#         elif data_cb == "info_dominance":
#             return await send_message(cid, f"💪🦾 BTC/ETH Market Dominance\n{await get_dominance()}")

#         elif data_cb == "cancel":
#             DRE_ACTIVE_USERS.pop(cid, None)
#             return await send_message_with_buttons(cid, "❌ Operation canceled.", MAIN_MENU)

#     # Handle /start command
#     if msg == "/start":
#         return await send_message_with_buttons(cid,
#                                                "👋 Welcome! Choose an option:", MAIN_MENU)

#     # Handle text input for Dre only if flow was started
#     if AMOUNT_PATTERN.match(msg or ""):
#         # If Emjay is active, ignore Dre
#         if cid in EmjayState:
#             return await start_emjay_oracle(cid, msg)

#         ts = DRE_ACTIVE_USERS.get(cid)
#         if ts and time.time() - ts < 120:  # 2 minutes session window
#             return await handle_price_it_flow(cid, msg)
#         else:
#             return await send_message(cid, "❌ Dre ain't listening unless you start with 🚀 Dre Price Calculator /start.")

#     return await send_message_with_buttons(cid,
#                                            "👋 Hello! Press /start to begin.", MAIN_MENU)


# @app.api_route("/ping", methods=["GET", "HEAD"])
# async def ping():
#     return {"status": "ok"}


# last working update

# import asyncio
# import traceback
# import httpx
# import os
# import time
# from fastapi import FastAPI, Request
# from contextlib import asynccontextmanager

# from background import start_price_checker
# from conversion import AMOUNT_PATTERN, handle_price_it_flow
# from tokenInfo import handle_token_info
# from marketOracle import start_emjay_oracle
# from utils import (
#     get_dominance, get_fear_greed, register_chat_id, TOKENS,
#     send_message_with_buttons, send_message, TELEGRAM_API_URL
# )

# BOT = os.getenv("TELEGRAM_BOT_TOKEN")

# MAIN_MENU = [
#     [{"text": "🚀 Dre Price Calculator", "callback_data": "dre_price_it"}],
#     [{"text": "📈 Emjay Market Oracle", "callback_data": "emjay_market_oracle"}],
#     [{"text": "ℹ️ Token Info", "callback_data": "token_info_menu"}],
#     [{"text": "📊 Fear & Greed", "callback_data": "info_fear_greed"}],
#     [{"text": "📉 BTC/ETH Dominance", "callback_data": "info_dominance"}],
# ]

# DRE_ACTIVE_USERS = {}  # {chat_id: timestamp}


# async def set_commands():
#     cmds = [{"command": "start", "description": "Open menu"}]
#     async with httpx.AsyncClient() as c:
#         await c.post(f"{TELEGRAM_API_URL}/setMyCommands", json={"commands": cmds})


# async def set_webhook():
#     async with httpx.AsyncClient() as client:
#         await client.post(f"{TELEGRAM_API_URL}/setWebhook",
#                           data={"url": os.getenv("WEBHOOK_URL")})


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     asyncio.create_task(start_price_checker())
#     await set_webhook()
#     await set_commands()
#     yield

# app = FastAPI(lifespan=lifespan)


# @app.post("/webhook")
# async def webhook(req: Request):
#     data = await req.json()
#     cid = (
#         data.get("message", {}).get("chat", {}).get("id") or
#         data.get("callback_query", {}).get(
#             "message", {}).get("chat", {}).get("id")
#     )
#     msg = data.get("message", {}).get("text", "")
#     cb = data.get("callback_query")

#     if not cid:
#         return {"ok": True}

#     register_chat_id(cid)

#     # Handle callback queries (button taps)
#     if cb:
#         data_cb = cb["data"]

#         if data_cb == "dre_price_it":
#             return await send_message_with_buttons(
#                 cid,
#                 "🚀 Dre’s Price Tool: send something like `10 wkc` or `$5`. I’ll calculate it!",
#                 [[{"text": "Cancel", "callback_data": "cancel"}]]
#             )

#         elif data_cb == "token_info_menu":
#             # 🧠 Build token info buttons in grid (2 per row)
#             buttons = []
#             row = []
#             for i, (k, v) in enumerate(TOKENS.items()):
#                 row.append(
#                     {"text": f"{v['emoji']} {v['display_name']}", "callback_data": f"info|{k}"})
#                 if len(row) == 2:
#                     buttons.append(row)
#                     row = []
#             if row:
#                 buttons.append(row)
#             return await send_message_with_buttons(cid, "🔍 Select a token to get details:", buttons)

#         elif data_cb.startswith("info|"):
#             _, key = data_cb.split("|", 1)
#             return await handle_token_info(cid, key)

#         elif data_cb == "emjay_market_oracle":
#             # 🔢 Emjay Oracle Grid (DexScreener only)
#             buttons = []
#             row = []
#             for k, v in TOKENS.items():
#                 if "contract" not in v:
#                     continue  # skip non-dex tokens
#                 row.append(
#                     {"text": f"{v['emoji']} {v['display_name']}", "callback_data": f"oracle|{k}"})
#                 if len(row) == 2:
#                     buttons.append(row)
#                     row = []
#             if row:
#                 buttons.append(row)
#             return await send_message_with_buttons(cid, "🎯 Emjay Oracle: pick a Dex token", buttons)

#         elif data_cb.startswith("oracle|"):
#             _, key = data_cb.split("|", 1)
#             return await start_emjay_oracle(cid, key)

#         elif data_cb == "info_fear_greed":
#             return await send_message(cid, f"🙀🤑 Fear & Greed Index\n{await get_fear_greed()}")

#         elif data_cb == "info_dominance":
#             return await send_message(cid, f"💪🦾 BTC/ETH Market Dominance\n{await get_dominance()}")

#         elif data_cb == "cancel":
#             return await send_message_with_buttons(cid, "❌ Operation canceled.", MAIN_MENU)

#     # "/" commands and free text
#     if msg == "/start":
#         return await send_message_with_buttons(cid,
#                                                "👋 Welcome! Choose an option:", MAIN_MENU)

#     if AMOUNT_PATTERN.match(msg or ""):
#         ts = DRE_ACTIVE_USERS.get(cid)
#         if ts and time.time() - ts < 120:  # 2 minutes
#             return await handle_price_it_flow(cid, msg)
#         else:
#             traceback.print_exc()
#             return await send_message(cid, "❌ Dre ain't listening unless you start with 🚀 Dre Price Calculator /start.")

#     return await send_message_with_buttons(cid,
#                                            "👋 Hello! Press /start to begin.", MAIN_MENU)


# @app.api_route("/ping", methods=["GET", "HEAD"])
# async def ping():
#     return {"status": "ok"}


# import asyncio
# import traceback
# import httpx
# import os
# from fastapi import FastAPI, Request
# from contextlib import asynccontextmanager
# from utils import (
#     format_change, get_price_with_change, register_chat_id, TOKENS,
#     get_token_info_dexscreener, get_token_info,
#     get_fear_greed, get_dominance,
#     send_message, send_message_with_buttons, TELEGRAM_API_URL
# )
# from background import build_message, start_price_checker
# from conversion import AMOUNT_PATTERN, handle_price_it_flow, start_dre_flow
# from marketOracle import (
#     EmjayState, start_emjay_flow, reset_emjay
# )

# BOT = os.getenv("TELEGRAM_BOT_TOKEN")


# async def set_commands():
#     cmds = [
#         {"command": "price", "description": "Show all prices"},
#         {"command": "dre_price_it",
#             "description": "Dre token ⇄ USD (button flow)"},
#         {"command": "emjay_market_oracle",
#             "description": "Emjay Market Oracle (simulate gains)"}
#     ]
#     cmds += [{"command": f"info_{k.replace('-', '_')}",
#               "description": f"{TOKENS[k]['display_name']} info"} for k in TOKENS]
#     cmds += [
#         {"command": "info_fear_greed", "description": "Fear & Greed"},
#         {"command": "info_dominance", "description": "Dominance"}
#     ]
#     async with httpx.AsyncClient() as c:
#         await c.post(f"{TELEGRAM_API_URL}/setMyCommands", json={"commands": cmds})


# async def set_webhook():
#     webhook_url = f"https://kodolam-bot-api.onrender.com/webhook"
#     async with httpx.AsyncClient() as client:
#         await client.post(f"{TELEGRAM_API_URL}/setWebhook", data={"url": webhook_url})


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
#     cid = None

#     if 'callback_query' in b:
#         cb = b['callback_query']
#         cid = cb['message']['chat']['id']
#         register_chat_id(cid)
#         data = cb['data']

#         # Dre button flows
#         if data == 'dre_open':
#             return await send_message_with_buttons(
#                 cid,
#                 "🔁 *Dre Options*",
#                 [[{"text": "💵 Convert $ → Token", "callback_data": "dre_usd_to_token"}],
#                  [{"text": "💰 Convert Token → $", "callback_data": "dre_token_to_usd"}]]
#             )
#         elif data in ('dre_usd_to_token', 'dre_token_to_usd'):
#             return await start_dre_flow(cid, data)

#         # Emjay button flows
#         if data == 'emjay_open':
#             return await send_message_with_buttons(
#                 cid,
#                 "📈 *Emjay Market Oracle*",
#                 [[{"text": "🎯 Simulate Gains", "callback_data": "emjay_start"}],
#                  [{"text": "♻️ Reset Oracle", "callback_data": "emjay_reset"}]]
#             )
#         elif data in ('emjay_start',) or EmjayState.in_flow(cid):
#             return await start_emjay_flow(cid, data)
#         elif data == 'emjay_reset':
#             return await reset_emjay(cid)

#     elif 'message' in b:
#         t = b['message'].get('text', '')
#         cid = b['message']['chat']['id']
#         register_chat_id(cid)

#         if t == '/price':
#             prices = {k: await get_price_with_change(k) for k in TOKENS}
#             return await send_message(cid, build_message(prices))

#         if t == '/dre_price_it':
#             return await send_message_with_buttons(
#                 cid,
#                 "🔁 Tap an option for Dre:",
#                 [[{"text": "💵 Convert $ → Token", "callback_data": "dre_usd_to_token"}],
#                  [{"text": "💰 Convert Token → $", "callback_data": "dre_token_to_usd"}]]
#             )

#         if t == '/emjay_market_oracle':
#             return await send_message_with_buttons(
#                 cid,
#                 "📈 Tap an Emjay option:",
#                 [[{"text": "🎯 Simulate Gains", "callback_data": "emjay_start"}],
#                  [{"text": "♻️ Reset Oracle", "callback_data": "emjay_reset"}]]
#             )

#         if t.startswith('/info_'):
#             cmd = t.split('_', 1)[1].replace('_', '-')
#             if cmd in TOKENS:
#                 if TOKENS[cmd].get('contract'):
#                     d = await get_token_info_dexscreener(cmd)
#                     return await send_message(cid, "\n".join([
#                         f"*{TOKENS[cmd]['display_name']} Info*",
#                         f"💡 Name: {d['name']}",
#                         f"💰 Price: ${d['price']} | 📉 24h: {format_change(d['chg_24'])}",
#                         f"📊 MCap: ${d['market_cap']} | 💧 Liq: ${d['liquidity']}",
#                         f"📈 Vol 24h: ${d['vol_24']} | 🔢 Sup: {d['supply']}",
#                         f"🔁 Txns 24h: {d['txns']}",
#                         f"🚀 Lunched: {d['created_at']}",
#                         f"🧾 Contract: `{d['contract']}`",
#                         "\n@kodOlamWkcWatcher"
#                     ]))
#                 else:
#                     d = await get_token_info(cmd)
#                     return await send_message(cid, "\n".join([
#                         f"*{TOKENS[cmd]['display_name']} Info*",
#                         f"💡 Name: {d['name']}",
#                         f"💰 Price: ${d['price']} | 📉 24h: {format_change(d['chg_24'])}",
#                         f"📊 MCap: ${d['market_cap']}",
#                         f"📈 Vol 24h: ${d['vol_24']}",
#                         f"🔢 Sup: {d['supply']}",
#                         "\n@kodOlamWkcWatcher"
#                     ]))

#         if t == '/info_fear_greed':
#             return await send_message(cid, f"🙀🤑 Fear & Greed\n{await get_fear_greed()}\n\n@kodOlamWkcWatcher")
#         if t == '/info_dominance':
#             return await send_message(cid, f"💹 Market Dominance\n{await get_dominance()}\n\n@kodOlamWkcWatcher")

#     # fallback
#     try:
#         if AMOUNT_PATTERN.match(b.get('message', {}).get('text', '') or ""):
#             return await handle_price_it_flow(cid, b['message']['text'])
#     except Exception:
#         traceback.print_exc()
#         return await send_message(cid, "🤯 Dre broke his calculator")

#     # Default
#     await send_message(
#         cid,
#         "👋 Try `/price`, `/dre_price_it`, or `/emjay_market_oracle` to begin!"
#     )
#     return {"ok": True}


# @app.api_route("/ping", methods=["GET", "HEAD"])
# async def ping(): return {"status": "ok"}


# based code base
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
    # return await send_message(cid, "\n".join([
    #     f"*{TOKENS[cmd]['display_name']} Info*\n",
    #     f"💡 Name: {d['name']}",
    #     f"💰 Price: ${d['price']} | 📉 24h: {format_change(d['chg_24'])}",
    #     f"📊 MCap: ${d['market_cap']} | 💧 Liq: ${d['liquidity']}",
    #     f"📈 Vol 24h: ${d['vol_24']} | 🔢 Sup: {d['supply']}",
    #     f"🔁 Txns 24h: {d['txns']}",
    #     f"🚀 Lunched: {d['created_at']}",
    #     f"🧾 Contract: `{d['contract']}`",
    #     f"\n@kodOlamWkcWatcher"
    # ]))
#             else:
#                 d = await get_token_info(cmd)
    # return await send_message(cid, "\n".join([
    #     f"*{TOKENS[cmd]['display_name']} Info*\n",
    #     f"💡 Name: {d['name']}",
    #     f"💰 Price: ${d['price']}",
    #     f"📉 Chg 24h: {format_change(d['chg_24'])}",
    #     f"📊 MCap: ${d['market_cap']}",
    #     f"📈 Vol 24h: ${d['vol_24']}",
    #     f"🔢 Sup: {d['supply']}",
    #     f"\n@kodOlamWkcWatcher"
    # ]))
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
