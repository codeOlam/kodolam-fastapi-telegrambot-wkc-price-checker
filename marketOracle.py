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

    if step.startswith("estimate_profit|"):
        token_key = step.split("|")[1]
        token = TOKENS.get(token_key)
        if not token:
            return await send_message(chat_id, "❌ Unknown token selected.")
        state.update({
            "step": 1,
            "sym": token["display_name"].lower(),
            "token_key": token_key,
            "option": "estimate_profit"
        })
        return await send_message(chat_id, f"📥 How many *{token['display_name']}* tokens do you hold or plan to buy? (e.g. `1000000000`)")

    if state["step"] == 1 and state["option"] == "estimate_profit":
        try:
            amt = parse_price(step)
            state.update({"amt": float(amt)})
            state["step"] = 2
            return await send_message(chat_id, "🧾 What was your *entry market cap*? (e.g. `$50M`) or type `skip` to use current MC.")
        except:
            return await send_message(chat_id, "❌ Couldn't parse your token amount. Try `1000000` or `5e6`.")

    if state["step"] == 2 and state["option"] == "estimate_profit":
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

    if state["step"] == 3 and state["option"] == "estimate_profit":
        await send_message(chat_id, "🥷 Emjay is estimating your profit...")
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
                f"🥷 *Emjay Market Ninja*\n\n"
                f"🎯 Token: *{token_info['display_name']}*\n"
                f"💼 Holdings: *{format_price(amt, compact=True)} {token_info['display_name'].upper()}*\n"
                f"💰 {'Entry MC' if state['entry_mc'] else 'Current MC'}: *${format_price(entry_mc, compact=True)}*\n"
                f"💵 Price @ {'Entry MC' if state['entry_mc'] else 'Current MC'}: *${format_price(price_entry)}*\n"
                f"💸 Cost @ Entry: *${cost_at_entry:,.2f}*\n\n"
                f"🚀 Exit MC: *${format_price(exit_mc, compact=True)}*\n"
                f"💵 Price @ Exit MC: *${format_price(price_exit)}*\n"
                f"📈 Gain: *{format_price(gain_x, compact=True)}x | {format_change(gain_pct)}*\n"
                f"🏁 Value @ Exit: *${format_price(value_at_exit, compact=True)}*\n"
                f"🏆 Profit: *${format_price(profit, compact=True)}*\n"
                f"⚠️ *No tax/burns considered.*\n\n"
                f"\n🔗 TG: @kodOlamWkcWatcher"
            )

            buttons = [
                [{"text": "💰 Try Another Profit Estimate",
                    "callback_data": f"estimate_profit|{state.get('token_key')}"}],
                [{"text": "🔁 Reset", "callback_data": "emjay_reset"}],
                [{"text": "🏠 Home", "callback_data": "go_home"}],
                [{"text": "🥷 How this was calculated?", "callback_data": "emjay_how"}],
            ]

            return await send_message_with_buttons(chat_id, msg, buttons)

        except Exception:
            traceback.print_exc()
            return await send_message(chat_id, "❌ Invalid market cap format. Try `$50M`, `$12B`, or `$0.5T`.")


async def find_mc_from_price_point(chat_id, step):
    state = EmjayState.setdefault(chat_id, {"step": 0})
    # New MC from Price flow

    if step.startswith("price_point|"):
        token_key = step.split("|")[1]
        token = TOKENS.get(token_key)
        sym = token["display_name"]
        if not token:
            return await send_message(chat_id, "❌ Unknown token selected.")
        state.update({
            "step": 1,
            "sym": sym.lower(),
            "token_key": token_key,
            "option": "price_point"
        })
        return await send_message(chat_id, f"💵 Enter a price point for *{sym}* (e.g. `0.000001`) to estimate Market Cap.\nAssuming you hold 1B tokens.")

    if state.get("step") == 1 and state["option"] == "price_point":
        await send_message(chat_id, "🥷 Emjay is estimating the MC...")
        try:
            price = float(parse_price(step))
            key = state["token_key"]
            token = TOKENS[key]
            sym = token["display_name"]

            pd = await get_token_info_dexscreener(key)
            total_supply = float(parse_market_cap(pd.get("supply")))
            if not total_supply:
                return await send_message(chat_id, "❌ Couldn't get total supply for this token.")

            estimated_mc = price * total_supply
            one_billion_cost = 1_000_000_000 * price
            current_mc = parse_market_cap(pd.get("market_cap"))

            price_entry = current_mc / total_supply
            price_exit = estimated_mc / total_supply

            gain_x = price_exit / price_entry
            gain_pct = ((price_exit - price_entry) / price_entry) * 100

            msg = (
                f"🥷 *Emjay Market Ninja*\n\n"
                f"🔹 Token: *{sym}*\n"
                f"💵 Price point: *${format_price(price)}*\n"
                f"🎯 Current Market Cap: *${format_price(current_mc, compact=True)}*\n\n"
                f"📊 Estimated Market Cap: *${format_price(estimated_mc, compact=True)}*\n"
                f"💰 Cost of 1B {sym}: *${format_price(one_billion_cost, compact=True)}*\n"
                f"📈 Gain: *{format_price(gain_x, compact=True)}x | {format_change(gain_pct)}*\n"
                f"⚠️ *No tax/burns considered.*\n\n"
                f"\n🔗 TG: @kodOlamWkcWatcher"
            )

            buttons = [
                [{"text": "🤑 Try Another Price Point",
                    "callback_data": f"price_point|{state.get('token_key')}"}],
                [{"text": "🔁 Reset Price Point",
                    "callback_data": "emjay_reset"}],
                [{"text": "🏠 Home", "callback_data": "go_home"}],
            ]

            EmjayState.pop(chat_id, None)
            return await send_message_with_buttons(chat_id, msg, buttons)

        except Exception:
            traceback.print_exc()
            return await send_message(chat_id, "❌ Invalid price input. Try something like `0.000001` or `5e-7`.")


async def show_emjay_ninja_flow_prompt(cid):
    button = [
        [{"text": "🤑 Estimate MC from price point",
            "callback_data": "emjay_ninja|price_point"}],
        [{"text": "💰 Estimate exit profit",
            "callback_data": "emjay_ninja|estimate_profit"}],
        [{"text": "🙅🏾 Cancel", "callback_data": "emjay_ninja|cancel"}]
    ]

    return await send_message_with_buttons(cid, "🥷 How do I proceed?", button)


async def show_emjay_ninja_buttons(cid, data_cb):
    buttons = []
    row = []
    for k, v in TOKENS.items():
        if "pairAddress" not in v:
            continue
        row.append(
            {"text": f"{v['emoji']} {v['display_name']}", "callback_data": f"{data_cb}|{k}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append(
        [{"text": "🙅🏾 Cancel", "callback_data": "emjay_cancel"}])
    return await send_message_with_buttons(cid, "🥷 Emjay says: pick any token", buttons)
