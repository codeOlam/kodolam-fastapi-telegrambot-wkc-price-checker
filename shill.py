# ai.py
import os
import traceback
import httpx
import random

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SHILL_TONES = {
    "funny": (
        "Write a hilarious WKC shill tweet in Gen Z meme style. "
        "Use crypto slang, emojis, and jokes. Be entertaining, absurd, but end on a bullish note. "
        "Mention $WKC and include the hashtag #WikiCat. Keep it as a single X post."
    ),
    "bullish": (
        "Write a bullish and hype-filled WKC shill tweet. Emphasize growth, future potential, and big gains. "
        "Use strong positive language. Mention $WKC and include the hashtag #WikiCat. Keep it as a single X post."
    ),
    "serious": (
        "Write a serious, informative shill tweet about WKC. Explain tokenomics, deflationary mechanics, auto-burns, "
        "or market position. Appeal to logical investors. End with $WKC and #WikiCat. Keep it as a single X post."
    ),
    "degen": (
        "Write a degenerate-style WKC shill tweet like it’s 2am and you just aped in. Pure chaos, moon vibes, max risk. "
        "Use wild energy, slang, and humor. End with $WKC and #WikiCat. Keep it as a single X post."
    ),
    "meme": (
        "Create a viral meme-style WKC tweet. Be clever, fast-paced, and punchy. Include something shocking, witty, "
        "or ironic. End with $WKC and #WikiCat. Keep it as a single X post."
    ),
    "analyst": (
        "Write a shill tweet for WKC from the perspective of a professional crypto analyst. "
        "Highlight trends, deflationary supply, tokenomics, volume, and market growth. "
        "Use technical but accessible language. End with $WKC and #WikiCat. Keep it as a single X post."
    ),
    "trader": (
        "Write a shill tweet about WKC from a technical trader's perspective. Mention support levels, breakouts, "
        "volume spikes, or entry zones. Use crisp, trader-style language. End with $WKC and #WikiCat. "
        "Keep it as a single X post."
    ),
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
