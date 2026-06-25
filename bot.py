import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")

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
    "COMMUNITY",
    "GAMING",
    "SUPPORT",
    "STAFF",
    "INFORMATION",
    "CLIENT AREA",
    "About Us",
    "┌──── Information ────┐",
    "┌──── Support ────┐",
    "┌──── Chat ────┐",
    "┌──── Staff ────┐",
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
