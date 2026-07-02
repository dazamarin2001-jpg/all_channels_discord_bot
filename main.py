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
    next_listener = text.find("\n\n@bot.listen", start + 1)
    candidates = [pos for pos in (next_command, next_event, next_listener) if pos != -1]
    end = min(candidates) if candidates else len(text)
    return text[:start] + replacement.rstrip() + text[end:]


def upsert_startup_cleanup_listener(text: str, replacement: str) -> str:
    start = text.find("_cleanup_startup_done = False")
    if start == -1:
        start = text.find("_sales_cleanup_done = False")
    if start != -1:
        next_command = text.find("\n\n@bot.tree.command", start + 1)
        next_event = text.find("\n\n@bot.event", start + 1)
        next_listener = text.find("\n\n@bot.listen", start + 1)
        candidates = [pos for pos in (next_command, next_event, next_listener) if pos != -1]
        end = min(candidates) if candidates else len(text)
        return text[:start] + replacement.rstrip() + text[end:]
    marker = '@bot.tree.command(description="Check whether the bot is responding.")\n'
    return text.replace(marker, replacement.rstrip() + "\n\n" + marker, 1)


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

    donation_block = '''DONATIONS_SHEET_NAME = os.getenv("DONATIONS_SHEET_NAME", "Donations")
DONATION_CHANNEL_ID = os.getenv("DONATION_CHANNEL_ID") or os.getenv("DONATIONS_CHANNEL_ID")
DONATIONS_HEADERS = ["Logged By", "Donor Habbo", "Amount", "Proof / Notes"]


def get_donations_worksheet(spreadsheet=None):
    spreadsheet = spreadsheet or get_spreadsheet()
    return get_or_create_worksheet(spreadsheet, DONATIONS_SHEET_NAME, DONATIONS_HEADERS)


def clean_donation_rows(values: list[list[str]]) -> list[list[str]]:
    cleaned = [DONATIONS_HEADERS]
    if not values:
        return cleaned
    for row in values[1:]:
        if not any(str(cell).strip() for cell in row):
            continue
        padded = list(row) + [""] * len(DONATIONS_HEADERS)
        cleaned.append(padded[:len(DONATIONS_HEADERS)])
    return cleaned


def setup_donations_sheet_layout() -> None:
    spreadsheet = get_spreadsheet()
    sheet = get_donations_worksheet(spreadsheet)
    values = sheet.get_all_values()
    cleaned = clean_donation_rows(values)
    sheet.clear()
    sheet.update(range_name="A1", values=cleaned, value_input_option="USER_ENTERED")
    try:
        sheet.batch_clear(["E:Z"])
    except Exception:
        pass
    apply_sales_sheet_style(sheet, len(DONATIONS_HEADERS))


def append_donation_to_sheet(row: list[str]) -> None:
    spreadsheet = get_spreadsheet()
    sheet = get_donations_worksheet(spreadsheet)
    values = sheet.get_all_values()
    current_header = values[0][:len(DONATIONS_HEADERS)] if values else []
    if current_header != DONATIONS_HEADERS:
        setup_donations_sheet_layout()
        spreadsheet = get_spreadsheet()
        sheet = get_donations_worksheet(spreadsheet)
    sheet.append_row(row, value_input_option="USER_ENTERED")
    apply_sales_sheet_style(sheet, len(DONATIONS_HEADERS))


async def get_donation_channel(guild: discord.Guild | None):
    if guild is None or not DONATION_CHANNEL_ID:
        return None
    try:
        channel_id = int(DONATION_CHANNEL_ID)
    except ValueError:
        return None
    channel = guild.get_channel(channel_id) or bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.DiscordException:
            return None
    if isinstance(channel, (discord.TextChannel, discord.Thread)):
        return channel
    return None


class DonationModal(discord.ui.Modal, title="Log Donation"):
    donor = discord.ui.TextInput(label="Donor Habbo Username", placeholder="Example: DonorName", required=True, max_length=80)
    amount = discord.ui.TextInput(label="Donation Amount", placeholder="Example: 50c, 1 GB, HC, furni", required=True, max_length=80)
    proof = discord.ui.TextInput(label="Proof / Notes", placeholder="Paste proof link or add notes", style=discord.TextStyle.paragraph, required=False, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            donor = clean_text(self.donor.value)
            amount = clean_text(self.amount.value)
            proof = clean_text(self.proof.value) or "N/A"
            logged_by = getattr(interaction.user, "nick", None) or getattr(interaction.user, "display_name", interaction.user.name)
            row = [logged_by, donor, amount, proof]
            await asyncio.to_thread(append_donation_to_sheet, row)
            embed = discord.Embed(title="Donation Logged", color=discord.Color.gold(), timestamp=datetime.now(ZoneInfo(TIMEZONE)))
            embed.add_field(name="Logged By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Donor", value=donor, inline=True)
            embed.add_field(name="Amount", value=amount, inline=True)
            embed.add_field(name="Proof / Notes", value=proof, inline=False)
            log_channel = await get_donation_channel(interaction.guild)
            if log_channel is None:
                raise RuntimeError("DONATION_CHANNEL_ID is missing, wrong, or the bot cannot see that channel.")
            await log_channel.send(embed=embed)
            await interaction.followup.send("Donation logged and sent to the donation channel.", ephemeral=True)
        except Exception as exc:
            print(f"Donation logging error: {type(exc).__name__}: {exc}")
            await interaction.followup.send(f"Could not log donation: {type(exc).__name__}: {exc}", ephemeral=True)


@bot.tree.command(name="donate", description="Open a form to log a donation into Google Sheets.")
async def donate(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    if not await member_can_log_sales(interaction):
        await interaction.response.send_message("You do not have permission to log donations.", ephemeral=True)
        return
    if not SPREADSHEET_ID or not GOOGLE_CREDENTIALS_JSON:
        await interaction.response.send_message("Donation logging is not configured yet. Add SPREADSHEET_ID and GOOGLE_CREDENTIALS_JSON in Railway Variables.", ephemeral=True)
        return
    if not DONATION_CHANNEL_ID:
        await interaction.response.send_message("Add DONATION_CHANNEL_ID in Railway Variables first.", ephemeral=True)
        return
    await interaction.response.send_modal(DonationModal())


@bot.tree.command(name="donation-summary", description="Show the top donors based on logged donations.")
async def donation_summary(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        worksheet = get_donations_worksheet()
        values = await asyncio.to_thread(worksheet.get_all_values)
        rows = values[1:] if len(values) > 1 else []
        if not rows:
            await interaction.followup.send("No donations have been logged yet.", ephemeral=True)
            return
        totals: dict[str, list[object]] = {}
        for row in rows:
            padded = list(row) + [""] * len(DONATIONS_HEADERS)
            _logged_by, donor, amount, _proof = padded[:4]
            donor_display = seller_identity_display(donor) or clean_text(donor)
            key = seller_identity_key(donor) or norm(donor)
            if not key:
                continue
            amount_value = amount_to_credits(amount)
            if key not in totals:
                totals[key] = [donor_display or "N/A", 0, 0.0, False]
            totals[key][1] = int(totals[key][1]) + 1
            if amount_value is not None:
                totals[key][2] = float(totals[key][2]) + amount_value
                totals[key][3] = True
        parsed = sorted(totals.values(), key=lambda record: (float(record[2]), int(record[1])), reverse=True)
        lines = []
        for rank_number, record in enumerate(parsed[:10], start=1):
            donor_name, donation_count, total_amount, has_amount = record
            donation_word = "donation" if int(donation_count) == 1 else "donations"
            lines.append(f"{rank_number}.  **{donor_name}**\n— {donation_count} {donation_word} — {format_credits(float(total_amount) if has_amount else None)} total")
        if not lines:
            await interaction.followup.send("No donor names found in the Donations sheet.", ephemeral=True)
            return
        embed = discord.Embed(title="Donation Totals", description="\n".join(lines), color=discord.Color.gold(), timestamp=datetime.now(ZoneInfo(TIMEZONE)))
        embed.set_footer(text="Synced from the Donations sheet")
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as exc:
        print(f"Donation summary error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not load donation summary: {type(exc).__name__}: {exc}", ephemeral=True)


async def can_setup_donations_sheet(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    member = interaction.user
    if not isinstance(member, discord.Member):
        member = await interaction.guild.fetch_member(interaction.user.id)
    if member.guild_permissions.administrator:
        return True
    allowed_roles = {"Chat Moderator", "Rank Seller"}
    return any(role.name in allowed_roles for role in member.roles)


@bot.tree.command(name="setup-donations-sheet", description="Create, clean, and style the Donations Google Sheet tab.")
@app_commands.check(can_setup_donations_sheet)
async def setup_donations_sheet(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await asyncio.to_thread(setup_donations_sheet_layout)
        await interaction.followup.send("Donations sheet tab was created, cleaned, and styled.", ephemeral=True)
    except Exception as exc:
        print(f"Donations sheet setup error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not setup donations sheet: {type(exc).__name__}: {exc}", ephemeral=True)


'''
    if "DONATIONS_SHEET_NAME" not in text:
        text = text.replace("bot.tree.add_command(sale_group)\n", donation_block + "bot.tree.add_command(sale_group)\n", 1)

    cleanup_block = '''CLEANUP_CHANNELS_SHEET_NAME = os.getenv("CLEANUP_CHANNELS_SHEET_NAME", "Cleanup Channels")
CLEANUP_CHANNELS_HEADERS = ["Guild ID", "Channel ID", "Channel Name", "Enabled By"]
EXTRA_CLEANUP_CHANNEL_IDS: set[int] = set()


def get_cleanup_channels_worksheet(spreadsheet=None):
    spreadsheet = spreadsheet or get_spreadsheet()
    return get_or_create_worksheet(spreadsheet, CLEANUP_CHANNELS_SHEET_NAME, CLEANUP_CHANNELS_HEADERS, rows=300)


def get_static_cleanup_channel_ids() -> set[int]:
    ids: set[int] = set()
    raw_values = [os.getenv("AUTO_CLEAN_CHANNEL_ID"), os.getenv("AUTO_CLEAN_CHANNEL_IDS"), RANK_SALES_CHANNEL_ID, globals().get("DONATION_CHANNEL_ID")]
    for raw_value in raw_values:
        if not raw_value:
            continue
        for piece in str(raw_value).replace(";", ",").split(","):
            piece = piece.strip()
            if not piece:
                continue
            try:
                ids.add(int(piece))
            except ValueError:
                pass
    return ids


def get_all_cleanup_channel_ids() -> set[int]:
    return set(EXTRA_CLEANUP_CHANNEL_IDS) | get_static_cleanup_channel_ids()


def load_extra_cleanup_channel_ids_from_sheet() -> set[int]:
    EXTRA_CLEANUP_CHANNEL_IDS.clear()
    try:
        sheet = get_cleanup_channels_worksheet()
        values = sheet.get_all_values()
        for row in values[1:]:
            padded = list(row) + [""] * len(CLEANUP_CHANNELS_HEADERS)
            channel_id = clean_text(padded[1])
            if not channel_id:
                continue
            try:
                EXTRA_CLEANUP_CHANNEL_IDS.add(int(channel_id))
            except ValueError:
                continue
    except Exception as exc:
        print(f"Cleanup channel load warning: {type(exc).__name__}: {exc}")
    return set(EXTRA_CLEANUP_CHANNEL_IDS)


def save_cleanup_channel_to_sheet(guild_id: int, channel_id: int, channel_name: str, enabled_by: str) -> None:
    sheet = get_cleanup_channels_worksheet()
    values = sheet.get_all_values()
    row_values = [str(guild_id), str(channel_id), channel_name, enabled_by]
    for index, row in enumerate(values[1:], start=2):
        padded = list(row) + [""] * len(CLEANUP_CHANNELS_HEADERS)
        if clean_text(padded[1]) == str(channel_id):
            sheet.update(range_name=f"A{index}:D{index}", values=[row_values], value_input_option="USER_ENTERED")
            EXTRA_CLEANUP_CHANNEL_IDS.add(channel_id)
            apply_sales_sheet_style(sheet, len(CLEANUP_CHANNELS_HEADERS))
            return
    sheet.append_row(row_values, value_input_option="USER_ENTERED")
    EXTRA_CLEANUP_CHANNEL_IDS.add(channel_id)
    apply_sales_sheet_style(sheet, len(CLEANUP_CHANNELS_HEADERS))


def remove_cleanup_channel_from_sheet(channel_id: int) -> bool:
    removed = False
    try:
        sheet = get_cleanup_channels_worksheet()
        values = sheet.get_all_values()
        for index in range(len(values), 1, -1):
            row = values[index - 1]
            padded = list(row) + [""] * len(CLEANUP_CHANNELS_HEADERS)
            if clean_text(padded[1]) == str(channel_id):
                sheet.delete_rows(index)
                removed = True
        apply_sales_sheet_style(sheet, len(CLEANUP_CHANNELS_HEADERS))
    finally:
        EXTRA_CLEANUP_CHANNEL_IDS.discard(channel_id)
    return removed


def is_cleanup_log_message(candidate: discord.Message) -> bool:
    return bool(candidate.embeds) and (candidate.author.bot or candidate.webhook_id is not None)


async def cleanup_existing_non_logs_in_channel(channel, history_limit: int | None = None) -> int:
    if history_limit is None:
        history_limit_raw = os.getenv("AUTO_CLEAN_HISTORY_LIMIT", "500")
        try:
            history_limit = max(1, min(int(history_limit_raw), 2000))
        except ValueError:
            history_limit = 500
    deleted = 0
    async for message in channel.history(limit=history_limit):
        if getattr(message, "pinned", False):
            continue
        if is_cleanup_log_message(message):
            continue
        try:
            await message.delete()
            deleted += 1
            await asyncio.sleep(0.25)
        except (discord.NotFound, discord.Forbidden):
            continue
        except discord.HTTPException as exc:
            print(f"Cleanup failed on old message: {type(exc).__name__}: {exc}")
            await asyncio.sleep(1)
    return deleted


async def can_manage_cleanup(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    member = interaction.user
    if not isinstance(member, discord.Member):
        member = await interaction.guild.fetch_member(interaction.user.id)
    return member.guild_permissions.administrator or member.guild_permissions.manage_messages


cleanup_group = app_commands.Group(name="cleanup", description="Clean-up crew channel tools.")


@cleanup_group.command(name="enable", description="Enable clean-up crew in this channel or another channel.")
@app_commands.describe(channel="Channel to clean. Leave empty to use this channel.")
@app_commands.check(can_manage_cleanup)
async def cleanup_enable(interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    target = channel or interaction.channel
    if not isinstance(target, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("Use this in a text channel or pick a text channel.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    enabled_by = getattr(interaction.user, "display_name", interaction.user.name)
    try:
        await asyncio.to_thread(save_cleanup_channel_to_sheet, interaction.guild.id, target.id, target.name, enabled_by)
        deleted = await cleanup_existing_non_logs_in_channel(target)
        await interaction.followup.send(f"🧹 Clean-up crew enabled in {target.mention}. I also removed {deleted} old non-log message(s).", ephemeral=True)
    except Exception as exc:
        print(f"Cleanup enable error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not enable cleanup: {type(exc).__name__}: {exc}", ephemeral=True)


@cleanup_group.command(name="disable", description="Disable clean-up crew in this channel or another channel.")
@app_commands.describe(channel="Channel to stop cleaning. Leave empty to use this channel.")
@app_commands.check(can_manage_cleanup)
async def cleanup_disable(interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
    target = channel or interaction.channel
    if not isinstance(target, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("Use this in a text channel or pick a text channel.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        removed = await asyncio.to_thread(remove_cleanup_channel_from_sheet, target.id)
        if target.id in get_static_cleanup_channel_ids():
            await interaction.followup.send(f"{target.mention} is still cleaned because it is set in Railway Variables. Remove it from the variable to fully disable it.", ephemeral=True)
        elif removed:
            await interaction.followup.send(f"🧹 Clean-up crew disabled in {target.mention}.", ephemeral=True)
        else:
            await interaction.followup.send(f"Clean-up crew was not enabled in {target.mention}.", ephemeral=True)
    except Exception as exc:
        print(f"Cleanup disable error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not disable cleanup: {type(exc).__name__}: {exc}", ephemeral=True)


@cleanup_group.command(name="list", description="List channels where clean-up crew is enabled.")
@app_commands.check(can_manage_cleanup)
async def cleanup_list(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await asyncio.to_thread(load_extra_cleanup_channel_ids_from_sheet)
        ids = sorted(get_all_cleanup_channel_ids())
        if not ids:
            await interaction.followup.send("No cleanup channels are enabled yet.", ephemeral=True)
            return
        lines = []
        for channel_id in ids[:25]:
            channel = interaction.guild.get_channel(channel_id) if interaction.guild else None
            lines.append(channel.mention if channel else f"`{channel_id}`")
        await interaction.followup.send("🧹 Clean-up crew is enabled in:\n" + "\n".join(lines), ephemeral=True)
    except Exception as exc:
        print(f"Cleanup list error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not list cleanup channels: {type(exc).__name__}: {exc}", ephemeral=True)


'''
    if "cleanup_group = app_commands.Group" not in text:
        text = text.replace("bot.tree.add_command(sale_group)\n", cleanup_block + "bot.tree.add_command(sale_group)\n", 1)
    if "bot.tree.add_command(cleanup_group)" not in text:
        text = text.replace("bot.tree.add_command(sale_group)\n", "bot.tree.add_command(sale_group)\nbot.tree.add_command(cleanup_group)\n", 1)

    auto_clean_event = '''@bot.event
async def on_message(message: discord.Message) -> None:
    if message.guild is None:
        return

    cleanup_ids = get_all_cleanup_channel_ids() if "get_all_cleanup_channel_ids" in globals() else set()
    if message.channel.id not in cleanup_ids:
        return
    if getattr(message, "pinned", False):
        return
    if is_cleanup_log_message(message):
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
        if is_cleanup_log_message(current_message) or getattr(current_message, "pinned", False):
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

    startup_cleanup_listener = '''_cleanup_startup_done = False


@bot.listen("on_ready")
async def clean_existing_cleanup_channel_messages() -> None:
    global _cleanup_startup_done
    if _cleanup_startup_done:
        return
    _cleanup_startup_done = True

    await asyncio.to_thread(load_extra_cleanup_channel_ids_from_sheet)
    cleanup_ids = get_all_cleanup_channel_ids()
    if not cleanup_ids:
        return

    for cleanup_channel_id in cleanup_ids:
        channel = bot.get_channel(cleanup_channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(cleanup_channel_id)
            except discord.HTTPException:
                continue
        if not hasattr(channel, "history"):
            continue
        deleted = await cleanup_existing_non_logs_in_channel(channel)
        if deleted:
            print(f"Startup cleanup deleted {deleted} old non-log message(s) from channel {cleanup_channel_id}.")


'''
    text = upsert_startup_cleanup_listener(text, startup_cleanup_listener)

    path.write_text(text)
    print("Sale log modal now uses server Discord username automatically.")
    print("Timestamps removed from Rank Sales and Rank Seller Totals.")
    print("Similar seller names are merged before totals are built.")
    print("Donation logging command and Donations sheet tab enabled.")
    print("Cleanup crew channel commands enabled.")

import bot
