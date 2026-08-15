#!/bin/bash

TOKEN="${TELEGRAM_BOT_TOKEN}"
NGROK_URL="$1"

if [ -z "$TOKEN" ]; then
  echo "❌ Error: TELEGRAM_BOT_TOKEN is not set."
  exit 1
fi

if [ -z "$NGROK_URL" ]; then
  echo "❌ Error: You must provide a public URL (e.g., from ngrok/cloudflared)."
  echo "Usage: ./ngrok-webhook.sh https://xxxx-xx-xx-xx.ngrok-free.app"
  exit 1
fi

curl -X POST "https://api.telegram.org/bot$TOKEN/setWebhook?url=$NGROK_URL/webhook"