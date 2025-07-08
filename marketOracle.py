from utils import send_message, format_price
from conversion import handle_price_it_flow
from utils import TOKENS, parse_price, format_change
import asyncio

EmjayState = {}


async def start_emjay_oracle(chat_id, step):
    state = EmjayState.setdefault(chat_id, {"step": 0})
    if step == "emjay_start":
        state["step"] = 1
        return await send_message(chat_id, "📈 How many tokens do you have? (e.g. `1000000 wkc`)")
    txt = state.get("last_text", "")
    if state["step"] == 1:
        state["last_text"] = txt = step if not step.startswith(
            "emjay_") else txt
        m = txt.split()
        try:
            amt = parse_price(m[0])
            sym = m[1].lower()
            state.update({"amt": amt, "sym": sym})
            state["step"] = 2
            return await send_message(chat_id, f"🔺 What's your *exit* market cap? (eg `$50M`)")
        except:
            return await send_message(chat_id, "❌ Couldn't parse. Please provide something like `1000000 wkc`.")
    if state["step"] == 2:
        exit_mc = parse_price(step.replace("$", "").replace("M", "e6"))
        state["exit_mc"] = exit_mc
        tok = state["sym"]
        key = {v["display_name"].lower(): k for k,
               v in TOKENS.items()}.get(tok)
        if not key:
            return await send_message(chat_id, "❌ Unknown token.")
        # calculate price at exit MC
        data = await handle_price_it_flow(chat_id, f"${exit_mc}")
        await asyncio.sleep(0.1)
        prices = {}  # fetch that token price
        pd = await handle_price_it_flow.__self__.get_price_with_change(key)
        exit_price = pd["raw_price"]  # approximate
        entry_price = state["amt"] * exit_price
        current_price = exit_price
        gain = exit_price / entry_price
        profit = (exit_price - entry_price) * state["amt"]
        return await send_message(chat_id,
                                  f"📊 Emjay Oracle Results:\n\n"
                                  f"🎯 Token: {tok.upper()}\n"
                                  f"💼 Entry Supply: {state['amt']} {tok.upper()}\n"
                                  f"💰 Exit MC: ${exit_mc:,.2f}\n"
                                  f"🚀 Price @ Exit MC: ${exit_price:,.8f}\n"
                                  f"📈 Change: {gain:.2f}x | {format_change((gain-1)*100)}\n"
                                  f"🏆 Profit: ${profit:,.2f}\n"
                                  f"💸 Token Cost @ Exit MC : ${current_price:,.2f}\n"
                                  "\n@kodOlamWkcWatcher"
                                  )


async def reset_emjay(chat_id):
    EmjayState.pop(chat_id, None)
    return await send_message(chat_id, "🔄 Emjay Oracle reset. Run `/emjay_market_oracle` to start again.")
