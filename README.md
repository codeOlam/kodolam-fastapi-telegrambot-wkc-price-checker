# 📊 KodOlam WKC WatchBot (FastAPI + Telegram Bot)

**KodOlam WKC WatchBot** is a lightweight Telegram bot that posts real-time crypto price updates to a Telegram channel and responds to user commands for token data, Bitcoin dominance, and Fear & Greed Index. It uses CoinLore (for price data) and CoinGecko (for extra metadata like market cap and logos). Built with **FastAPI**, **Python**, and **Telegram Bot API**.

---

## 🧩 Features

- ✅ Periodic price updates to a Telegram channel (`@kodOlamWkcWatcher`)
- ✅ Supports Telegram commands like `/info_wiki-cat`, `/info_fear_greed`, `/info_dominance`, etc.
- ✅ Token data includes price, 24h % change, market cap, volume, circulating supply, and contract address.
- ✅ Sends rich messages with emojis, formatting, token logos, and external links.
- ✅ Easy deployment via **Render.com** (Infrastructure-as-Code)
- ✅ Scheduled background task via **GitHub Actions**

---

## 🚀 Quick Start (Local Setup)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/kodolam-fastapi-telegrambot-wkc-price-checker.git
cd kodolam-fastapi-telegrambot-wkc-price-checker
```

### 2. Create and activate a virtual environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # on Mac/Linux
venv\Scripts\activate     # on Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## ⚙️ Environment Variables

The following environment variables are required:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from BotFather
- `CHANNEL_ID`: The ID of your target Telegram channel (e.g. `-100XXXXXXXXXX`)

### Option 1: Using `.env` file

Create a `.env` file in the root directory:

```
TELEGRAM_BOT_TOKEN=your_bot_token
CHANNEL_ID=-100xxxxxxxxxxxxx
```

Install `python-dotenv` and load it in your scripts if needed.

### Option 2: Export to shell (e.g., Fish shell)

```fish
set -x TELEGRAM_BOT_TOKEN your_bot_token
set -x CHANNEL_ID -100xxxxxxxxxxxxx
```

Or for Bash/zsh:

```bash
export TELEGRAM_BOT_TOKEN=your_bot_token
export CHANNEL_ID=-100xxxxxxxxxxxxx
```

---

## 🧪 Running Locally

### Start the FastAPI server:

```bash
uvicorn main:app --reload
```

It runs on: `http://127.0.0.1:8000`

To test commands, you can set a webhook using a tunneling service like `ngrok`:

```bash
./ngrok-webhook.sh  # exposes your localhost to the internet
```

Or manually:

```bash
./set-webhook.sh
```

---

## ☁️ Deploying to Render (Blueprint / IaaC)

### 1. Fork this repo to your GitHub account.

### 2. Create a file called `render.yaml` (already included in this repo):

```yaml
services:
  - type: web
    name: kodolam-bot-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port 10000
    envVars:
      - key: TELEGRAM_BOT_TOKEN
        sync: false # Set manually in Render dashboard
      - key: CHANNEL_ID
        sync: false
```

### 3. Deploy with one click:

Go to: https://render.com/docs/infrastructure-as-code

Choose **"New Blueprint"**, connect your repo, and deploy.

> 💡 Make sure to add the required environment variables from the Render dashboard UI after deployment.

---

## ⚙️ GitHub Actions: Background Worker (Price Updates)

This project includes a GitHub Actions workflow that runs every 5 minutes and posts price updates.

### Location:

```
.github/workflows/price-checker.yml
```

### Run it manually:

1. Go to your repo on GitHub
2. Click on **Actions**
3. Select **“Price Checker Bot”**
4. Click **Run Workflow**

### Secrets needed:

Go to **GitHub → Settings → Secrets → Actions**, and add:

- `TELEGRAM_BOT_TOKEN`
- `CHANNEL_ID`

---

## 🗂 File Structure

```
.
├── main.py               # FastAPI app and Telegram webhook
├── background.py         # Periodic price update task
├── utils.py              # Shared helpers (price fetchers, message formatters)
├── render.yaml           # Render.com IaaC config
├── requirements.txt      # Python dependencies
├── ngrok-webhook.sh      # Helper for dev webhook testing
├── set-webhook.sh        # Manual webhook setter
└── README.md             # This doc
```

---

## 🔐 Security Notes

- **Never commit your `.env` file** or hard-code secrets in code.
- Use GitHub Secrets and Render dashboard for secure env var management.

---

## 📌 Todo / Future Plans

- [ ] Add caching to avoid redundant API calls
- [ ] Display token logos using Telegram inline images
- [ ] Add a database to track token history
- [ ] Improve error reporting/logging to a channel

---

## 📫 Contact

Built by [@codeOlam](https://x.com/codeOlam) for [@WikiCatCoin](https://x.com/WikiCatCoin).  
Join the updates: [@kodOlamWkcWatcher](https://t.me/kodOlamWkcWatcher)
