import traceback
from utils import get_token_info_dexscreener, send_message, format_price, TOKENS, parse_price, format_change, send_message_with_buttons

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
            entry_mc = parse_market_cap(
                state["entry_mc"] or pd["market_cap"])
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

            return await send_message(chat_id, msg)

        except Exception as e:
            traceback.print_exc()
            return await send_message(chat_id, "❌ Invalid market cap format. Try `$50M`, `$12B`, or `$0.5T`.")


async def reset_emjay(chat_id):
    EmjayState.pop(chat_id, None)
    return await send_message(chat_id, "🔄 Emjay Oracle reset. Run `/emjay_market_oracle` to start again.")


# import traceback
# from utils import get_token_info_dexscreener, send_message, format_price, TOKENS, parse_price, format_change

# EmjayState = {}


# def parse_market_cap(text):
#     text = text.upper().replace("$", "").strip()
#     if text.endswith("T"):
#         return float(text[:-1]) * 1e12
#     elif text.endswith("B"):
#         return float(text[:-1]) * 1e9
#     elif text.endswith("M"):
#         return float(text[:-1]) * 1e6
#     elif text.endswith("K"):
#         return float(text[:-1]) * 1e3
#     else:
#         return float(text)


# async def start_emjay_oracle(chat_id, step):
#     state = EmjayState.setdefault(chat_id, {"step": 0})

#     if step.startswith("oracle|"):
#         token_key = step.split("|")[1]
#         token = TOKENS.get(token_key)
#         if not token:
#             return await send_message(chat_id, "❌ Unknown token selected.")
#         state.update({
#             "step": 1,
#             "sym": token["display_name"].lower(),
#             "token_key": token_key
#         })
#         return await send_message(chat_id, f"📥 How many *{token['display_name']}* tokens do you hold or plan to buy? (e.g. `1000000000`)")

#     if state["step"] == 1:
#         try:
#             amt = parse_price(step)
#             state.update({"amt": amt})
#             state["step"] = 2
#             return await send_message(chat_id, "🧾 What was your *entry market cap*? (e.g. `$50M`) or type `skip` to use current MC.")
#         except:
#             return await send_message(chat_id, "❌ Couldn't parse your token amount. Try `1000000` or `5e6`.")

#     if state["step"] == 2:
#         if step.lower() == "skip":
#             state["entry_mc"] = None
#         else:
#             try:
#                 state["entry_mc"] = parse_market_cap(step)
#             except:
#                 return await send_message(chat_id, "❌ Invalid entry market cap format. Try `$50M`, `$2B`, or `$0.5T`.")
#         state["step"] = 3
#         return await send_message(chat_id, "🎯 What's your *exit market cap*? (e.g. `$500M`, `$10B`, `$1T`)")

#     if state["step"] == 3:
#         try:
#             exit_mc = parse_market_cap(step)
#             state["exit_mc"] = exit_mc

#             key = state["token_key"]
#             token_info = TOKENS[key]

#             # Get current price & MC
#             pd = await get_token_info_dexscreener(key)
#             total_supply = pd.get("supply")
#             if not total_supply:
#                 return await send_message(chat_id, "❌ Total supply not available for this token.")

#             # Use entry MC (provided or fallback to current)
#             entry_mc = state["entry_mc"] or pd["market_cap"]
#             exit_mc = state["exit_mc"]

#             price_entry = entry_mc / total_supply
#             price_exit = exit_mc / total_supply

#             amt = state["amt"]
#             cost_at_entry = amt * price_entry
#             value_at_exit = amt * price_exit
#             gain_x = price_exit / price_entry
#             gain_pct = ((price_exit - price_entry) / price_entry) * 100
#             profit = value_at_exit - cost_at_entry

#             return await send_message(chat_id,
#                                       f"🥷 *Emjay Ninja Results*\n\n"
#                                       f"🎯 Token: *{token_info['display_name']}*\n"
#                                       f"💼 Current holdings: *{amt:,.0f} {token_info['display_name'].upper()}*\n"
#                                       f"💰 {'Entry MC' if state["entry_mc"] else 'Current MC'}: *${format_price(entry_mc, compact=True)}*\n"
#                                       f"🚀 Exit MC: *${format_price(exit_mc, compact=True)}*\n\n"
#                                       f"💵 Price @ {'Entry MC' if state["entry_mc"] else 'Current MC'}: *${format_price(price_entry)}*\n"
#                                       f"💵 Price @ Exit MC: *${format_price(price_exit)}*\n"
#                                       f"📈 Gain: *{gain_x:.2f}x | {format_change(gain_pct)}*\n"
#                                       f"💸 Cost @ {'Entry MC' if state["entry_mc"] else 'Current MC'}: *${cost_at_entry:,.2f}*\n"
#                                       f"🏁 Value @ Exit MC: *${value_at_exit:,.2f}*\n"
#                                       f"🏆 Profit: *${profit:,.2f}*\n\n"
#                                       f"🔗 TG: @kodOlamWkcWatcher",
#                                       parse_mode="Markdown"
#                                       )

