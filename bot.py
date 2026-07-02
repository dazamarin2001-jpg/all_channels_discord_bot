import asyncio
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
import gspread
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")

RANK_SALES_CHANNEL_ID = os.getenv("RANK_SALES_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID")
SALES_ROLE_ID = os.getenv("SALES_ROLE_ID")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID") or os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
RANK_SALES_SHEET_NAME = os.getenv("RANK_SALES_SHEET_NAME", "Rank Sales")
TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")

RANK_SALES_HEADERS = [
    "Timestamp",
    "Discord Seller",
    "Seller Habbo",
    "Buyer",
    "Rank Sold",
    "Amount",
    "Proof / Notes",
]

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing in Railway Variables.")

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.synced_commands_once = False

STAFF_ROLE_NAMES = (
    "Founder", "Foundation Advisor", "Supreme Command", "Elite Command",
    "Trial Moderation", "Administrator", "Moderator", "Staff"
)

AGENCY_ROLES = [
    "Founder", "Foundation Advisor", "Supreme Command", "Elite Command",
    "Trial Moderation", "Legend", "Supreme Donator", "Emerald Donator",
    "Administrator", "Moderator", "Staff", "Support", "Member", "Bot"
]

HIERARCHY_ROLES = [
    ("Founder", discord.Permissions(administrator=True)),
    ("Foundation Advisor", discord.Permissions(administrator=True)),
    ("Supreme Command", discord.Permissions(administrator=True)),
    ("Elite Command", discord.Permissions(manage_guild=True, manage_roles=True, manage_channels=True, kick_members=True, ban_members=True, manage_messages=True, moderate_members=True)),
    ("Trial Moderation", discord.Permissions(kick_members=True, manage_messages=True, moderate_members=True)),
    ("Administrator", discord.Permissions(administrator=True)),
    ("Moderator", discord.Permissions(kick_members=True, manage_messages=True, moderate_members=True)),
    ("Staff", discord.Permissions(manage_messages=True, moderate_members=True)),
    ("Support", discord.Permissions(manage_threads=True, manage_messages=True)),
    ("Legend", discord.Permissions(view_channel=True, send_messages=True, read_message_history=True)),
    ("Supreme Donator", discord.Permissions(view_channel=True, send_messages=True, read_message_history=True)),
    ("Emerald Donator", discord.Permissions(view_channel=True, send_messages=True, read_message_history=True)),
    ("Member", discord.Permissions(view_channel=True, send_messages=True, read_message_history=True)),
    ("Muted", discord.Permissions(view_channel=True, read_message_history=True)),
]

AGENCY_CHANNELS = {
    "START HERE": [
        ("📜︱server-rules", "text"),
        ("find-channel", "text"),
        ("Server Members: 0", "voice"),
        ("Staff Members: 0", "voice"),
        ("Boost tier: 0", "voice"),
    ],
    "📣 ANNOUNCEMENTS": [
        ("📣︱staff-announcements", "text"),
        ("📣︱code-of-conduct-announcements", "text"),
        ("📣︱staff-updates", "text"),
        ("📣︱pay-announcements", "text"),
        ("📣︱event-announcements", "text"),
        ("📣︱broadcasting-announcements", "text"),
        ("📣︱donation-shoutout", "text"),
        ("📋︱applications-and-quizzes", "text"),
        ("📰︱blog-updates", "text"),
        ("💕︱compliments-and-confessions", "text"),
        ("🎁︱giveaways", "text"),
        ("📊︱polls", "text"),
        ("𝕏︱twitter", "text"),
    ],
    "💬 SOCIAL CHATS": [("🚀︱nitro-boosters", "text")],
    "HELP DESK": [
        ("🏷️︱role-request-plats", "text"),
        ("✅︱reaction-roles", "text"),
        ("📑︱name-change-request", "text"),
        ("📑︱requests", "text"),
        ("❓︱questions", "text"),
        ("⚙️︱report-a-bug-or-issue", "text"),
        ("💡︱suggestions", "text"),
        ("💡︱suggestions-feedback", "text"),
        ("🎂︱birthday-set", "text"),
    ],
    "💬 ELECTIVE CHATS": [
        ("『💬』elective-general", "text"),
        ("『✍️』elective-point-vouch", "text"),
        ("『📋』elective-task-requests", "text"),
        ("『🗂️』elective-task-management", "text"),
        ("『🧸』founders-reps", "text"),
        ("『🟣』ownership", "text"),
        ("『🔵』presidential-chat", "text"),
        ("『🔴』supreme-command", "text"),
        ("『⚪』elite-command", "text"),
        ("『🟡』elective-internship", "text"),
        ("『✍️』elec-intern-point-vouch", "text"),
        ("『🏆』special-division-leaders", "text"),
        ("『⚫』moderation-5ic", "text"),
        ("『✍️』moderation-point-vouch", "text"),
    ],
    "SHARE WITH THE CLASS": [
        ("🍔︱food", "text"),
        ("🐸︱pet-pics", "text"),
        ("✈️︱travel-pics", "text"),
        ("📸︱selfie-channel", "text"),
        ("🤣︱best-memes", "text"),
        ("🎮︱gamers-corner", "text"),
        ("📱︱tiktoks", "text"),
    ],
}

