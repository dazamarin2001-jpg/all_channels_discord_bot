import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Add DISCORD_TOKEN in Railway Variables.")

intents = discord.Intents.default()
intents.members = True


class ServerBot(commands.Bot):
    async def setup_hook(self) -> None:
        self.add_view(TicketPanel())
        self.add_view(CloseTicketView())

        if TEST_GUILD_ID:
            guild = discord.Object(id=int(TEST_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Commands synced instantly to test server {TEST_GUILD_ID}.")
        else:
            await self.tree.sync()
            print("Global commands synced. Discord may take time to display them.")


bot = ServerBot(command_prefix="!", intents=intents)


class TicketPanel(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Open Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.green,
        custom_id="persistent:create_ticket",
    )
    async def create_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Use this inside a server.", ephemeral=True)
            return

        guild = interaction.guild
        existing = discord.utils.find(
            lambda c: isinstance(c, discord.TextChannel)
            and c.topic == f"ticket-owner:{interaction.user.id}",
            guild.channels,
        )
        if existing:
            await interaction.response.send_message(
                f"You already have an open ticket: {existing.mention}", ephemeral=True
            )
            return

        bot_member = guild.me
        if bot_member is None:
            await interaction.response.send_message("Bot member could not be resolved.", ephemeral=True)
            return

        category = discord.utils.find(
            lambda c: isinstance(c, discord.CategoryChannel)
            and ("help" in c.name.lower() or "support" in c.name.lower()),
            guild.categories,
        )
        support_role = discord.utils.get(guild.roles, name="Support") or discord.utils.get(guild.roles, name="Staff")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True,
            ),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )

        safe_name = interaction.user.name.lower().replace(" ", "-")[:40]
        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{safe_name}",
                category=category,
                overwrites=overwrites,
                topic=f"ticket-owner:{interaction.user.id}",
                reason=f"Ticket opened by {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I need **Manage Channels** to create tickets.", ephemeral=True
            )
            return

        await channel.send(
            content=interaction.user.mention,
            embed=discord.Embed(
                title="Support Ticket",
                description="Explain what you need help with. A staff member will respond here.",
                color=discord.Color.blurple(),
            ),
            view=CloseTicketView(),
        )
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)


class CloseTicketView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.red,
        custom_id="persistent:close_ticket",
    )
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not channel.topic or not channel.topic.startswith("ticket-owner:"):
            await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
            return

        owner_id = int(channel.topic.split(":", 1)[1])
        can_close = interaction.user.id == owner_id or (
            isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.manage_channels
        )
        if not can_close:
            await interaction.response.send_message(
                "Only the ticket owner or staff can close this ticket.", ephemeral=True
            )
            return

        await interaction.response.send_message("Closing this ticket…")
        await channel.delete(reason=f"Ticket closed by {interaction.user}")


ROLE_PERMISSIONS = {
    "Founder": discord.Permissions(administrator=True),
    "Foundation Advisor": discord.Permissions(administrator=True),
    "Administrator": discord.Permissions(administrator=True),
    "Supreme Command": discord.Permissions(
        manage_channels=True,
        manage_roles=True,
        manage_messages=True,
        moderate_members=True,
        view_audit_log=True,
    ),
    "Elite Command": discord.Permissions(
        manage_channels=True,
        manage_messages=True,
        moderate_members=True,
        view_audit_log=True,
    ),
    "Moderator": discord.Permissions(
        manage_messages=True,
        moderate_members=True,
        manage_nicknames=True,
        view_audit_log=True,
    ),
    "Trial Moderation": discord.Permissions(
        manage_messages=True,
        moderate_members=True,
        view_audit_log=True,
    ),
    "Staff": discord.Permissions(
        manage_messages=True,
        moderate_members=True,
        view_audit_log=True,
    ),
    "Support": discord.Permissions(manage_messages=True),
}

STAFF_ROLE_NAMES = (
    "Founder",
    "Foundation Advisor",
    "Administrator",
    "Supreme Command",
    "Elite Command",
    "Moderator",
    "Trial Moderation",
    "Staff",
)
READ_ONLY_MARKERS = (
    "rules",
    "announcements",
    "updates",
    "pay-announcements",
    "event-announcements",
    "broadcasting-announcements",
    "donation-shoutout",
    "applications-and-quizzes",
    "blog-updates",
    "giveaways",
    "polls",
    "twitter",
    "reaction-roles",
    "birthday-set",
)
STAFF_MARKERS = (
    "staff",
    "elective",
    "ownership",
    "presidential-chat",
    "supreme-command",
    "elite-command",
    "founders-reps",
    "special-division-leaders",
    "moderation-5ic",
)
VOICE_COUNTER_PREFIXES = ("server members:", "staff members:", "boost tier:")