#         except:
#             traceback.print_exc()
#             return await send_message(chat_id, "❌ Invalid market cap format. Try `$50M`, `$12b`, or `$0.5T`.")


# async def reset_emjay(chat_id):
#     EmjayState.pop(chat_id, None)
#     return await send_message(chat_id, "🔄 Emjay Oracle reset. Run `/emjay_market_oracle` to start again.")


# Last working logic

# import traceback
# from utils import get_price_with_change, send_message, format_price, TOKENS, parse_price, format_change
# from conversion import handle_price_it_flow
# import asyncio

# EmjayState = {}


# def parse_exit_mc(raw: str) -> float:
#     """
#     Parses input like "$50M", "20b", "1.5T" into numeric market cap.
#     """
#     raw = raw.strip().lower().replace("$", "")
#     multiplier = 1

#     if raw.endswith("k"):
#         multiplier = 1e3
#         raw = raw[:-1]
#     elif raw.endswith("m"):
#         multiplier = 1e6
#         raw = raw[:-1]
#     elif raw.endswith("b"):
#         multiplier = 1e9
#         raw = raw[:-1]
#     elif raw.endswith("t"):
#         multiplier = 1e12
#         raw = raw[:-1]

#     try:
#         return float(raw) * multiplier
#     except ValueError:
#         raise ValueError("Invalid number format")


# async def start_emjay_oracle(chat_id, step):
#     state = EmjayState.setdefault(chat_id, {"step": 0})

#     if step.startswith("oracle|"):
#         token_key = step.split("|")[1]
#         token = TOKENS.get(token_key)
#         if not token:
#             return await send_message(chat_id, "❌ Unknown token selected.")
#         state.update({
#             "step": 1,
#             "sym": token["display_name"].lower()
#         })
#         return await send_message(chat_id, f"📈 How many {token['display_name']} tokens do you have? (e.g. `1000000`)")

#     if state["step"] == 1:
#         try:
#             amt = parse_price(step)
#             state.update({"amt": amt})
#             state["step"] = 2
#             return await send_message(chat_id, "↑ What's your *exit* market cap? (e.g. `$50M`, `$12b`, or `$0.5T`)")
#         except:
#             return await send_message(chat_id, "❌ Couldn't parse. Try something like `1000000`.")

#     if state["step"] == 2:
#         try:
#             exit_mc = parse_exit_mc(step)
#             state["exit_mc"] = exit_mc
#             key = {v["display_name"].lower(): k for k, v in TOKENS.items()
#                    }.get(state["sym"])
#             if not key:
#                 return await send_message(chat_id, "❌ Unknown token.")
#             pd = await get_price_with_change(key)
#             exit_price = pd["raw_price"]
#             entry_price = exit_price  # current price baseline
#             gain = (exit_price / entry_price)
#             profit = (exit_price - entry_price) * state["amt"]

#             return await send_message(chat_id,
#                                       f"🥷 Emjay Oracle Results:\n\n"
#                                       f"🎯 Token: {state['sym'].upper()}\n"
#                                       f"💼 Entry Supply: {state['amt']:,} {state['sym'].upper()}\n"
#                                       f"💰 Exit MC: ${exit_mc:,.2f}\n"
#                                       f"🚀 Price @ Exit MC: ${exit_price:,.8f}\n"
#                                       f"📈 Change: {gain:.2f}x | {format_change((gain-1)*100)}\n"
#                                       f"🏆 Profit: ${profit:,.2f}\n"
#                                       f"💸 Token Cost @ Exit MC: ${(entry_price * state['amt']):,.2f}\n"
#                                       "\n\n🔗 TG: @kodOlamWkcWatcher"
#                                       )
#         except:
#             traceback.print_exc()
#             return await send_message(chat_id, "❌ Invalid market cap format. Try `$50M`, `$12b`, or `$0.5T`.")


# async def reset_emjay(chat_id):
#     EmjayState.pop(chat_id, None)
#     return await send_message(chat_id, "🔄 Emjay Oracle reset. Run /emjay_market_oracle to start again.")


# from utils import send_message, format_price, TOKENS, parse_price, format_change
# from conversion import handle_price_it_flow
# import asyncio

# EmjayState = {}


# async def start_emjay_oracle(chat_id, step):
#     state = EmjayState.setdefault(chat_id, {"step": 0})

#     if step.startswith("oracle|"):
#         token_key = step.split("|")[1]
#         token = TOKENS.get(token_key)
#         if not token:
#             return await send_message(chat_id, "❌ Unknown token selected.")
#         state.update({
#             "step": 1,
#             "sym": token["display_name"].lower()
#         })
#         return await send_message(chat_id, f"📈 How many {token['display_name']} tokens do you have? (e.g. `1000000`)")