SIMPLE_ROLES = ["Administrator", "Moderator", "Staff", "Support", "Member", "Bot"]
SIMPLE_CHANNELS = {
    "START HERE": [("welcome", "text"), ("rules", "text"), ("announcements", "text")],
    "COMMUNITY": [("general", "text"), ("media", "text"), ("suggestions", "text")],
    "SUPPORT": [("open-a-ticket", "text"), ("questions", "text")],
    "STAFF": [("staff-chat", "text"), ("mod-logs", "text")],
}

OLD_LAYOUT_CATEGORIES = {
    "COMMUNITY", "GAMING", "SUPPORT", "STAFF", "INFORMATION", "CLIENT AREA",
    "About Us", "┌──── Information ────┐", "┌──── Support ────┐",
    "┌──── Chat ────┐", "┌──── Staff ────┐",
}

READ_ONLY_MARKERS = (
    "rules", "announcements", "updates", "pay-announcements", "event-announcements",
    "broadcasting-announcements", "donation-shoutout", "applications-and-quizzes",
    "blog-updates", "giveaways", "polls", "twitter", "reaction-roles", "birthday-set"
)

STAFF_MARKERS = (
    "staff", "elective", "ownership", "presidential-chat", "supreme-command",
    "elite-command", "founders-reps", "special-division-leaders", "moderation-5ic"
)


