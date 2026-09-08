# 📊 WKC WatchBot (FastAPI + Telegram)

**WKC WatchBot** is a lightweight Telegram bot that posts real-time crypto signals for
[WikiCat (WKC)](https://dexscreener.com/bsc/0x933477eba23726ca95a957cb85dbb1957267ef85)
to a Telegram channel and answers on-demand commands for token data, BTC/ETH dominance,
and the Fear & Greed Index. Built with **FastAPI**, **Python 3.12+**, and the
**Telegram Bot API**.

It is designed to run entirely on **free tiers** — no paid data providers, no API keys
required for the core features (an optional Groq key powers the AI "shill post"
generator only).

---

## 🧩 Features

- **Price-move alerts** — posts to the channel only when WKC actually moves ±0.2%
  since the last alert (not on a fixed schedule), with market cap, holder count, and
  24h change baked in.
- **⏱ Hourly Pulse** — buy/sell counts and buy-pressure % for the last hour.
- **📅 Daily / 🗓 Weekly recaps** — price, market cap, and holder deltas versus the
  start of the period.
- **🔥 Burn tracking** — reads the dead-address balance from the holder list.
- **🐋 Whale alerts** — decodes PancakeSwap `Swap` events straight off BSC public RPC
  nodes and posts any single trade above a configurable USD threshold, with a BscScan
  link. `/setwhale <amount>` tunes the threshold live (admin only).
- **On-demand commands / buttons** — token info (price, 24h change, market cap, volume,
  supply, contract), Fear & Greed Index, BTC/ETH dominance.
- **🧮 Dre Price Calculator** — quick `10 wkc` / `$5` conversions.
- **🥷 Emjay Market Ninja** — estimate market cap from a price point, or profit from an
  entry/exit.
- **🐱 Shill generator** — optional AI-generated WKC posts in several tones (needs a
  Groq API key).

### Data sources (all free, keyless)

| Purpose | Source |
| --- | --- |
| Token price / pair data | [DexScreener](https://docs.dexscreener.com/) |
| Ticker prices, global dominance | [CoinLore](https://www.coinlore.com/cryptocurrency-data-api) |
| Holder count, token security, burn balance | [GoPlus](https://docs.gopluslabs.io/) |
| On-chain swap events | BSC public RPC (`publicnode.com`) |
| Fear & Greed Index | [alternative.me](https://alternative.me/crypto/fear-and-greed-index/) |
| AI shill posts (optional) | [Groq](https://console.groq.com/) |

---

## 🚀 Quick start (local)

```bash
git clone <your-fork-url>
cd telegrambot

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configure

Create a bot with [@BotFather](https://t.me/BotFather), then set these environment
variables (e.g. in a `.env` file — it is git-ignored):

| Variable | Required | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from BotFather |
| `CHANNEL_ID` | ✅ | Target channel's **numeric** ID (e.g. `-100XXXXXXXXXX`). Prefer the numeric ID over `@handle` — a channel rename breaks a handle. |
| `WEBHOOK_URL` | ✅ (prod) | Public HTTPS URL Telegram should call, e.g. `https://your-app.onrender.com/webhook` |
| `ADMIN_CHAT_ID` | optional | Telegram chat ID allowed to run `/setwhale`. If unset, `/setwhale` is disabled. |
| `GROQ_API_KEY` | optional | Enables the AI shill-post generator |

```bash
# bash / zsh
export TELEGRAM_BOT_TOKEN=...
export CHANNEL_ID=-100xxxxxxxxxx
export WEBHOOK_URL=https://your-app.example.com/webhook
```

```fish
set -x TELEGRAM_BOT_TOKEN ...
set -x CHANNEL_ID -100xxxxxxxxxx
```

### Run

```bash
uvicorn main:app --reload      # http://127.0.0.1:8000
```

For local webhook testing, expose the port with a tunnel (ngrok, cloudflared) and
register it:

```bash
./set-webhook.sh https://your-tunnel-url        # or ./ngrok-webhook.sh <url>
```

Both scripts read `TELEGRAM_BOT_TOKEN` from the environment.

---

## ☁️ Deploy to Render

[`render.yaml`](render.yaml) is a Render Blueprint. Fork the repo, create a **New
Blueprint** in Render pointed at your fork, and set the environment variables from the
table above in the Render dashboard (they are marked `sync: false` so they are never
committed).

On startup the app registers its webhook with Telegram (`WEBHOOK_URL`), sets the
command menu, and launches the background tasks (price checker, hourly pulse, digests,
whale watcher) via FastAPI lifespan events.

### Keeping it awake

Render's free web service sleeps on inactivity. Point an uptime pinger (e.g.
[UptimeRobot](https://uptimerobot.com)) at `https://your-app.onrender.com/ping` every
5–10 minutes.

---

## 🗂 Project layout

```
main.py           FastAPI app, Telegram webhook, command/callback routing
background.py     Periodic tasks: price alerts, hourly pulse, digests, whale watcher
utils.py          Shared helpers: data fetchers, on-chain decoding, formatters, state
conversion.py     "Dre" price calculator flow
marketOracle.py   "Emjay" market-cap / profit estimator flow
tokenInfo.py      Token info card rendering
shill.py          Optional Groq-backed post generator
render.yaml       Render Blueprint
set-webhook.sh    Register the Telegram webhook (reads env)
ngrok-webhook.sh  Same, for an ngrok/tunnel URL
```

Runtime state (`chat_ids.json`, `digest_state.json`, `whale_config.json`,
`whale_state.json`) is written to the working directory and is git-ignored. On Render's
free tier the filesystem is ephemeral, so these reset on redeploy.

---

## 🔐 Security notes

- Never commit `.env` or hard-code tokens — all secrets come from environment
  variables, and `.env` / macOS metadata files are git-ignored.
- If you fork from an existing deployment, **rotate the bot token** (BotFather →
  `/revoke`) and any Groq key so the previous operator can't post as your bot.
- The `/webhook` endpoint does not currently verify Telegram's
  [secret token](https://core.telegram.org/bots/api#setwebhook). Anyone who learns the
  URL can POST a crafted update. `/setwhale` is additionally guarded by an
  `ADMIN_CHAT_ID` match, but for production you should set a `secret_token` on
  `setWebhook` and check the `X-Telegram-Bot-Api-Secret-Token` header. See
  [Todo](#-todo).

---

## 📌 Todo

- [ ] Verify Telegram's webhook secret token on `/webhook`
- [ ] Add response caching to cut redundant API calls
- [ ] Persist runtime state to a real datastore (survives redeploys)
- [ ] Route error/logging output to a private channel

---

## 📄 License

No license file is included yet. Add one (e.g. `LICENSE` with MIT) before publishing if
you want others to be able to reuse the code.
