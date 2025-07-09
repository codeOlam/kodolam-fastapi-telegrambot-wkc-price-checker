import traceback
from utils import (
    get_token_info_dexscreener,
    send_message,
    format_price,
    TOKENS,
    parse_price,
    format_change,
    send_message_with_buttons
)

EmjayState = {}


def parse_market_cap(text):
    text = text.upper().replace("$", "").strip()
    if text.endswith("T"):
        return float(text[:-1]) * 1e12
    elif text.endswith("B"):
        return float(text[:-1]) * 1e9
    elif text.endswith("M"):
        return float(text[:-1]) * 1e6
    elif text.endswith("K"):
        return float(text[:-1]) * 1e3
    else:
        return float(text)


async def start_emjay_oracle(chat_id, step):
    state = EmjayState.setdefault(chat_id, {"step": 0})

    if step.startswith("oracle|"):
        token_key = step.split("|")[1]
        token = TOKENS.get(token_key)
        if not token:
            return await send_message(chat_id, "❌ Unknown token selected.")
        state.update({
            "step": 1,
            "sym": token["display_name"].lower(),
            "token_key": token_key
        })
        return await send_message(chat_id, f"📥 How many *{token['display_name']}* tokens do you hold or plan to buy? (e.g. `1000000000`)")

    if state["step"] == 1:
        try:
            amt = parse_price(step)
            state.update({"amt": float(amt)})
            state["step"] = 2
            return await send_message(chat_id, "🧾 What was your *entry market cap*? (e.g. `$50M`) or type `skip` to use current MC.")
        except:
            return await send_message(chat_id, "❌ Couldn't parse your token amount. Try `1000000` or `5e6`.")

    if state["step"] == 2:
        if step.lower() == "skip":
            state["entry_mc"] = None
        else:
            try:
                state["entry_mc"] = float(parse_market_cap(step))
            except:
                traceback.print_exc()
                return await send_message(chat_id, "❌ Invalid entry market cap format. Try `$50M`, `2B`, or `0.5T`.")
        state["step"] = 3
        return await send_message(chat_id, "🎯 What's your *exit market cap*? (e.g. `$500M`, `10B`, `1T`)")

    if state["step"] == 3:
        try:
            exit_mc = float(parse_market_cap(step))
            state["exit_mc"] = exit_mc

            key = state["token_key"]
            token_info = TOKENS[key]

            # Get current price & MC
            pd = await get_token_info_dexscreener(key)
            total_supply = parse_market_cap(pd.get("supply"))
            if not total_supply:
                return await send_message(chat_id, "❌ Total supply not available for this token.")

            # Use entry MC (provided or fallback to current)
            entry_mc = state["entry_mc"] or parse_market_cap(
                pd["market_cap"])
            price_entry = entry_mc / total_supply
            price_exit = exit_mc / total_supply

            amt = state["amt"]
            cost_at_entry = amt * price_entry
            value_at_exit = amt * price_exit
            gain_x = price_exit / price_entry
            gain_pct = ((price_exit - price_entry) / price_entry) * 100
            profit = value_at_exit - cost_at_entry

            msg = (
                f"🥷 *Emjay Ninja Results*\n\n"
                f"🎯 Token: *{token_info['display_name']}*\n"
                f"💼 Holdings: *{amt:,.0f} {token_info['display_name'].upper()}*\n"
                f"💰 {'Entry MC' if state['entry_mc'] else 'Current MC'}: *${format_price(entry_mc, compact=True)}*\n"
                f"🚀 Exit MC: *${format_price(exit_mc, compact=True)}*\n\n"
                f"💵 Price @ {'Entry MC' if state['entry_mc'] else 'Current MC'}: *${format_price(price_entry)}*\n"
                f"💵 Price @ Exit MC: *${format_price(price_exit)}*\n"
                f"📈 Gain: *{gain_x:.2f}x | {format_change(gain_pct)}*\n"
                f"💸 Cost @ Entry: *${cost_at_entry:,.2f}*\n"
                f"🏁 Value @ Exit: *${value_at_exit:,.2f}*\n"
                f"🏆 Profit: *${profit:,.2f}*\n\n"
                f"⚠️ *Note: Auto-deflation (burn) mechanics are not reflected in this estimate.*\n"
                f"\n🔗 TG: @kodOlamWkcWatcher"
            )

            buttons = [
                [{"text": "🔁 Reset", "callback_data": "emjay_reset"}],
                [{"text": "🏠 Home", "callback_data": "go_home"}],
                [{"text": "🥷 How this was calculated?", "callback_data": "emjay_how"}],
            ]

            return await send_message_with_buttons(chat_id, msg, buttons)

        except Exception:
            traceback.print_exc()
            return await send_message(chat_id, "❌ Invalid market cap format. Try `$50M`, `$12B`, or `$0.5T`.")


async def reset_emjay(chat_id):
    EmjayState.pop(chat_id, None)
    return await send_message(chat_id, "🔄 Emjay Oracle reset. Run `/emjay_market_oracle` to start again.")


async def show_emjay_ninja_buttons(cid):
    buttons = []
    row = []
    for k, v in TOKENS.items():
        if "pairAddress" not in v:
            continue
        row.append(
            {"text": f"{v['emoji']} {v['display_name']}", "callback_data": f"oracle|{k}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        buttons.append(
            [{"text": "🙅🏾 Cancel", "callback_data": "emjay_cancel"}])
    return await send_message_with_buttons(cid, "🥷 Emjay says: pick any token", buttons)