class RankSaleModal(discord.ui.Modal, title="Log Rank Sale"):
    seller_habbo = discord.ui.TextInput(
        label="Seller Habbo Username",
        placeholder="Example: Dazamarin",
        required=True,
        max_length=80,
    )
    buyer = discord.ui.TextInput(
        label="Buyer Habbo Username",
        placeholder="Example: BuyerName",
        required=True,
        max_length=80,
    )
    rank = discord.ui.TextInput(
        label="Rank Sold",
        placeholder="Example: Trial iC, Senior Management, etc.",
        required=True,
        max_length=100,
    )
    amount = discord.ui.TextInput(
        label="Amount Paid",
        placeholder="Example: 50c, 100c, 1 GB",
        required=True,
        max_length=60,
    )
    proof = discord.ui.TextInput(
        label="Proof / Notes",
        placeholder="Paste proof link or add notes",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            seller_habbo = str(self.seller_habbo.value).strip()
            buyer = str(self.buyer.value).strip()
            rank = str(self.rank.value).strip()
            amount = str(self.amount.value).strip()
            proof = str(self.proof.value).strip() or "N/A"

            timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %I:%M %p %Z")

            row = [
                timestamp,
                getattr(interaction.user, "display_name", interaction.user.name),
                seller_habbo,
                buyer,
                rank,
                amount,
                proof,
            ]

            await asyncio.to_thread(append_rank_sale_to_sheet, row)

            embed = discord.Embed(
                title="Rank Sale Logged",
                color=discord.Color.green(),
                timestamp=datetime.now(ZoneInfo(TIMEZONE)),
            )
            embed.add_field(name="Discord Seller", value=interaction.user.mention, inline=True)
            embed.add_field(name="Seller Habbo", value=seller_habbo, inline=True)
            embed.add_field(name="Buyer", value=buyer, inline=True)
            embed.add_field(name="Rank Sold", value=rank, inline=True)
            embed.add_field(name="Amount", value=amount, inline=True)
            embed.add_field(name="Proof / Notes", value=proof, inline=False)

            log_channel = await get_rank_sales_channel(interaction.guild)
            if log_channel is None:
                raise RuntimeError("RANK_SALES_CHANNEL_ID is missing, wrong, or the bot cannot see that channel.")
            await log_channel.send(embed=embed)

            await interaction.followup.send("Rank sale logged successfully.", ephemeral=True)
        except Exception as exc:
            print(f"Rank sale logging error: {type(exc).__name__}: {exc}")
            await interaction.followup.send(
                f"Could not log the rank sale: {type(exc).__name__}: {exc}",
                ephemeral=True,
            )


def staff_roles(guild: discord.Guild) -> list[discord.Role]:
    return [role for role in guild.roles if role.name in STAFF_ROLE_NAMES]


def is_staff_area(category_name: str, channel_name: str = "") -> bool:
    text = f"{category_name} {channel_name}".casefold()
    return any(marker in text for marker in STAFF_MARKERS)


def is_read_only(channel_name: str) -> bool:
    lowered = channel_name.casefold()
    return any(marker in lowered for marker in READ_ONLY_MARKERS)


def is_counter(channel_name: str) -> bool:
    lowered = channel_name.casefold()
    return lowered.startswith("server members:") or lowered.startswith("staff members:") or lowered.startswith("boost tier:")


def staff_channel_overwrites(guild: discord.Guild) -> dict:
    overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    for role in staff_roles(guild):
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, connect=True, speak=True
        )
    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, connect=True, speak=True
        )
    return overwrites


def readonly_overwrites(guild: discord.Guild) -> dict:
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True, send_messages=False, read_message_history=True
        )
    }
    for role in staff_roles(guild):
        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    return overwrites


def counter_overwrites(guild: discord.Guild) -> dict:
    return {guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False)}


def get_overwrites(guild: discord.Guild, category_name: str, channel_name: str, channel_type: str) -> dict | None:
    if channel_type == "voice" and is_counter(channel_name):
        return counter_overwrites(guild)
    if is_staff_area(category_name, channel_name):
        return staff_channel_overwrites(guild)
    if is_read_only(channel_name):
        return readonly_overwrites(guild)
    return None


