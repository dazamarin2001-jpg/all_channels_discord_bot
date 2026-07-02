from pathlib import Path
import re


def replace_function(text: str, name: str, replacement: str) -> str:
    start = text.find(f"def {name}(")
    if start == -1:
        return text
    next_start = text.find("\n\ndef ", start + 1)
    if next_start == -1:
        next_start = len(text)
    return text[:start] + replacement.rstrip() + text[next_start:]


def upsert_on_message_event(text: str, replacement: str) -> str:
    start = text.find("@bot.event\nasync def on_message(")
    if start == -1:
        marker = '@bot.tree.command(description="Check whether the bot is responding.")\n'
        return text.replace(marker, replacement.rstrip() + "\n\n" + marker, 1)
    next_command = text.find("\n\n@bot.tree.command", start + 1)
    next_event = text.find("\n\n@bot.event", start + 1)
    candidates = [pos for pos in (next_command, next_event) if pos != -1]
    end = min(candidates) if candidates else len(text)
    return text[:start] + replacement.rstrip() + text[end:]


path = Path("bot.py")
if path.exists():
    text = path.read_text()

    text = re.sub(
        r'RANK_SALES_HEADERS = \[[\s\S]*?\]\n\nRANK_SELLER_TOTALS_HEADERS',
        '''RANK_SALES_HEADERS = [
    "Discord Seller",
    "Seller Habbo",
    "Buyer",
    "Rank Sold",
    "Amount",
    "Proof / Notes",
]

RANK_SELLER_TOTALS_HEADERS''',
        text,
        count=1,
    )
    text = re.sub(
        r'RANK_SELLER_TOTALS_HEADERS = \[[\s\S]*?\]\n\nGOOGLE_SCOPES',
        '''RANK_SELLER_TOTALS_HEADERS = [
    "Discord Username",
    "Habbo Username",
    "Total Sales",
    "Total Amount Sold",
    "Last Rank Sold",
]

GOOGLE_SCOPES''',
        text,
        count=1,
    )

    helpers = '''def seller_identity_display(value: object) -> str:
    text = clean_text(value)
    if not text or text.casefold() == "n/a":
        return ""
    for separator in ("|", " - ", " — ", " – "):
        if separator in text:
            text = text.split(separator, 1)[0].strip()
            break
    text = re.sub(r"\\s+", " ", text)
    return text.strip(" .,-_")


def seller_identity_key(value: object) -> str:
    display = seller_identity_display(value).casefold()
    return re.sub(r"[^a-z0-9]+", "", display)
'''
    if "def seller_identity_display(" not in text:
        text = text.replace("\n\ndef amount_to_credits", "\n\n" + helpers + "\ndef amount_to_credits", 1)

    seller_field = '''    seller_habbo = discord.ui.TextInput(
        label="Seller Habbo Username",
        placeholder="Example: Dazamarin",
        required=True,
        max_length=80,
    )
'''
    text = text.replace(seller_field, "", 1)

    broken_submit = '''            seller_habbo = clean_text(self.children[0].value)
buyer = clean_text(self.children[1].value)
rank = clean_text(self.children[2].value)
amount = clean_text(self.children[3].value)
proof = clean_text(self.children[4].value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
'''
    old_submit = '''            seller_habbo = clean_text(self.children[0].value)
            buyer = clean_text(self.children[1].value)
            rank = clean_text(self.children[2].value)
            amount = clean_text(self.children[3].value)
            proof = clean_text(self.children[4].value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
'''
    already_submit = '''            buyer = clean_text(self.children[0].value)
            rank = clean_text(self.children[1].value)
            amount = clean_text(self.children[2].value)
            proof = clean_text(self.children[3].value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
            seller_habbo = discord_seller
'''
    named_submit = '''            seller_habbo = clean_text(self.seller_habbo.value)
            buyer = clean_text(self.buyer.value)
            rank = clean_text(self.rank.value)
            amount = clean_text(self.amount.value)
            proof = clean_text(self.proof.value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
'''
    new_submit = '''            buyer = clean_text(self.children[0].value)
            rank = clean_text(self.children[1].value)
            amount = clean_text(self.children[2].value)
            proof = clean_text(self.children[3].value) or "N/A"
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
            seller_habbo = discord_seller
'''
    for old in (broken_submit, old_submit, already_submit, named_submit):
        if old in text:
            text = text.replace(old, new_submit, 1)
            break

    text = text.replace("row = [timestamp, discord_seller, seller_habbo, buyer, rank, amount, proof]", "row = [discord_seller, seller_habbo, buyer, rank, amount, proof]", 1)
    text = text.replace('            embed.add_field(name="Seller Habbo", value=seller_habbo, inline=True)', '            embed.add_field(name="Server Username", value=discord_seller, inline=True)', 1)

    text = replace_function(text, "clean_rank_sales_rows", '''def clean_rank_sales_rows(values: list[list[str]]) -> list[list[str]]:
    cleaned = [RANK_SALES_HEADERS]
    if not values:
        return cleaned

    old_header = [cell.strip().casefold() for cell in values[0]]
    has_old_private_columns = "seller id" in old_header or "channel id" in old_header or "channel" in old_header
    looks_like_totals = old_header[:len(RANK_SELLER_TOTALS_HEADERS)] == [h.casefold() for h in RANK_SELLER_TOTALS_HEADERS]
    has_timestamp_column = bool(old_header) and old_header[0] == "timestamp"

    for row in values[1:]:
        if not any(str(cell).strip() for cell in row):
            continue
        padded = list(row) + [""] * 12
        if looks_like_totals:
            continue
        if has_old_private_columns:
            cleaned.append([padded[1], padded[3], padded[4], padded[5], padded[6], padded[7]])
        elif has_timestamp_column:
            cleaned.append([padded[1], padded[2], padded[3], padded[4], padded[5], padded[6]])
        else:
            cleaned.append(padded[:len(RANK_SALES_HEADERS)])
    return cleaned
''')

    text = replace_function(text, "aggregate_rank_sales", '''def aggregate_rank_sales(rows: list[list[str]]) -> dict[str, list[object]]:
    totals: dict[str, list[object]] = {}
    for row in rows:
        padded = list(row) + [""] * len(RANK_SALES_HEADERS)
        discord_seller, seller_habbo, _buyer, rank_sold, amount, _proof = padded[:6]
        seller_habbo = clean_text(seller_habbo)
        discord_seller = clean_text(discord_seller)
        seller_display = seller_identity_display(seller_habbo) or seller_identity_display(discord_seller)
        key = seller_identity_key(seller_habbo) or seller_identity_key(discord_seller)
        if not key:
            continue
        amount_value = amount_to_credits(amount)
        if key not in totals:
            totals[key] = [seller_display or "N/A", seller_display or "N/A", 0, 0.0, rank_sold or "N/A", False]
        record = totals[key]
        if seller_display:
            record[0] = seller_display
            record[1] = seller_display
        record[2] = int(record[2]) + 1
        if amount_value is not None:
            record[3] = float(record[3]) + amount_value
            record[5] = True
        record[4] = rank_sold or record[4]
    return totals
''')

    text = replace_function(text, "write_rank_seller_totals", '''def write_rank_seller_totals(spreadsheet, raw_rows: list[list[str]]) -> None:
    totals_sheet = get_rank_seller_totals_worksheet(spreadsheet)
    totals = aggregate_rank_sales(raw_rows)
    output = [RANK_SELLER_TOTALS_HEADERS]
    for record in totals.values():
        has_amount = bool(record[5])
        output.append([record[0], record[1], record[2], format_credits(float(record[3]) if has_amount else None), record[4]])
    totals_sheet.clear()
    totals_sheet.update(range_name="A1", values=output, value_input_option="USER_ENTERED")
    apply_sales_sheet_style(totals_sheet, len(RANK_SELLER_TOTALS_HEADERS))
''')

    text = replace_function(text, "update_rank_seller_totals_for_sale", '''def update_rank_seller_totals_for_sale(spreadsheet, sale_row: list[str]) -> None:
    totals_sheet = get_rank_seller_totals_worksheet(spreadsheet)
    values = totals_sheet.get_all_values()
    rows = values[1:] if len(values) > 1 else []
    discord_seller, seller_habbo, _buyer, rank_sold, amount, _proof = (sale_row + [""] * 6)[:6]
    seller_display = seller_identity_display(seller_habbo) or seller_identity_display(discord_seller)
    target_habbo = seller_identity_key(seller_habbo)
    target_discord = seller_identity_key(discord_seller)
    new_amount = amount_to_credits(amount)

    for index, row in enumerate(rows, start=2):
        padded = list(row) + [""] * len(RANK_SELLER_TOTALS_HEADERS)
        same_habbo = target_habbo and seller_identity_key(padded[1]) == target_habbo
        same_discord = target_discord and seller_identity_key(padded[0]) == target_discord
        if not same_habbo and not same_discord:
            continue
        try:
            total_sales = int(float(clean_text(padded[2]) or "0")) + 1
        except ValueError:
            total_sales = 1
        previous_amount = amount_to_credits(padded[3])
        total_amount = (previous_amount or 0) + (new_amount or 0) if previous_amount is not None or new_amount is not None else None
        updated = [seller_display or padded[0] or padded[1] or "N/A", seller_display or padded[1] or padded[0] or "N/A", total_sales, format_credits(total_amount), clean_text(rank_sold) or padded[4] or "N/A"]
        totals_sheet.update(range_name=f"A{index}:E{index}", values=[updated], value_input_option="USER_ENTERED")
        apply_sales_sheet_style(totals_sheet, len(RANK_SELLER_TOTALS_HEADERS))
        return

    new_row = [seller_display or "N/A", seller_display or "N/A", 1, format_credits(new_amount), clean_text(rank_sold) or "N/A"]
    next_row = max(len(values) + 1, 2)
    totals_sheet.update(range_name=f"A{next_row}:E{next_row}", values=[new_row], value_input_option="USER_ENTERED")
    apply_sales_sheet_style(totals_sheet, len(RANK_SELLER_TOTALS_HEADERS))
''')

    text = text.replace(
        '''            discord_username = padded[0].strip()
            sales_count = padded[2].strip() or "0"''',
        '''            discord_username = padded[0].strip()
            habbo_username = padded[1].strip()
            if not discord_username or discord_username.casefold() == "n/a":
                discord_username = habbo_username
            sales_count = padded[2].strip() or "0"''',
        1,
    )
    text = text.replace('rank_sales.batch_clear(["H:Z"])', 'rank_sales.batch_clear(["G:Z"])')

    auto_clean_event = '''@bot.event
async def on_message(message: discord.Message) -> None:
    if message.guild is None:
        return

    cleanup_channel_id_raw = os.getenv("AUTO_CLEAN_CHANNEL_ID") or RANK_SALES_CHANNEL_ID
    if not cleanup_channel_id_raw:
        return
    try:
        cleanup_channel_id = int(cleanup_channel_id_raw)
    except ValueError:
        return
    if message.channel.id != cleanup_channel_id:
        return
    if getattr(message, "pinned", False):
        return

    def is_log_message(candidate: discord.Message) -> bool:
        return bool(candidate.embeds) and (candidate.author.bot or candidate.webhook_id is not None)

    if is_log_message(message):
        return

    warning = None
    if not message.author.bot and message.webhook_id is None:
        try:
            warning = await message.channel.send(
                "🧹 **Clean-up crew is here!** This channel is for logs only. Non-log messages will be swept away in **5 seconds** to keep a clean environment."
            )
        except discord.HTTPException:
            warning = None

    await asyncio.sleep(5)
    try:
        current_message = await message.channel.fetch_message(message.id)
        if is_log_message(current_message) or getattr(current_message, "pinned", False):
            return
        await current_message.delete()
        if warning is not None:
            try:
                await warning.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
    except (discord.NotFound, discord.Forbidden):
        pass
    except discord.HTTPException as exc:
        print(f"Auto cleanup failed: {type(exc).__name__}: {exc}")


'''
    text = upsert_on_message_event(text, auto_clean_event)

    path.write_text(text)
    print("Sale log modal now uses server Discord username automatically.")
    print("Timestamps removed from Rank Sales and Rank Seller Totals.")
    print("Sale summary now falls back to Habbo Username when Discord Username is blank.")
    print("Similar seller names are merged before totals are built.")
    print("Auto-clean warning enabled for non-log messages in the sales channel.")

import bot
