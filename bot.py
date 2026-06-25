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
    "Trial Moderation", "Head Admin", "Admin", "Senior Moderator",
    "Administrator", "Moderator", "Support Manager", "Support Staff", "Staff"
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

HIERARCHY_ROLES = [
    ("👑 Owner", discord.Permissions(administrator=True)),
    ("🛡️ Head Admin", discord.Permissions(administrator=True)),
    ("⚔️ Admin", discord.Permissions(administrator=True)),
    ("🛠️ Senior Moderator", discord.Permissions(kick_members=True, manage_messages=True, moderate_members=True)),
    ("🔨 Moderator", discord.Permissions(kick_members=True, manage_messages=True, moderate_members=True)),
    ("🎫 Support Manager", discord.Permissions(manage_channels=True, manage_threads=True, manage_messages=True)),
    ("📨 Support Staff", discord.Permissions(manage_threads=True, manage_messages=True)),
    ("💎 Premium", discord.Permissions(view_channel=True, send_messages=True, read_message_history=True)),
    ("⭐ Verified", discord.Permissions(view_channel=True, send_messages=True, read_message_history=True)),
    ("👤 Member", discord.Permissions(view_channel=True, send_messages=True, read_message_history=True)),
    ("🆕 New Member", discord.Permissions(view_channel=True, read_message_history=True)),
    ("🚫 Muted", discord.Permissions(view_channel=True, read_message_history=True)),
]

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


@bot.tree.command(description="Create and order the server role hierarchy.")
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
    failed: list[str] = []
    role_objects: list[discord.Role] = []

    try:
        for role_name, permissions in HIERARCHY_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role is None:
                role = await guild.create_role(
                    name=role_name,
                    permissions=permissions,
                    reason="Created by hierarchy setup",
                )
                created += 1
            else:
                await role.edit(permissions=permissions, reason="Updated by hierarchy setup")
                updated += 1
            role_objects.append(role)

        position = max(guild.me.top_role.position - 1, 1)
        for role in role_objects:
            if role >= guild.me.top_role:
                failed.append(role.name)
                continue
            await role.edit(position=position, reason="Ordered by hierarchy setup")
            position = max(position - 1, 1)
            moved += 1

        muted_role = discord.utils.get(guild.roles, name="🚫 Muted")
        if muted_role is not None:
            overwrite = discord.PermissionOverwrite(
                send_messages=False,
                speak=False,
                add_reactions=False,
                create_public_threads=False,
                create_private_threads=False,
            )
            for channel in guild.channels:
                if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.ForumChannel)):
                    try:
                        await channel.set_permissions(muted_role, overwrite=overwrite, reason="Muted role restrictions")
                    except discord.Forbidden:
                        failed.append(f"{channel.name} muted permissions")

        message = f"Hierarchy setup done. Created: {created}, updated: {updated}, moved: {moved}."
        if failed:
            message += " Could not update: " + ", ".join(failed[:10])
            if len(failed) > 10:
                message += f" and {len(failed) - 10} more."
        await interaction.followup.send(message, ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send(
            "I need Administrator or Manage Roles. Move my bot role near the top, above every role I should manage.",
            ephemeral=True,
        )
    except Exception as exc:
        await interaction.followup.send(f"Hierarchy error: {type(exc).__name__}: {exc}", ephemeral=True)
        raise


bot.run(TOKEN)