def get_rank_sales_worksheet():
    if not GOOGLE_CREDENTIALS_JSON:
        raise RuntimeError("GOOGLE_CREDENTIALS_JSON is missing in Railway Variables.")
    if not SPREADSHEET_ID:
        raise RuntimeError("SPREADSHEET_ID is missing in Railway Variables.")

    credentials_info = json.loads(GOOGLE_CREDENTIALS_JSON)
    credentials = Credentials.from_service_account_info(credentials_info, scopes=GOOGLE_SCOPES)
    sheets_client = gspread.authorize(credentials)
    spreadsheet = sheets_client.open_by_key(SPREADSHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(RANK_SALES_SHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=RANK_SALES_SHEET_NAME, rows=1000, cols=len(RANK_SALES_HEADERS))

    return worksheet


def clean_rank_sales_rows(values: list[list[str]]) -> list[list[str]]:
    cleaned = [RANK_SALES_HEADERS]
    if not values:
        return cleaned

    old_header = [cell.strip().casefold() for cell in values[0]]
    has_old_private_columns = "seller id" in old_header or "channel id" in old_header or "channel" in old_header

    for row in values[1:]:
        if not any(str(cell).strip() for cell in row):
            continue

        padded = list(row) + [""] * 12
        if has_old_private_columns:
            cleaned.append([
                padded[0],  # Timestamp
                padded[1],  # Discord Seller
                padded[3],  # Seller Habbo
                padded[4],  # Buyer
                padded[5],  # Rank Sold
                padded[6],  # Amount
                padded[7],  # Proof / Notes
            ])
        else:
            cleaned.append(padded[:len(RANK_SALES_HEADERS)])

    return cleaned


def apply_rank_sales_sheet_style(worksheet) -> None:
    try:
        worksheet.format("A1:G1", {
            "backgroundColor": {"red": 0.18, "green": 0.08, "blue": 0.36},
            "textFormat": {
                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                "bold": True,
                "fontSize": 11,
            },
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
        })
        worksheet.format("A2:G1000", {
            "backgroundColor": {"red": 0.97, "green": 0.95, "blue": 1.0},
            "textFormat": {"foregroundColor": {"red": 0.08, "green": 0.08, "blue": 0.12}},
            "verticalAlignment": "MIDDLE",
        })
        worksheet.format("G:G", {"wrapStrategy": "WRAP", "horizontalAlignment": "LEFT"})
        worksheet.format("A:F", {"horizontalAlignment": "CENTER"})

        try:
            worksheet.freeze(rows=1)
        except Exception:
            worksheet.spreadsheet.batch_update({
                "requests": [{
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": worksheet.id,
                            "gridProperties": {"frozenRowCount": 1},
                        },
                        "fields": "gridProperties.frozenRowCount",
                    }
                }]
            })

        try:
            worksheet.columns_auto_resize(0, 7)
        except Exception:
            worksheet.spreadsheet.batch_update({
                "requests": [{
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": worksheet.id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 7,
                        }
                    }
                }]
            })

        worksheet.spreadsheet.batch_update({
            "requests": [{
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": worksheet.id,
                        "dimension": "COLUMNS",
                        "startIndex": 6,
                        "endIndex": 7,
                    },
                    "properties": {"pixelSize": 350},
                    "fields": "pixelSize",
                }
            }]
        })
    except Exception as exc:
        print(f"Rank sales sheet style warning: {type(exc).__name__}: {exc}")


def setup_rank_sales_sheet_layout() -> None:
    worksheet = get_rank_sales_worksheet()
    values = worksheet.get_all_values()
    cleaned = clean_rank_sales_rows(values)

    worksheet.clear()
    worksheet.update(range_name="A1", values=cleaned, value_input_option="USER_ENTERED")

    try:
        worksheet.batch_clear(["H:Z"])
    except Exception:
        pass

    apply_rank_sales_sheet_style(worksheet)


def append_rank_sale_to_sheet(row: list[str]) -> None:
    worksheet = get_rank_sales_worksheet()
    values = worksheet.get_all_values()
    current_header = values[0][:len(RANK_SALES_HEADERS)] if values else []
    old_header = [cell.strip().casefold() for cell in values[0]] if values else []

    if current_header != RANK_SALES_HEADERS or "seller id" in old_header or "channel id" in old_header or "channel" in old_header:
        setup_rank_sales_sheet_layout()
        worksheet = get_rank_sales_worksheet()
    elif not values:
        worksheet.update(range_name="A1", values=[RANK_SALES_HEADERS], value_input_option="USER_ENTERED")
        apply_rank_sales_sheet_style(worksheet)

    worksheet.append_row(row, value_input_option="USER_ENTERED")
    apply_rank_sales_sheet_style(worksheet)


async def get_rank_sales_channel(guild: discord.Guild | None):
    if guild is None or not RANK_SALES_CHANNEL_ID:
        return None

    try:
        channel_id = int(RANK_SALES_CHANNEL_ID)
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