SERVER_TEMPLATES = {
    "agency": {
        "roles": [
            "Founder",
            "Foundation Advisor",
            "Supreme Command",
            "Elite Command",
            "Trial Moderation",
            "Legend",
            "Supreme Donator",
            "Emerald Donator",
            "Administrator",
            "Moderator",
            "Staff",
            "Support",
            "Member",
            "Bot",
        ],
        "categories": {
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
            "💬 SOCIAL CHATS": [
                ("🚀︱nitro-boosters", "text"),
            ],
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
        },
    },
    "simple": {
        "roles": ["Administrator", "Moderator", "Staff", "Support", "Member", "Bot"],
        "categories": {
            "START HERE": [("welcome", "text"), ("rules", "text"), ("announcements", "text")],
            "COMMUNITY": [("general", "text"), ("media", "text"), ("suggestions", "text")],
            "SUPPORT": [("open-a-ticket", "text"), ("questions", "text")],
            "STAFF": [("staff-chat", "text"), ("mod-logs", "text")],
        },
    },
}


def roles_by_name(guild: discord.Guild, names: tuple[str, ...]) -> list[discord.Role]:
    return [role for role in guild.roles if role.name in names]


def is_staff_area(category_name: str, channel_name: str = "") -> bool:
    value = f"{category_name} {channel_name}".casefold()
    return any(marker in value for marker in STAFF_MARKERS)


def is_read_only(channel_name: str) -> bool:
    lowered = channel_name.casefold()
    return any(marker in lowered for marker in READ_ONLY_MARKERS)


def is_voice_counter(channel_name: str) -> bool:
    lowered = channel_name.casefold()
    return any(lowered.startswith(prefix) for prefix in VOICE_COUNTER_PREFIXES)


def add_bot_overwrite(guild: discord.Guild, overwrites: dict) -> None:
    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True,
            connect=True,
            speak=True,
        )


def private_staff_overwrites(guild: discord.Guild, staff_roles: list[discord.Role]) -> dict:
    overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    for role in staff_roles:
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True,
            connect=True,
            speak=True,
        )
    add_bot_overwrite(guild, overwrites)
    return overwrites


def read_only_overwrites(guild: discord.Guild, staff_roles: list[discord.Role]) -> dict:
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            read_message_history=True,
        )
    }
    for role in staff_roles:
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True,
        )
    add_bot_overwrite(guild, overwrites)
    return overwrites


def voice_counter_overwrites(guild: discord.Guild) -> dict:
    overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False)}
    add_bot_overwrite(guild, overwrites)
    return overwrites


def overwrites_for(guild: discord.Guild, category_name: str, channel_name: str, channel_type: str, staff_roles: list[discord.Role]) -> dict | None:
    if channel_type == "voice" and is_voice_counter(channel_name):
        return voice_counter_overwrites(guild)
    if is_staff_area(category_name, channel_name):
        return private_staff_overwrites(guild, staff_roles)
    if is_read_only(channel_name):
        return read_only_overwrites(guild, staff_roles)
    return None


async def update_server_stats(guild: discord.Guild) -> None:
    staff_roles = roles_by_name(guild, STAFF_ROLE_NAMES)
    staff_ids = set()
    for role in staff_roles:
        staff_ids.update(member.id for member in role.members)

    replacements = {
        "server members:": f"Server Members: {guild.member_count or 0}",
        "staff members:": f"Staff Members: {len(staff_ids)}",
        "boost tier:": f"Boost tier: {guild.premium_tier}",
    }
    for channel in guild.voice_channels:
        lowered = channel.name.casefold()
        for prefix, new_name in replacements.items():
            if lowered.startswith(prefix) and channel.name != new_name:
                try:
                    await channel.edit(name=new_name, reason="Update server counters")
                except discord.Forbidden:
                    pass
                break


@tasks.loop(minutes=30)
async def stat_counter_loop() -> None:
    for guild in bot.guilds:
        await update_server_stats(guild)


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} (ID: {bot.user.id if bot.user else 'unknown'})")
    if not stat_counter_loop.is_running():
        stat_counter_loop.start()


@bot.event
async def on_member_join(member: discord.Member) -> None:
    await update_server_stats(member.guild)


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    await update_server_stats(member.guild)


