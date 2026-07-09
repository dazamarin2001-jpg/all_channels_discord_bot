# Railway entrypoint for the Discord bot.
#
# Adds optional generated commands safely without touching the rank-sale modal.
# It removes previously injected generated blocks first, so runtime injections can
# repair themselves on the next deploy/restart.

from pathlib import Path

DONATION_START_MARKER = "# ---- Donation commands ----"
DONATION_END_MARKER = "# ---- End donation commands ----"
CLEANUP_START_MARKER = "# ---- Cleanup crew commands ----"
CLEANUP_END_MARKER = "# ---- End cleanup crew commands ----"
TRADE_START_MARKER = "# ---- Trade commands ----"
TRADE_END_MARKER = "# ---- End trade commands ----"

DONATION_BLOCK = r"""
# ---- Donation commands ----
DONATIONS_SHEET_NAME = os.getenv("DONATIONS_SHEET_NAME", "Donations")
DONATION_CHANNEL_ID = os.getenv("DONATION_CHANNEL_ID") or os.getenv("DONATIONS_CHANNEL_ID")
DONATIONS_HEADERS = ["Logged By", "Donor Habbo", "Amount", "Proof / Notes"]


def get_donations_worksheet(spreadsheet=None):
    spreadsheet = spreadsheet or get_spreadsheet()
    return get_or_create_worksheet(spreadsheet, DONATIONS_SHEET_NAME, DONATIONS_HEADERS)


def setup_donations_sheet_layout() -> None:
    spreadsheet = get_spreadsheet()
    sheet = get_donations_worksheet(spreadsheet)
    values = sheet.get_all_values()
    cleaned = [DONATIONS_HEADERS]
    if values:
        for row in values[1:]:
            if any(str(cell).strip() for cell in row):
                padded = list(row) + [""] * len(DONATIONS_HEADERS)
                cleaned.append(padded[:len(DONATIONS_HEADERS)])
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
            logged_by = member_display_name(interaction.user)
            await asyncio.to_thread(append_donation_to_sheet, [logged_by, donor, amount, proof])

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


@bot.tree.command(name="setup-donations-sheet", description="Create, clean, and style the Donations Google Sheet tab.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_donations_sheet(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await asyncio.to_thread(setup_donations_sheet_layout)
        await interaction.followup.send("Donations sheet tab was created, cleaned, and styled.", ephemeral=True)
    except Exception as exc:
        print(f"Donations sheet setup error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not setup donations sheet: {type(exc).__name__}: {exc}", ephemeral=True)
# ---- End donation commands ----
"""