#     if state["step"] == 1:
#         try:
#             amt = parse_price(step)
#             state.update({"amt": amt})
#             state["step"] = 2
#             return await send_message(chat_id, "🔺 What's your *exit* market cap? (e.g. `$50M`)")
#         except:
#             return await send_message(chat_id, "❌ Couldn't parse. Try something like `1000000`.")

#     if state["step"] == 2:
#         try:
#             exit_mc = parse_price(step.replace("$", "").replace("M", "e6"))
#             state["exit_mc"] = exit_mc
#             key = {v["display_name"].lower(): k for k,
#                    v in TOKENS.items()}.get(state["sym"])
#             if not key:
#                 return await send_message(chat_id, "❌ Unknown token.")
#             pd = await handle_price_it_flow.__self__.get_price_with_change(key)
#             exit_price = pd["raw_price"]
#             entry_price = state["amt"] * exit_price
#             gain = exit_price / (entry_price / state["amt"])
#             profit = (exit_price - (entry_price / state["amt"])) * state["amt"]

#             return await send_message(chat_id,
#                                       f"📊 Emjay Oracle Results:\n\n"
#                                       f"🎯 Token: {state['sym'].upper()}\n"
#                                       f"💼 Entry Supply: {state['amt']:,} {state['sym'].upper()}\n"
#                                       f"💰 Exit MC: ${exit_mc:,.2f}\n"
#                                       f"🚀 Price @ Exit MC: ${exit_price:,.8f}\n"
#                                       f"📈 Change: {gain:.2f}x | {format_change((gain-1)*100)}\n"
#                                       f"🏆 Profit: ${profit:,.2f}\n"
#                                       f"💸 Token Cost @ Exit MC: ${entry_price:,.2f}\n"
#                                       "\n@kodOlamWkcWatcher"
#                                       )
#         except:
#             return await send_message(chat_id, "❌ Invalid market cap format. Try `$50M`.")


# async def reset_emjay(chat_id):
#     EmjayState.pop(chat_id, None)
#     return await send_message(chat_id, "🔄 Emjay Oracle reset. Run `/emjay_market_oracle` to start again.")


# from utils import get_price_with_change, send_message, format_price
# from conversion import handle_price_it_flow
# from utils import TOKENS, parse_price, format_change
# import asyncio

# EmjayState = {}


# async def start_emjay_oracle(chat_id, step):
#     state = EmjayState.setdefault(chat_id, {"step": 0})
#     if step == "emjay_start":
#         state["step"] = 1
#         return await send_message(chat_id, "📈 How many tokens do you have? (e.g. `1000000 wkc`)")
#     txt = state.get("last_text", "")
#     if state["step"] == 1:
#         state["last_text"] = txt = step if not step.startswith(
#             "emjay_") else txt
#         m = txt.split()
#         try:
#             amt = parse_price(m[0])
#             sym = m[1].lower()
#             state.update({"amt": amt, "sym": sym})
#             state["step"] = 2
#             return await send_message(chat_id, f"🔺 What's your *exit* market cap? (eg `$50M`)")
#         except:
#             return await send_message(chat_id, "❌ Couldn't parse. Please provide something like `1000000 wkc`.")
#     if state["step"] == 2:
#         exit_mc = parse_price(step.replace("$", "").replace("M", "e6"))
#         state["exit_mc"] = exit_mc
#         tok = state["sym"]
#         key = {v["display_name"].lower(): k for k,
#                v in TOKENS.items()}.get(tok)
#         if not key:
#             return await send_message(chat_id, "❌ Unknown token.")
#         # calculate price at exit MC
#         data = await handle_price_it_flow(chat_id, f"${exit_mc}")
#         await asyncio.sleep(0.1)
#         prices = {}  # fetch that token price
#         pd = await get_price_with_change(key)
#         exit_price = pd["raw_price"]  # approximate
#         entry_price = state["amt"] * exit_price
#         current_price = exit_price
#         gain = exit_price / entry_price
#         profit = (exit_price - entry_price) * state["amt"]
#         return await send_message(chat_id,
#                                   f"📊 Emjay Oracle Results:\n\n"
#                                   f"🎯 Token: {tok.upper()}\n"
#                                   f"💼 Entry Supply: {state['amt']} {tok.upper()}\n"
#                                   f"💰 Exit MC: ${exit_mc:,.2f}\n"
#                                   f"🚀 Price @ Exit MC: ${exit_price:,.8f}\n"
#                                   f"📈 Change: {gain:.2f}x | {format_change((gain-1)*100)}\n"
#                                   f"🏆 Profit: ${profit:,.2f}\n"
#                                   f"💸 Token Cost @ Exit MC : ${current_price:,.2f}\n"
#                                   "\n@kodOlamWkcWatcher"
#                                   )


# async def reset_emjay(chat_id):
#     EmjayState.pop(chat_id, None)
#     return await send_message(chat_id, "🔄 Emjay Oracle reset. Run `/emjay_market_oracle` to start again.")
