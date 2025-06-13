from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import asyncio
import httpx

from utils import (
    get_token_id_from_command, register_chat_id, TOKENS, get_token_price, TELEGRAM_API_URL, send_message,
    send_token_info, get_fear_and_greed_index, get_market_dominance
)
from background import build_price_message, start_price_checker


async def set_bot_commands():
    commands = {
        "commands": [
            {"command": "price", "description": "Get all token prices"},
            *[
                {"command": f"info_{token.replace('-', '_')}",
                 "description": f"Info about {data['display_name']}"}
                for token, data in TOKENS.items()
            ],
            {"command": "info_fear_greed", "description": "Crypto Fear & Greed Index"},
            {"command": "info_dominance",
                "description": "Bitcoin and Altcoin Market Dominance"},
        ]
    }

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(f"{TELEGRAM_API_URL}/setMyCommands", json=commands)
            r.raise_for_status()
            print("✅ Bot commands updated.")
        except httpx.HTTPError as e:
            print(f"[ERROR] Failed to set bot commands: {e}")
        # await client.post(f"{TELEGRAM_API_URL}/setMyCommands", json=commands)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(start_price_checker())
    await set_bot_commands()
    print("✅ Bot is running and sending price updates to channel.")
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    message = data.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")

    if chat_id:
        register_chat_id(chat_id)

    if text == "/price":
        await send_price(chat_id)
    elif text.startswith("/info_"):
        command = text[6:]  # e.g. 'wiki_cat'
        token_id = get_token_id_from_command(command)
        if token_id in TOKENS:
            await send_token_info(chat_id, token_id)
        elif command == "fear_greed":
            index = await get_fear_and_greed_index()
            await send_message(chat_id, index)
        elif command == "dominance":
            dominance = await get_market_dominance()
            await send_message(chat_id, dominance)
        else:
            await send_message(chat_id, "❌ Unknown command.")
    else:
        await send_message(chat_id, "👋 Send /price to get latest crypto prices!")

    return {"ok": True}


async def send_price(chat_id):
    prices = {}
    for token_id in TOKENS:
        price = await get_token_price(token_id)
        prices[token_id] = price or "N/A"
    message = build_price_message(prices)
    await send_message(chat_id, message)
