import asyncio
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import httpx
import os
from utils import (
    register_chat_id, TOKENS, get_price_coinlore, get_token_info,
    get_fear_greed, get_dominance, format_price, send_message, TELEGRAM_API_URL
)
from background import build_message, start_price_checker

BOT = os.getenv("TELEGRAM_BOT_TOKEN")


async def set_commands():
    cmds = [{"command": "price", "description": "Show all prices"}]
    cmds += [{"command": f"info_{k.replace('-', '_')}",
              "description": f"Info on {v['display_name']}"} for k, v in TOKENS.items()]
    cmds += [
        {"command": "info_fear_greed", "description": "Fear & Greed index"},
        {"command": "info_dominance", "description": "Market dominance"}
    ]
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
    # print('[lifespan] running now')
    asyncio.create_task(start_price_checker())
    await set_webhook()
    await set_commands()
    yield

app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(req: Request):
    b = await req.json()
    msg = b.get("message", {})
    t, cid = msg.get("text", ""), msg.get("chat", {}).get("id")
    if cid:
        register_chat_id(cid)

    resp = "👋 Send /price to get chart prices."
    if t == "/price":
        prices = {k: (await get_price_coinlore(k)) or format_price(msg) for k in TOKENS}
        resp = build_message(prices)
    elif t.startswith("/info_"):
        cmd = t[6:].replace("_", "-")
        if cmd in TOKENS:
            d = await get_token_info(cmd)
            resp = "\n".join([
                f"*{TOKENS[cmd]['display_name']} Info*",
                f"Price: ${d['price']}",
                f"Market Cap: ${d['market_cap']}",
                f"Vol 24h: ${d['vol_24']}",
                f"Change 24h: {d['chg_24']}",
                f"Supply: {d['supply']}",
                f"Contract: `{d['contract']}`",
                f"Msg: `{d['msg']}`"
            ])
        elif cmd == "fear-greed":
            resp = f"🙀🤑 Fear & Greed:\n\n{await get_fear_greed()}"
        elif cmd == "dominance":
            resp = f"💹 Dominance:\n\n{await get_dominance()}"
    await send_message(cid, resp)
    return {"ok": True}


# this will work with uptimeroobot to kep render.com alive,
# if you are using free tier else comment out
@app.get("/ping")
async def ping():
    return {"status": "ok"}