@bot.tree.command(description="Check whether the bot is responding.")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(f"🏓 Pong! `{round(bot.latency * 1000)} ms`")


@bot.tree.command(description="Show information about this Discord server.")
async def serverinfo(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    embed = discord.Embed(title=guild.name, color=discord.Color.blurple(), timestamp=discord.utils.utcnow())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Members", value=str(guild.member_count))
    embed.add_field(name="Channels", value=str(len(guild.channels)))
    embed.add_field(name="Boost Tier", value=str(guild.premium_tier))
    await interaction.response.send_message(embed=embed)


@bot.tree.command(description="Post a button that members can use to create tickets.")
@app_commands.checks.has_permissions(manage_channels=True)
async def ticketpanel(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="Need Help?",
        description="Press the button below to open a private support ticket.",
        color=discord.Color.blurple(),
    )
    await interaction.response.send_message(embed=embed, view=TicketPanel())


@bot.tree.command(description="Delete a number of recent messages.")
@app_commands.describe(amount="Number of messages to delete, from 1 to 100")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use this command in a text channel.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)


@bot.tree.command(description="Build channels and roles from a template.")
@app_commands.describe(
    template="Choose the server layout to build",
    keep_existing="Keep existing matching channels and permissions",
)
@app_commands.choices(
    template=[
        app_commands.Choice(name="Agency style server", value="agency"),
        app_commands.Choice(name="Simple server", value="simple"),
    ]
)
@app_commands.checks.has_permissions(administrator=True)
async def build_server(
    interaction: discord.Interaction,
    template: app_commands.Choice[str],
    keep_existing: bool = True,
) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    layout = SERVER_TEMPLATES[template.value]
    created_roles = 0
    created_categories = 0
    created_text_channels = 0
    created_voice_channels = 0
    updated_permissions = 0

    try:
        for role_name in reversed(layout["roles"]):
            existing = discord.utils.get(guild.roles, name=role_name)
            permissions = ROLE_PERMISSIONS.get(role_name, discord.Permissions.none())
            if existing is None:
                await guild.create_role(name=role_name, permissions=permissions, reason="Created by server builder")
                created_roles += 1
            elif not keep_existing and guild.me and existing < guild.me.top_role and not existing.managed:
                if existing.permissions != permissions:
                    await existing.edit(permissions=permissions, reason="Updated by server builder")
                    updated_permissions += 1

        staff_roles = roles_by_name(guild, STAFF_ROLE_NAMES)

        for category_name, channels in layout["categories"].items():
            category = discord.utils.get(guild.categories, name=category_name)
            category_overwrites = private_staff_overwrites(guild, staff_roles) if is_staff_area(category_name) else None
            if category is None:
                category = await guild.create_category(
                    category_name,
                    overwrites=category_overwrites,
                    reason="Created by server builder",
                )
                created_categories += 1
            elif not keep_existing and category_overwrites and category.overwrites != category_overwrites:
                await category.edit(overwrites=category_overwrites, reason="Updated by server builder")
                updated_permissions += 1

            for channel_name, channel_type in channels:
                existing = discord.utils.get(category.channels, name=channel_name)
                channel_overwrites = overwrites_for(guild, category_name, channel_name, channel_type, staff_roles)
                if existing:
                    if not keep_existing and channel_overwrites and existing.overwrites != channel_overwrites:
                        await existing.edit(overwrites=channel_overwrites, reason="Updated by server builder")
                        updated_permissions += 1
                    continue

                if channel_type == "voice":
                    await guild.create_voice_channel(
                        channel_name,
                        category=category,
                        overwrites=channel_overwrites,
                        reason="Created by server builder",
                    )
                    created_voice_channels += 1
                else:
                    await guild.create_text_channel(
                        channel_name,
                        category=category,
                        overwrites=channel_overwrites,
                        reason="Created by server builder",
                    )
                    created_text_channels += 1

        await update_server_stats(guild)

        await interaction.followup.send(
            f"✅ **{template.name} created.**\n"
            f"New roles: **{created_roles}**\n"
            f"New categories: **{created_categories}**\n"
            f"New text channels: **{created_text_channels}**\n"
            f"New voice channels: **{created_voice_channels}**\n"
            f"Permission updates: **{updated_permissions}**",
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "I could not finish. Give the bot **Manage Roles** and **Manage Channels**, then move the bot role above the roles it manages.",
            ephemeral=True,
        )


bot.run(TOKEN)
