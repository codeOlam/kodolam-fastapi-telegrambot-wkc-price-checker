# ai.py
import os
import traceback
import httpx
import random

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SHILL_TONES = {
    "funny": "Write a hilarious WKC shill tweet in Gen Z meme style. Include emojis, slang and crypto lingo. End with $WKC and #WikiCat.",
    "bullish": "Write a very bullish and hype-filled shill tweet about WKC. Emphasize growth, market potential, and moon talk. End with $WKC and #WikiCat.",
    "serious": "Write a serious and informative shill tweet about WKC's potential, tokenomics, and why it stands out. End with $WKC and #WikiCat.",
    "degen": "Write a degenerate-style WKC shill tweet like a 2am ape post. Wild, chaotic, YOLO energy. End with $WKC and #WikiCat.",
    "meme": "Create a meme-style WKC tweet that could go viral. Don't be boring. End with $WKC and #WikiCat.",
    "analyst": "Write a professional shill tweet about WKC as if you're a market analyst. Focus on price action, volume, and trend momentum. Use trader lingo. End with $WKC and #WikiCat.",
    "trader": "Write a shill tweet about WKC from a trader's perspective. Mention entry points, support/resistance, or a breakout setup. Keep it sharp and technical. End with $WKC and #WikiCat."
}


def build_prompt(tone):
    return SHILL_TONES.get(tone, SHILL_TONES["bullish"])


async def generate_shill_post(tone="bullish"):
    prompt = build_prompt(tone)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.9
                }
            )
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        traceback.print_exc()
        return "⚠️ Failed to generate post. Try again later!"
