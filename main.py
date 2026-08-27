import asyncio
import httpx
import os
import time
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from background import start_price_checker
from conversion import AMOUNT_PATTERN, handle_price_it_flow
from shill import generate_shill_post
from tokenInfo import handle_token_info
from marketOracle import EmjayState, find_mc_from_price_point, show_emjay_ninja_buttons, show_emjay_ninja_flow_prompt, start_emjay_oracle
from utils import (
    CHANNEL_HANDLE, get_dominance, get_fear_greed, register_chat_id, TOKENS,
    send_message_with_buttons, send_message, TELEGRAM_API_URL
)

BOT = os.getenv("TELEGRAM_BOT_TOKEN")

MAIN_MENU = [
    [{"text": "🧮 Dre Price Calculator", "callback_data": "dre_price_it"}],
    [{"text": "🥷 Emjay Market Ninja", "callback_data": "emjay_market_oracle"}],
    [{"text": "🧠 Token Info", "callback_data": "token_info_menu"}],
    [{"text": "🙀🤑 Fear & Greed", "callback_data": "info_fear_greed"}],
    [{"text": "🦾 BTC/ETH Dominance", "callback_data": "info_dominance"}],
    [{"text": "🐱 Shill Me WKC", "callback_data": "shill_me_wkc"}],
    [{"text": "Creator on X", "url": "https://x.com/codeolam"}],
    [{"text": "WikiCat on X", "url": "https://x.com/wikicatcoin"}],
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
            return await show_emjay_ninja_flow_prompt(cid)

        elif data_cb.startswith("emjay_ninja|"):
            option = data_cb.split('|')[1]
            if option == 'cancel':
                DRE_ACTIVE_USERS.pop(cid, None)
                EmjayState.pop(cid, None)
                return await send_message_with_buttons(cid, "❌ Operation canceled.", MAIN_MENU)
            else:
                return await show_emjay_ninja_buttons(cid, option)

        elif data_cb.startswith("estimate_profit|"):
            return await start_emjay_oracle(cid, data_cb)

        elif data_cb.startswith("price_point|"):
            return await find_mc_from_price_point(cid, data_cb)

        elif data_cb == "info_fear_greed":
            return await send_message(cid, f"🙀🤑 Fear & Greed Index\n{await get_fear_greed()}")

        elif data_cb == "info_dominance":
            return await send_message(cid, f"💪🦾 BTC/ETH Market Dominance\n{await get_dominance()}")

        elif data_cb == "cancel":
            DRE_ACTIVE_USERS.pop(cid, None)
            EmjayState.pop(cid, None)
            return await send_message_with_buttons(cid, "❌ Operation canceled.", MAIN_MENU)

        elif data_cb == "emjay_reset":
            EmjayState.pop(cid, None)
            return await show_emjay_ninja_flow_prompt(cid)

        elif data_cb == "go_home":
            EmjayState.pop(cid, None)
            DRE_ACTIVE_USERS.pop(cid, None)
            return await send_message_with_buttons(cid, "🏠 Back to main menu", MAIN_MENU)

        elif data_cb == "emjay_how":
            return await send_message(cid,
                                      "\n".join(["📘 *How Emjay Calculates*\n\n",
                                                 "1. *Price @ MC* = Market Cap ÷ Total Supply\n",
                                                 "2. *Cost @ Entry* = Tokens x Entry Price\n",
                                                 "3. *Value @ Exit* = Tokens x Exit Price\n",
                                                 "4. *Gain* = Exit Price ÷ Entry Price\n",
                                                 "5. *Profit* = Value @ Exit - Cost @ Entry\n\n",
                                                 "⚠️ This tool does *not* simulate tax/burns or liquidity effects.\n",
                                                 "_For tokens with deflation, future supply may be lower than now._",
                                                 f"\n🔗 TG: {CHANNEL_HANDLE}"]),
                                      )

        elif data_cb == "shill_me_wkc":
            tone_buttons = [
                [{"text": "🤣 Funny", "callback_data": "shill_tone|funny"},
                 {"text": "🚀 Bullish", "callback_data": "shill_tone|bullish"}],
                [{"text": "📊 Analyst", "callback_data": "shill_tone|analyst"},
                 {"text": "📈 Trader", "callback_data": "shill_tone|trader"}],
                [{"text": "🧠 Serious", "callback_data": "shill_tone|serious"},
                 {"text": "🧨 Degen", "callback_data": "shill_tone|degen"}],
                [{"text": "😂 Meme", "callback_data": "shill_tone|meme"}],
                [{"text": "🏠 Back", "callback_data": "go_home"}]
            ]
            return await send_message_with_buttons(cid, "🎭 Choose your WKC shill tone:", tone_buttons)

        elif data_cb.startswith("shill_tone|"):
            tone = data_cb.split("|")[1]
            await send_message(cid, "🤖 Generating your post...")
            post = await generate_shill_post(tone)
            return await send_message_with_buttons(
                cid,
                f"🎯 *Your {tone} auto-generated WKC Post:*\n\n`{post}`",
                [
                    [{"text": "♻️ Try Another", "callback_data": "shill_me_wkc"},
                     {"text": "🏠 Home", "callback_data": "go_home"}]
                ]
            )

    if msg == "/start":
        return await send_message_with_buttons(cid, "👋 Welcome! Choose an option:", MAIN_MENU)

    # Route to Emjay if active
    if cid in EmjayState:
        if EmjayState.get(cid, {}).get('option') == 'price_point':
            return await find_mc_from_price_point(cid, msg)
        else:
            return await start_emjay_oracle(cid, msg)

    # Handle Dre
    ts = DRE_ACTIVE_USERS.get(cid)
    dre_active = bool(ts) and time.time() - ts < 120
    if AMOUNT_PATTERN.match(msg or ""):
        if dre_active:
            return await handle_price_it_flow(cid, msg)
        else:
            return await send_message(cid, "❌ Dre ain't listening unless you start with 🧮 Dre Price Calculator.")
    elif dre_active:
        return await send_message(cid, "🤔 Dre didn't catch that. Try something like `10 wkc` or `$5`.")

    return await send_message_with_buttons(cid, "👋 Hello! Press /start to begin.", MAIN_MENU)


@app.api_route("/ping", methods=["GET", "HEAD"])
async def ping():
    return {"status": "ok"}
