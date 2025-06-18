# worker.py
import asyncio
import signal
import sys
from background import start_price_checker


def shutdown():
    # Graceful shutdown signal received.
    sys.exit(0)


async def main():
    try:
        # print("🔁 Worker starting price checker...")
        await start_price_checker()
    except Exception as e:
        # print(f"[Worker Error] {type(e).__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: shutdown())
    signal.signal(signal.SIGINT, lambda *_: shutdown())
    asyncio.run(main())
