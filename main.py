from pathlib import Path

path = Path("bot.py")
if path.exists():
    text = path.read_text()

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
    old_children_block = '''            seller_habbo = clean_text(self.children[0].value)
            buyer = clean_text(self.children[1].value)
            rank = clean_text(self.children[2].value)
            amount = clean_text(self.children[3].value)
            proof = clean_text(self.children[4].value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
'''
    new_children_block = '''            buyer = clean_text(self.children[0].value)
            rank = clean_text(self.children[1].value)
            amount = clean_text(self.children[2].value)
            proof = clean_text(self.children[3].value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
            seller_habbo = discord_seller
'''
    text = text.replace(old_children_block, new_children_block, 1)

    old_named_block = '''            seller_habbo = clean_text(self.seller_habbo.value)
            buyer = clean_text(self.buyer.value)
            rank = clean_text(self.rank.value)
            amount = clean_text(self.amount.value)
            proof = clean_text(self.proof.value) or "N/A"
            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")
            discord_seller = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
'''
    text = text.replace(old_named_block, new_children_block, 1)

    text = text.replace(
        '            embed.add_field(name="Seller Habbo", value=seller_habbo, inline=True)',
        '            embed.add_field(name="Server Username", value=discord_seller, inline=True)',
        1,
    )

    # Make new rows in Rank Seller Totals write directly into A:F.
    # This prevents Google Sheets from appending the totals row into G:K when stray formulas/cells exist.
    old_append_totals = '''    totals_sheet.append_row(new_row, value_input_option="USER_ENTERED")
    apply_sales_sheet_style(totals_sheet, len(RANK_SELLER_TOTALS_HEADERS))'''
    new_append_totals = '''    next_row = max(len(values) + 1, 2)
    totals_sheet.update(range_name=f"A{next_row}:F{next_row}", values=[new_row], value_input_option="USER_ENTERED")
    apply_sales_sheet_style(totals_sheet, len(RANK_SELLER_TOTALS_HEADERS))'''
    text = text.replace(old_append_totals, new_append_totals, 1)

    path.write_text(text)
    print("Sale log modal now uses server Discord username automatically.")
    print("Rank Seller Totals now writes new sellers into A:F.")

import bot
