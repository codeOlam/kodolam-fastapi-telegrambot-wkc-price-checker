#!/bin/bash

echo "Starting price checker worker..."
python3 -c "
import asyncio
from background import start_price_checker
asyncio.run(start_price_checker())
"

echo "Setting Telegram Webhook..."

# Set webhook using the TELEGRAM_BOT_TOKEN from Render's injected env var
curl -s -X POST https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook \
  -d "url=https://kodolam-fastapi-telegrambot-wkc-price.onrender.com/webhook"

echo "Webhook set. Starting background worker..."