CLEANUP_BLOCK = r"""
# ---- Cleanup crew commands ----
CLEANUP_CHANNELS_FILE = os.getenv("CLEANUP_CHANNELS_FILE", "cleanup_channels.json")
EXTRA_CLEANUP_CHANNEL_IDS: set[int] = set()
CLEANUP_DELETE_DELAY_SECONDS = 120


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


def load_extra_cleanup_channel_ids_from_file() -> set[int]:
    EXTRA_CLEANUP_CHANNEL_IDS.clear()
    if not os.path.exists(CLEANUP_CHANNELS_FILE):
        return set(EXTRA_CLEANUP_CHANNEL_IDS)
    try:
        with open(CLEANUP_CHANNELS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        for entry in data.get("channels", []):
            try:
                EXTRA_CLEANUP_CHANNEL_IDS.add(int(entry.get("channel_id")))
            except (TypeError, ValueError):
                continue
    except Exception as exc:
        print(f"Cleanup channel file warning: {type(exc).__name__}: {exc}")
    return set(EXTRA_CLEANUP_CHANNEL_IDS)


def save_extra_cleanup_channels_to_file() -> None:
    payload = {"channels": [{"channel_id": str(channel_id)} for channel_id in sorted(EXTRA_CLEANUP_CHANNEL_IDS)]}
    with open(CLEANUP_CHANNELS_FILE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def get_all_cleanup_channel_ids() -> set[int]:
    return set(EXTRA_CLEANUP_CHANNEL_IDS) | get_static_cleanup_channel_ids()


def add_cleanup_channel(channel_id: int) -> None:
    load_extra_cleanup_channel_ids_from_file()
    EXTRA_CLEANUP_CHANNEL_IDS.add(channel_id)
    save_extra_cleanup_channels_to_file()


def remove_cleanup_channel(channel_id: int) -> bool:
    load_extra_cleanup_channel_ids_from_file()
    existed = channel_id in EXTRA_CLEANUP_CHANNEL_IDS
    EXTRA_CLEANUP_CHANNEL_IDS.discard(channel_id)
    save_extra_cleanup_channels_to_file()
    return existed


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
        if getattr(message, "pinned", False) or is_cleanup_log_message(message):
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
    try:
        await asyncio.to_thread(add_cleanup_channel, target.id)
        deleted = await cleanup_existing_non_logs_in_channel(target)
        await interaction.followup.send(f"🧹 Clean-up crew enabled in {target.mention}. I also removed {deleted} old non-log message(s).", ephemeral=True)
    except Exception as exc:
        print(f"Cleanup enable error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not enable cleanup: {type(exc).__name__}: {exc}", ephemeral=True)


@cleanup_group.command(name="disable", description="Disable clean-up crew in this channel or another channel.")
@app_commands.describe(channel="Channel to stop cleaning. Leave empty to use this channel.")
@app_commands.check(can_manage_cleanup)
async def cleanup_disable(interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    target = channel or interaction.channel
    if not isinstance(target, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("Use this in a text channel or pick a text channel.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        removed = await asyncio.to_thread(remove_cleanup_channel, target.id)
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
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await asyncio.to_thread(load_extra_cleanup_channel_ids_from_file)
        ids = sorted(get_all_cleanup_channel_ids())
        if not ids:
            await interaction.followup.send("No cleanup channels are enabled yet.", ephemeral=True)
            return
        lines = []
        for channel_id in ids[:25]:
            channel = interaction.guild.get_channel(channel_id)
            lines.append(channel.mention if channel else f"`{channel_id}`")
        await interaction.followup.send("🧹 Clean-up crew is enabled in:\n" + "\n".join(lines), ephemeral=True)
    except Exception as exc:
        print(f"Cleanup list error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not list cleanup channels: {type(exc).__name__}: {exc}", ephemeral=True)


@bot.listen("on_message")
async def auto_cleanup_on_message(message: discord.Message) -> None:
    if message.guild is None:
        return
    await asyncio.to_thread(load_extra_cleanup_channel_ids_from_file)
    if message.channel.id not in get_all_cleanup_channel_ids():
        return
    if getattr(message, "pinned", False) or is_cleanup_log_message(message):
        return

    warning = None
    if not message.author.bot and message.webhook_id is None:
        try:
            warning = await message.channel.send("🧹 **Clean-up crew is here!** This channel is for logs only. Non-log messages will be swept away in **2 minutes**.")
        except discord.HTTPException:
            warning = None

    await asyncio.sleep(CLEANUP_DELETE_DELAY_SECONDS)
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


_cleanup_startup_done = False


@bot.listen("on_ready")
async def clean_existing_cleanup_channel_messages() -> None:
    global _cleanup_startup_done
    if _cleanup_startup_done:
        return
    _cleanup_startup_done = True
    await asyncio.to_thread(load_extra_cleanup_channel_ids_from_file)
    for cleanup_channel_id in get_all_cleanup_channel_ids():
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


bot.tree.add_command(cleanup_group)
# ---- End cleanup crew commands ----
"""

