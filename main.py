import asyncio
import traceback
import httpx
import os
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from utils import (
    get_price_with_change, register_chat_id, TOKENS,
    get_token_info_dexscreener, get_token_info,
    get_fear_greed, get_dominance, send_message, TELEGRAM_API_URL
)
from background import build_message, start_price_checker
from conversion import AMOUNT_PATTERN, handle_price_it_flow

BOT = os.getenv("TELEGRAM_BOT_TOKEN")


async def set_commands():
    cmds = [
        {"command": "price", "description": "Show all prices"},
        {"command": "dre_price_it", "description": "Dre will to advice you on token ⇄ USD"}
    ]
    cmds += [{"command": f"info_{k.replace('-', '_')}",
              "description": f"{TOKENS[k]['display_name']} info"} for k in TOKENS]
    cmds += [{"command": "info_fear_greed", "description": "Fear & Greed"},
             {"command": "info_dominance", "description": "Dominance"}]
    async with httpx.AsyncClient() as c:
        await c.post(f"{TELEGRAM_API_URL}/setMyCommands", json={"commands": cmds})


async def set_webhook():
    webhook_url = f"https://kodolam-bot-api.onrender.com/webhook"
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API_URL}/setWebhook",
            data={"url": webhook_url}
        )


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

    if t == "/price":
        prices = {}
        for k in TOKENS:
            prices[k] = await get_price_with_change(k)
        return await send_message(cid, build_message(prices))

    elif t == "/dre_price_it":
        return await send_message(
            cid,
            "🚀 Yo yo! Dre in the house. Tell me what you're stackin' — `1000000000 wkc` or maybe `$20`? Let me flip the math for ya 📊💰"
        )

    elif t.startswith("/info_"):
        cmd = t.split("_", 1)[1].replace("_", "-")
        if cmd in TOKENS:
            d = await (get_token_info_dexscreener(cmd) if TOKENS[cmd].get("contract") else get_token_info(cmd))
            return await send_message(cid, "\n".join([
                f"*{TOKENS[cmd]['display_name']} Info*",
                f"Price: ${d['price']}",
                f"Market Cap: ${d['market_cap']}",
                f"Vol 24h: ${d['vol_24']}",
                f"Change 24h: {d['chg_24']}",
                f"Supply: {d['supply']}",
                f"Contract: `{d['contract']}`",
                f"Note: {d['msg']}"
            ]))
        elif cmd == "fear":
            return await send_message(cid, f"🙀🤑 Fear & Greed: {await get_fear_greed()}")
        elif cmd == "dominance":
            return await send_message(cid, f"💹 Market Dominance: {await get_dominance()}")

    try:
        if AMOUNT_PATTERN.match(t or ""):
            return await handle_price_it_flow(cid, t)
    except Exception:
        traceback.print_exc()
        return await send_message(cid, "🤯 Dre broke his calculator")

    # ➕ Default fallback if none of the above matched
    await send_message(
        cid,
        "👋 Yo! kodOlam here. Try `/price`, `/dre_price_it`, or send Dre something like `1000000000 wkc`, `100 xrp` or `$5` and let Dre crunch the numbers. 🧠💰"
    )
    return {"ok": True}


# this will work with uptimeroobot to kep render.com alive,
# if you are using free tier else comment out
@app.api_route("/ping", methods=["GET", "HEAD"])
async def ping():
    return {"status": "ok"}