async def member_can_log_sales(interaction: discord.Interaction) -> bool:
    if not SALES_ROLE_ID:
        return True
    if interaction.guild is None:
        return False

    try:
        sales_role_id = int(SALES_ROLE_ID)
    except ValueError:
        return False

    member = interaction.user
    if not isinstance(member, discord.Member):
        member = await interaction.guild.fetch_member(interaction.user.id)

    if member.guild_permissions.administrator:
        return True

    return any(role.id == sales_role_id for role in member.roles)


async def update_stats(guild: discord.Guild) -> None:
    staff_ids = set()
    for role in staff_roles(guild):
        staff_ids.update(member.id for member in role.members)

    names = {
        "server members:": f"Server Members: {guild.member_count or 0}",
        "staff members:": f"Staff Members: {len(staff_ids)}",
        "boost tier:": f"Boost tier: {guild.premium_tier}",
    }
    for channel in guild.voice_channels:
        lowered = channel.name.casefold()
        for prefix, new_name in names.items():
            if lowered.startswith(prefix) and channel.name != new_name:
                try:
                    await channel.edit(name=new_name, reason="Updated server counters")
                except discord.Forbidden:
                    pass
                break


@tasks.loop(minutes=30)
async def stat_loop() -> None:
    for guild in bot.guilds:
        await update_stats(guild)


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} (ID: {bot.user.id if bot.user else 'unknown'})")
    if not bot.synced_commands_once:
        if TEST_GUILD_ID:
            guild_object = discord.Object(id=int(TEST_GUILD_ID))
            bot.tree.clear_commands(guild=guild_object)
            bot.tree.copy_global_to(guild=guild_object)
            await bot.tree.sync(guild=guild_object)
            print(f"Commands synced instantly to test server {TEST_GUILD_ID}.")
        else:
            await bot.tree.sync()
            print("Global commands synced. Discord may take time to display them.")
        bot.synced_commands_once = True
    if not stat_loop.is_running():
        stat_loop.start()


@bot.tree.command(description="Check whether the bot is responding.")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)} ms")


sale_group = app_commands.Group(name="sale", description="Rank sale tools.")