TRADE_BLOCK = r"""
# ---- Trade commands ----
TRADE_SUMMARY_SHEET_NAME = os.getenv("TRADE_SUMMARY_SHEET_NAME", "Summary Log")
TRADE_SUMMARY_HEADERS = ["Account", "Category", "Action", "Change", "Traded To", "Status"]
TRADE_ALLOWED_ROLE_NAMES = {"rank sellers", "rank seller", "chat moderator"}


def protect_sheet_value(value: object) -> str:
    text = clean_text(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def get_trade_summary_worksheet(spreadsheet=None):
    spreadsheet = spreadsheet or get_spreadsheet()
    return get_or_create_worksheet(spreadsheet, TRADE_SUMMARY_SHEET_NAME, TRADE_SUMMARY_HEADERS)


def setup_trade_summary_sheet_layout() -> None:
    spreadsheet = get_spreadsheet()
    sheet = get_trade_summary_worksheet(spreadsheet)
    values = sheet.get_all_values()
    if not values or values[0][:len(TRADE_SUMMARY_HEADERS)] != TRADE_SUMMARY_HEADERS:
        sheet.update(range_name="A1", values=[TRADE_SUMMARY_HEADERS], value_input_option="USER_ENTERED")
    apply_sales_sheet_style(sheet, len(TRADE_SUMMARY_HEADERS))


def read_trade_account_balance(spreadsheet, account: str) -> tuple[object, int, float]:
    totals_sheet = get_rank_seller_totals_worksheet(spreadsheet)
    values = totals_sheet.get_all_values()
    target_account = norm(account)

    for index, row in enumerate(values[1:] if len(values) > 1 else [], start=2):
        padded = list(row) + [""] * len(RANK_SELLER_TOTALS_HEADERS)
        if norm(padded[0]) != target_account:
            continue
        current_balance = amount_to_credits(padded[3]) or 0.0
        return totals_sheet, index, current_balance

    raise RuntimeError(f"No Rank Seller Totals row was found for {account}. Log a sale first, then try /trade again.")


def apply_trade_to_sales_summary(account: str, amount: float) -> tuple[str, str]:
    spreadsheet = get_spreadsheet()
    totals_sheet, row_index, current_balance = read_trade_account_balance(spreadsheet, account)

    if current_balance < amount:
        raise RuntimeError(f"{account} only has {format_credits(current_balance)} available.")

    new_balance = current_balance - amount
    totals_sheet.update(
        range_name=f"D{row_index}:D{row_index}",
        values=[[format_credits(new_balance)]],
        value_input_option="USER_ENTERED",
    )
    apply_sales_sheet_style(totals_sheet, len(RANK_SELLER_TOTALS_HEADERS))
    return format_credits(current_balance), format_credits(new_balance)


def append_trade_to_summary_log(row: list[object]) -> None:
    spreadsheet = get_spreadsheet()
    sheet = get_trade_summary_worksheet(spreadsheet)
    values = sheet.get_all_values()
    if not values or values[0][:len(TRADE_SUMMARY_HEADERS)] != TRADE_SUMMARY_HEADERS:
        setup_trade_summary_sheet_layout()
        spreadsheet = get_spreadsheet()
        sheet = get_trade_summary_worksheet(spreadsheet)
    sheet.append_row(row, value_input_option="USER_ENTERED")
    apply_sales_sheet_style(sheet, len(TRADE_SUMMARY_HEADERS))


async def member_can_trade(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    member = interaction.user
    if not isinstance(member, discord.Member):
        member = await interaction.guild.fetch_member(interaction.user.id)
    return any(role.name.casefold() in TRADE_ALLOWED_ROLE_NAMES for role in member.roles)


class TradeModal(discord.ui.Modal, title="Log Trade"):
    amount = discord.ui.TextInput(
        label="Amount",
        placeholder="Example: 700 or 1 GB",
        required=True,
        max_length=60,
    )
    category = discord.ui.TextInput(
        label="Donation/Sale",
        placeholder="Type Donation or Sale",
        required=True,
        max_length=20,
    )
    traded_to = discord.ui.TextInput(
        label="Traded To",
        placeholder="Example: FSA-Finance",
        required=True,
        max_length=80,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            account = member_display_name(interaction.user)
            amount_text = clean_text(self.amount.value)
            amount_value = amount_to_credits(amount_text)

            if amount_value is None or amount_value <= 0:
                await interaction.followup.send("Amount must be a valid number. Example: `700` or `1 GB`.", ephemeral=True)
                return

            category = clean_text(self.category.value).title()
            if category.casefold() not in {"sale", "donation"}:
                await interaction.followup.send("Donation/Sale must be either `Donation` or `Sale`.", ephemeral=True)
                return

            traded_to = protect_sheet_value(self.traded_to.value)
            negative_change = -int(amount_value) if float(amount_value).is_integer() else -amount_value

            old_balance, new_balance = await asyncio.to_thread(apply_trade_to_sales_summary, account, amount_value)
            await asyncio.to_thread(
                append_trade_to_summary_log,
                [account, category, "Trade Out", negative_change, traded_to, "Completed"],
            )

            embed = discord.Embed(
                title="Trade Logged",
                color=discord.Color.green(),
                timestamp=datetime.now(ZoneInfo(TIMEZONE)),
            )
            embed.add_field(name="Account", value=interaction.user.mention, inline=True)
            embed.add_field(name="Category", value=category, inline=True)
            embed.add_field(name="Amount", value=format_credits(amount_value), inline=True)
            embed.add_field(name="Traded To", value=traded_to, inline=True)
            embed.add_field(name="Previous Balance", value=old_balance, inline=True)
            embed.add_field(name="New Balance", value=new_balance, inline=True)
            embed.set_footer(text="Logged to Summary Log and applied to /sale summary totals.")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as exc:
            print(f"Trade logging error: {type(exc).__name__}: {exc}")
            await interaction.followup.send(f"Could not log trade: {type(exc).__name__}: {exc}", ephemeral=True)


@bot.tree.command(name="trade", description="Open a form to log a trade.")
async def trade(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    if not await member_can_trade(interaction):
        await interaction.response.send_message("You do not have permission to use /trade.", ephemeral=True)
        return
    if not SPREADSHEET_ID or not GOOGLE_CREDENTIALS_JSON:
        await interaction.response.send_message("Trade logging is not configured yet. Add SPREADSHEET_ID and GOOGLE_CREDENTIALS_JSON in Railway Variables.", ephemeral=True)
        return
    await interaction.response.send_modal(TradeModal())
# ---- End trade commands ----
"""


