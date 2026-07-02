from pathlib import Path
import re


def replace_top_function(text: str, name: str, replacement: str) -> str:
    start = text.find(f"def {name}(")
    if start == -1:
        return text
    next_start = text.find("\n\ndef ", start + 1)
    if next_start == -1:
        next_start = len(text)
    return text[:start] + replacement.rstrip() + text[next_start:]


path = Path("bot.py")
if path.exists():
    text = path.read_text()

    # Remove timestamp columns from both sheet layouts.
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

    # Fix the bad indentation from the previous modal edit if it exists.
    broken = '''            seller_habbo = clean_text(self.children[0].value)
buyer = clean_text(self.children[1].value)
rank = clean_text(self.children[2].value)
amount = clean_text(self.children[3].value)
proof = clean_text(self.children[4].value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")'''
    fixed = '''            seller_habbo = clean_text(self.children[0].value)
            buyer = clean_text(self.children[1].value)
            rank = clean_text(self.children[2].value)
            amount = clean_text(self.children[3].value)
            proof = clean_text(self.children[4].value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")'''
    text = text.replace(broken, fixed, 1)

    # Remove the Seller Habbo Username field from the Discord modal.
    seller_field = '''    seller_habbo = discord.ui.TextInput(
        label="Seller Habbo Username",
        placeholder="Example: Dazamarin",
        required=True,
        max_length=80,
    )
'''
    text = text.replace(seller_field, "", 1)

    # Use the server Discord nickname/display name automatically as the seller name.
    new_children_block = '''            buyer = clean_text(self.children[0].value)
            rank = clean_text(self.children[1].value)
            amount = clean_text(self.children[2].value)
            proof = clean_text(self.children[3].value) or "N/A"
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
            seller_habbo = discord_seller
'''
    modal_variants = [
        '''            seller_habbo = clean_text(self.children[0].value)
            buyer = clean_text(self.children[1].value)
            rank = clean_text(self.children[2].value)
            amount = clean_text(self.children[3].value)
            proof = clean_text(self.children[4].value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
''',
        '''            buyer = clean_text(self.children[0].value)
            rank = clean_text(self.children[1].value)
            amount = clean_text(self.children[2].value)
            proof = clean_text(self.children[3].value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
            seller_habbo = discord_seller
''',
        '''            seller_habbo = clean_text(self.seller_habbo.value)
            buyer = clean_text(self.buyer.value)
            rank = clean_text(self.rank.value)
            amount = clean_text(self.amount.value)
            proof = clean_text(self.proof.value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
''',
    ]
    for old_block in modal_variants:
        if old_block in text:
            text = text.replace(old_block, new_children_block, 1)
            break

    text = text.replace(
        "row = [timestamp, discord_seller, seller_habbo, buyer, rank, amount, proof]",
        "row = [discord_seller, seller_habbo, buyer, rank, amount, proof]",
        1,
    )
    text = text.replace(
        '            embed.add_field(name="Seller Habbo", value=seller_habbo, inline=True)',
        '            embed.add_field(name="Server Username", value=discord_seller, inline=True)',
        1,
    )

    text = replace_top_function(text, "clean_rank_sales_rows", '''def clean_rank_sales_rows(values: list[list[str]]) -> list[list[str]]:
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

    text = replace_top_function(text, "aggregate_rank_sales", '''def aggregate_rank_sales(rows: list[list[str]]) -> dict[str, list[object]]:
    totals: dict[str, list[object]] = {}
    for row in rows:
        padded = list(row) + [""] * len(RANK_SALES_HEADERS)
        discord_seller, seller_habbo, _buyer, rank_sold, amount, _proof = padded[:6]
        seller_habbo = clean_text(seller_habbo)
        discord_seller = clean_text(discord_seller)
        key = norm(seller_habbo) or norm(discord_seller)
        if not key:
            continue

        amount_value = amount_to_credits(amount)
        if key not in totals:
            totals[key] = [discord_seller or "N/A", seller_habbo or "N/A", 0, 0.0, rank_sold or "N/A", False]
        record = totals[key]
        record[0] = discord_seller or record[0]
        record[1] = seller_habbo or record[1]
        record[2] = int(record[2]) + 1
        if amount_value is not None:
            record[3] = float(record[3]) + amount_value
            record[5] = True
        record[4] = rank_sold or record[4]
    return totals
''')

    text = replace_top_function(text, "write_rank_seller_totals", '''def write_rank_seller_totals(spreadsheet, raw_rows: list[list[str]]) -> None:
    totals_sheet = get_rank_seller_totals_worksheet(spreadsheet)
    totals = aggregate_rank_sales(raw_rows)
    output = [RANK_SELLER_TOTALS_HEADERS]
    for record in totals.values():
        has_amount = bool(record[5])
        output.append([
            record[0],
            record[1],
            record[2],
            format_credits(float(record[3]) if has_amount else None),
            record[4],
        ])

    totals_sheet.clear()
    totals_sheet.update(range_name="A1", values=output, value_input_option="USER_ENTERED")
    apply_sales_sheet_style(totals_sheet, len(RANK_SELLER_TOTALS_HEADERS))
''')

    text = replace_top_function(text, "update_rank_seller_totals_for_sale", '''def update_rank_seller_totals_for_sale(spreadsheet, sale_row: list[str]) -> None:
    totals_sheet = get_rank_seller_totals_worksheet(spreadsheet)
    values = totals_sheet.get_all_values()
    rows = values[1:] if len(values) > 1 else []

    discord_seller, seller_habbo, _buyer, rank_sold, amount, _proof = (sale_row + [""] * 6)[:6]
    target_habbo = norm(seller_habbo)
    target_discord = norm(discord_seller)
    new_amount = amount_to_credits(amount)

    for index, row in enumerate(rows, start=2):
        padded = list(row) + [""] * len(RANK_SELLER_TOTALS_HEADERS)
        same_habbo = target_habbo and norm(padded[1]) == target_habbo
        same_discord = target_discord and norm(padded[0]) == target_discord
        if not same_habbo and not same_discord:
            continue

        try:
            total_sales = int(float(clean_text(padded[2]) or "0")) + 1
        except ValueError:
            total_sales = 1

        previous_amount = amount_to_credits(padded[3])
        total_amount = None
        if previous_amount is not None or new_amount is not None:
            total_amount = (previous_amount or 0) + (new_amount or 0)

        updated = [
            clean_text(discord_seller) or padded[0] or "N/A",
            clean_text(seller_habbo) or padded[1] or "N/A",
            total_sales,
            format_credits(total_amount),
            clean_text(rank_sold) or padded[4] or "N/A",
        ]
        totals_sheet.update(range_name=f"A{index}:E{index}", values=[updated], value_input_option="USER_ENTERED")
        apply_sales_sheet_style(totals_sheet, len(RANK_SELLER_TOTALS_HEADERS))
        return

    new_row = [
        clean_text(discord_seller) or "N/A",
        clean_text(seller_habbo) or "N/A",
        1,
        format_credits(new_amount),
        clean_text(rank_sold) or "N/A",
    ]
    next_row = max(len(values) + 1, 2)
    totals_sheet.update(range_name=f"A{next_row}:E{next_row}", values=[new_row], value_input_option="USER_ENTERED")
    apply_sales_sheet_style(totals_sheet, len(RANK_SELLER_TOTALS_HEADERS))
''')

    text = text.replace('rank_sales.batch_clear(["H:Z"])', 'rank_sales.batch_clear(["G:Z"])')

    path.write_text(text)
    print("Sale log modal now uses server Discord username automatically.")
    print("Timestamps removed from Rank Sales and Rank Seller Totals.")

import bot
