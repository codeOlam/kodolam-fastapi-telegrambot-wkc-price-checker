#!/bin/bash

# This assumes TELEGRAM_BOT_TOKEN is set in your environment
TOKEN="${TELEGRAM_BOT_TOKEN}"
URL="$1"

if [ -z "$TOKEN" ]; then
  echo "❌ Error: TELEGRAM_BOT_TOKEN is not set."
  exit 1
fi

if [ -z "$URL" ]; then
  echo "❌ Error: You must provide a public URL (e.g., from ngrok/cloudflared)."
  echo "Usage: ./set-webhook.sh https://your-tunnel-url"
  exit 1
fi

curl -X POST "https://api.telegram.org/bot$TOKEN/setWebhook" \
     -H "Content-Type: application/json" \
     -d "{\"url\": \"$URL/webhook\"}"