def remove_marked_block(text: str, start_marker: str, end_marker: str) -> str:
    while start_marker in text:
        start = text.find(start_marker)
        block_start = text.rfind("\n", 0, start)
        if block_start == -1:
            block_start = start
        end = text.find(end_marker, start)
        if end == -1:
            run_marker = "bot.run(TOKEN)"
            run_pos = text.find(run_marker, start)
            if run_pos == -1:
                return text[:block_start].rstrip() + "\n"
            text = text[:block_start].rstrip() + "\n\n" + text[run_pos:]
            continue
        line_end = text.find("\n", end + len(end_marker))
        if line_end == -1:
            line_end = len(text)
        text = text[:block_start].rstrip() + "\n" + text[line_end:].lstrip("\n")
    return text


path = Path("bot.py")
if path.exists():
    text = path.read_text(encoding="utf-8")
    text = remove_marked_block(text, DONATION_START_MARKER, DONATION_END_MARKER)
    text = remove_marked_block(text, CLEANUP_START_MARKER, CLEANUP_END_MARKER)
    text = remove_marked_block(text, TRADE_START_MARKER, TRADE_END_MARKER)

    marker = "\n\nbot.run(TOKEN)"
    if marker in text:
        injected = DONATION_BLOCK.strip() + "\n\n" + CLEANUP_BLOCK.strip() + "\n\n" + TRADE_BLOCK.strip()
        text = text.replace(marker, "\n\n" + injected + marker, 1)
        path.write_text(text, encoding="utf-8")
        print("Donation, cleanup, and trade commands injected into bot.py.")
    else:
        print("Generated command warning: could not find bot.run(TOKEN) marker.")

import bot