@sale_group.command(name="log", description="Open a form to log a rank sale into Google Sheets.")
async def sale_log(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    if not await member_can_log_sales(interaction):
        await interaction.response.send_message("You do not have permission to log rank sales.", ephemeral=True)
        return

    if not SPREADSHEET_ID or not GOOGLE_CREDENTIALS_JSON:
        await interaction.response.send_message(
            "Rank sales logging is not configured yet. Add SPREADSHEET_ID and GOOGLE_CREDENTIALS_JSON in Railway Variables.",
            ephemeral=True,
        )
        return

    await interaction.response.send_modal(RankSaleModal())


@sale_group.command(name="summary", description="Show the top rank sellers based on logged sales.")
async def sale_summary(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        worksheet = await asyncio.to_thread(get_rank_sales_worksheet)
        values = await asyncio.to_thread(worksheet.get_all_values)
        rows = values[1:] if len(values) > 1 else []

        if not rows:
            await interaction.followup.send("No rank sales have been logged yet.", ephemeral=True)
            return

        seller_totals = {}
        seller_amounts = {}

        for row in rows:
            padded = list(row) + [""] * 7
            seller = padded[1].strip() or "Unknown"
            amount_text = padded[5].strip().lower().replace(",", "")

            amount = 0
            number = ""
            for char in amount_text + " ":
                if char.isdigit():
                    number += char
                    continue
                if number:
                    value = int(number)
                    idx = amount_text.find(number)
                    nearby = amount_text[max(0, idx - 2):idx + len(number) + 4]
                    if "gb" in nearby or "gold" in nearby:
                        amount += value * 50
                    else:
                        amount += value
                    number = ""

            seller_totals[seller] = seller_totals.get(seller, 0) + 1
            seller_amounts[seller] = seller_amounts.get(seller, 0) + amount

        sorted_sellers = sorted(
            seller_totals.keys(),
            key=lambda seller: (seller_amounts.get(seller, 0), seller_totals.get(seller, 0)),
            reverse=True,
        )[:10]

        lines = []
        for index, seller in enumerate(sorted_sellers, start=1):
            sales_count = seller_totals[seller]
            amount_total = seller_amounts[seller]
            lines.append(
                f"{index}.  **{seller}**\n— {sales_count} sale{'s' if sales_count != 1 else ''} — {amount_total}c total"
            )

        embed = discord.Embed(
            title="Rank Seller Totals",
            description="\n".join(lines),
            color=discord.Color.purple(),
            timestamp=datetime.now(ZoneInfo(TIMEZONE)),
        )
        embed.set_footer(text="Synced from the Rank Sales sheet")
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as exc:
        print(f"Rank sales summary error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not load sales summary: {type(exc).__name__}: {exc}", ephemeral=True)



bot.tree.add_command(sale_group)


@bot.tree.command(name="setup-rank-sales-sheet", description="Clean and style the rank sales Google Sheet.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_rank_sales_sheet(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await asyncio.to_thread(setup_rank_sales_sheet_layout)
        await interaction.followup.send(
            "Rank Sales sheet cleaned and styled. Columns are now: Timestamp, Discord Seller, Seller Habbo, Buyer, Rank Sold, Amount, Proof / Notes.",
            ephemeral=True,
        )
    except Exception as exc:
        print(f"Rank sales sheet setup error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not setup sheet: {type(exc).__name__}: {exc}", ephemeral=True)


@bot.tree.command(description="Build channels and roles from a template.")
@app_commands.describe(template="Choose the server layout to build", keep_existing="Do not edit existing channels")
@app_commands.choices(
    template=[
        app_commands.Choice(name="Agency style server", value="agency"),
        app_commands.Choice(name="Simple server", value="simple"),
    ]
)
@app_commands.checks.has_permissions(administrator=True)
async def build_server(interaction: discord.Interaction, template: app_commands.Choice[str], keep_existing: bool = True) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    try:
        await interaction.response.defer(ephemeral=True, thinking=True)
    except discord.NotFound:
        print("Build server interaction expired before it could be acknowledged. Run /build_server again.")
        return
    roles = AGENCY_ROLES if template.value == "agency" else SIMPLE_ROLES
    channels = AGENCY_CHANNELS if template.value == "agency" else SIMPLE_CHANNELS

    created_roles = 0
    created_categories = 0
    created_text = 0
    created_voice = 0
    updated = 0

    try:
        for role_name in reversed(roles):
            if discord.utils.get(guild.roles, name=role_name) is None:
                await guild.create_role(name=role_name, reason="Created by server builder")
                created_roles += 1

        for category_name, channel_list in channels.items():
            category = discord.utils.get(guild.categories, name=category_name)
            category_overwrites = staff_channel_overwrites(guild) if is_staff_area(category_name) else None
            if category is None:
                if category_overwrites is None:
                    category = await guild.create_category(name=category_name, reason="Created by server builder")
                else:
                    category = await guild.create_category(
                        name=category_name, overwrites=category_overwrites, reason="Created by server builder"
                    )
                created_categories += 1
            elif not keep_existing and category_overwrites is not None:
                await category.edit(overwrites=category_overwrites, reason="Updated by server builder")
                updated += 1

            for channel_name, channel_type in channel_list:
                if discord.utils.get(category.channels, name=channel_name):
                    continue
                channel_overwrites = get_overwrites(guild, category_name, channel_name, channel_type)
                if channel_type == "voice":
                    if channel_overwrites is None:
                        await guild.create_voice_channel(name=channel_name, category=category, reason="Created by server builder")
                    else:
                        await guild.create_voice_channel(
                            name=channel_name, category=category, overwrites=channel_overwrites, reason="Created by server builder"
                        )
                    created_voice += 1
                else:
                    if channel_overwrites is None:
                        await guild.create_text_channel(name=channel_name, category=category, reason="Created by server builder")
                    else:
                        await guild.create_text_channel(
                            name=channel_name, category=category, overwrites=channel_overwrites, reason="Created by server builder"
                        )
                    created_text += 1

        await update_stats(guild)
        await interaction.followup.send(
            f"Done. Roles: {created_roles}, categories: {created_categories}, text: {created_text}, voice: {created_voice}, updates: {updated}",
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "I need Manage Roles and Manage Channels. Also move my bot role above the roles I create.", ephemeral=True
        )
    except Exception as exc:
        await interaction.followup.send(f"Error: {type(exc).__name__}: {exc}", ephemeral=True)
        raise


@bot.tree.command(description="Create and reorder the server role hierarchy.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_hierarchy(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    if guild.me is None:
        await interaction.followup.send("I could not find my bot member in this server.", ephemeral=True)
        return

    created = 0
    updated = 0
    moved = 0
    failed = []
    managed_roles: list[discord.Role] = []

    try:
        for role_name, permissions in HIERARCHY_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role is None:
                role = await guild.create_role(
                    name=role_name,
                    permissions=permissions,
                    reason="Created by hierarchy setup command",
                )
                created += 1
            else:
                await role.edit(permissions=permissions, reason="Updated by hierarchy setup command")
                updated += 1
            managed_roles.append(role)

        muted_role = discord.utils.get(guild.roles, name="Muted")
        if muted_role is not None:
            for channel in guild.channels:
                try:
                    await channel.set_permissions(
                        muted_role,
                        send_messages=False,
                        speak=False,
                        add_reactions=False,
                        create_public_threads=False,
                        create_private_threads=False,
                        reason="Muted role permissions",
                    )
                except (discord.Forbidden, AttributeError):
                    pass

        position = max(guild.me.top_role.position - 1, 1)
        for role in managed_roles:
            if role >= guild.me.top_role:
                failed.append(role.name)
                continue
            try:
                await role.edit(position=position, reason="Reordered by hierarchy setup command")
                moved += 1
                position = max(position - 1, 1)
            except discord.Forbidden:
                failed.append(role.name)

        message = f"Hierarchy setup done. Created: {created}, updated: {updated}, moved: {moved}."
        if failed:
            message += " Could not move: " + ", ".join(failed) + ". Move my bot role higher and run again."
        await interaction.followup.send(message, ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send(
            "I need Administrator or Manage Roles. Also move my bot role above every role I should control.",
            ephemeral=True,
        )
    except Exception as exc:
        await interaction.followup.send(f"Hierarchy error: {type(exc).__name__}: {exc}", ephemeral=True)
        raise


@bot.tree.command(description="Remove old template categories after confirming.")
@app_commands.describe(confirm="Type DELETE to confirm", include_start_here="Also remove START HERE")
@app_commands.checks.has_permissions(administrator=True)
async def delete_old_layout(interaction: discord.Interaction, confirm: str, include_start_here: bool = False) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    if confirm != "DELETE":
        await interaction.response.send_message("Type DELETE in the confirm field to run cleanup.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    names_to_remove = set(OLD_LAYOUT_CATEGORIES)
    if include_start_here:
        names_to_remove.add("START HERE")

    removed_channels = 0
    removed_categories = 0
    try:
        for category in list(guild.categories):
            if category.name not in names_to_remove:
                continue
            for channel in list(category.channels):
                await channel.delete(reason="Removed old layout")
                removed_channels += 1
            await category.delete(reason="Removed old layout")
            removed_categories += 1

        await interaction.followup.send(
            f"Old layout cleanup done. Removed categories: {removed_categories}, removed channels: {removed_channels}.",
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "I need Manage Channels permission to remove the old layout.", ephemeral=True
        )
    except Exception as exc:
        await interaction.followup.send(f"Cleanup error: {type(exc).__name__}: {exc}", ephemeral=True)
        raise


bot.run(TOKEN)
