import os
import sqlite3
from datetime import timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_data.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4.1-mini")
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY and AsyncOpenAI else None

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and add your bot token.")

intents = discord.Intents.default()
intents.members = True

class ServerBot(commands.Bot):
    async def setup_hook(self) -> None:
        initialize_database()
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
db = sqlite3.connect(DATABASE_PATH)
db.row_factory = sqlite3.Row


def initialize_database() -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            welcome_channel_id INTEGER,
            log_channel_id INTEGER,
            ticket_category_id INTEGER,
            support_role_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    db.commit()


def get_settings(guild_id: int) -> sqlite3.Row | None:
    return db.execute(
        "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
    ).fetchone()


def upsert_setting(guild_id: int, column: str, value: int | None) -> None:
    allowed = {
        "welcome_channel_id",
        "log_channel_id",
        "ticket_category_id",
        "support_role_id",
    }
    if column not in allowed:
        raise ValueError("Invalid settings column")

    db.execute(
        "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
    )
    db.execute(
        f"UPDATE guild_settings SET {column} = ? WHERE guild_id = ?",
        (value, guild_id),
    )
    db.commit()


async def send_log(guild: discord.Guild, embed: discord.Embed) -> None:
    settings = get_settings(guild.id)
    if not settings or not settings["log_channel_id"]:
        return

    channel = guild.get_channel(settings["log_channel_id"])
    if isinstance(channel, discord.TextChannel):
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass


def moderation_embed(
    action: str,
    target: discord.abc.User,
    moderator: discord.abc.User,
    reason: str,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"Moderation: {action}",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Member", value=f"{target} (`{target.id}`)", inline=False)
    embed.add_field(name="Moderator", value=f"{moderator} (`{moderator.id}`)", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    return embed


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
            await interaction.response.send_message(
                "Tickets can only be opened inside a server.", ephemeral=True
            )
            return

        guild = interaction.guild
        settings = get_settings(guild.id)
        category = None
        support_role = None

        if settings:
            category = guild.get_channel(settings["ticket_category_id"]) if settings["ticket_category_id"] else None
            support_role = guild.get_role(settings["support_role_id"]) if settings["support_role_id"] else None

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
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                topic=f"ticket-owner:{interaction.user.id}",
                reason=f"Ticket opened by {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I need the **Manage Channels** permission to create tickets.",
                ephemeral=True,
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
        await interaction.response.send_message(
            f"Your ticket was created: {channel.mention}", ephemeral=True
        )


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
            await interaction.response.send_message(
                "This is not a ticket channel.", ephemeral=True
            )
            return

        owner_id = int(channel.topic.split(":", 1)[1])
        member = interaction.user
        can_close = (
            member.id == owner_id
            or (
                isinstance(member, discord.Member)
                and member.guild_permissions.manage_channels
            )
        )
        if not can_close:
            await interaction.response.send_message(
                "Only the ticket owner or staff can close this ticket.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Closing this ticket…")
        await channel.delete(reason=f"Ticket closed by {interaction.user}")


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} (ID: {bot.user.id if bot.user else 'unknown'})")


@bot.event
async def on_member_join(member: discord.Member) -> None:
    settings = get_settings(member.guild.id)
    if not settings or not settings["welcome_channel_id"]:
        return

    channel = member.guild.get_channel(settings["welcome_channel_id"])
    if isinstance(channel, discord.TextChannel):
        embed = discord.Embed(
            title="Welcome!",
            description=f"Welcome to **{member.guild.name}**, {member.mention}!",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count}")
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    embed = discord.Embed(
        title="Member Left",
        description=f"{member} (`{member.id}`) left the server.",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow(),
    )
    await send_log(member.guild, embed)


@bot.tree.command(description="Check whether the bot is responding.")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        f"🏓 Pong! `{round(bot.latency * 1000)} ms`"
    )


@bot.tree.command(description="Show information about a server member.")
@app_commands.describe(member="The member to inspect")
async def userinfo(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None,
) -> None:
    member = member or interaction.user
    if not isinstance(member, discord.Member):
        await interaction.response.send_message("Member not found.", ephemeral=True)
        return

    roles = [role.mention for role in member.roles[1:][-10:]]
    embed = discord.Embed(
        title=str(member),
        color=member.color,
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="User ID", value=str(member.id), inline=False)
    embed.add_field(
        name="Account Created",
        value=discord.utils.format_dt(member.created_at, style="F"),
        inline=False,
    )
    if member.joined_at:
        embed.add_field(
            name="Joined Server",
            value=discord.utils.format_dt(member.joined_at, style="F"),
            inline=False,
        )
    embed.add_field(
        name="Roles",
        value=", ".join(roles) if roles else "No roles",
        inline=False,
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(description="Show information about this Discord server.")
async def serverinfo(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    embed = discord.Embed(
        title=guild.name,
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown")
    embed.add_field(name="Members", value=str(guild.member_count))
    embed.add_field(name="Channels", value=str(len(guild.channels)))
    embed.add_field(
        name="Created",
        value=discord.utils.format_dt(guild.created_at, style="D"),
        inline=False,
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(description="Configure the welcome-message channel.")
@app_commands.checks.has_permissions(manage_guild=True)
async def setup_welcome(
    interaction: discord.Interaction, channel: discord.TextChannel
) -> None:
    if interaction.guild is None:
        return
    upsert_setting(interaction.guild.id, "welcome_channel_id", channel.id)
    await interaction.response.send_message(
        f"Welcome messages will be sent in {channel.mention}.", ephemeral=True
    )


@bot.tree.command(description="Configure the moderation log channel.")
@app_commands.checks.has_permissions(manage_guild=True)
async def setup_logs(
    interaction: discord.Interaction, channel: discord.TextChannel
) -> None:
    if interaction.guild is None:
        return
    upsert_setting(interaction.guild.id, "log_channel_id", channel.id)
    await interaction.response.send_message(
        f"Moderation logs will be sent in {channel.mention}.", ephemeral=True
    )


@bot.tree.command(description="Configure the ticket category and support role.")
@app_commands.checks.has_permissions(manage_guild=True)
async def setup_tickets(
    interaction: discord.Interaction,
    category: discord.CategoryChannel,
    support_role: discord.Role,
) -> None:
    if interaction.guild is None:
        return
    upsert_setting(interaction.guild.id, "ticket_category_id", category.id)
    upsert_setting(interaction.guild.id, "support_role_id", support_role.id)
    await interaction.response.send_message(
        f"Tickets will be created under **{category.name}** and visible to {support_role.mention}.",
        ephemeral=True,
    )


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


@bot.tree.command(description="Warn a member.")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided",
) -> None:
    if interaction.guild is None:
        return
    db.execute(
        "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
        (interaction.guild.id, member.id, interaction.user.id, reason),
    )
    db.commit()
    try:
        await member.send(f"You were warned in **{interaction.guild.name}**.\nReason: {reason}")
    except discord.Forbidden:
        pass
    await interaction.response.send_message(
        f"Warned {member.mention}.", ephemeral=True
    )
    await send_log(
        interaction.guild,
        moderation_embed("Warning", member, interaction.user, reason),
    )


@bot.tree.command(description="View a member's warnings.")
@app_commands.checks.has_permissions(moderate_members=True)
async def warnings(interaction: discord.Interaction, member: discord.Member) -> None:
    if interaction.guild is None:
        return
    rows = db.execute(
        "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 10",
        (interaction.guild.id, member.id),
    ).fetchall()
    if not rows:
        await interaction.response.send_message(
            f"{member.mention} has no warnings.", ephemeral=True
        )
        return

    lines = [
        f"`#{row['id']}` — {row['reason']} (moderator ID: `{row['moderator_id']}`)"
        for row in rows
    ]
    embed = discord.Embed(
        title=f"Warnings for {member}",
        description="\n".join(lines),
        color=discord.Color.orange(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(description="Temporarily prevent a member from chatting.")
@app_commands.describe(minutes="Timeout duration in minutes")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: str = "No reason provided",
) -> None:
    if interaction.guild is None:
        return
    if member.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "I cannot timeout that member because their role is equal to or above mine.",
            ephemeral=True,
        )
        return
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await interaction.response.send_message(
        f"Timed out {member.mention} for {minutes} minute(s).", ephemeral=True
    )
    await send_log(
        interaction.guild,
        moderation_embed(f"Timeout ({minutes} minutes)", member, interaction.user, reason),
    )


@bot.tree.command(description="Kick a member from the server.")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided",
) -> None:
    if interaction.guild is None:
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"Kicked **{member}**.", ephemeral=True)
    await send_log(
        interaction.guild,
        moderation_embed("Kick", member, interaction.user, reason),
    )


@bot.tree.command(description="Ban a member from the server.")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided",
) -> None:
    if interaction.guild is None:
        return
    await member.ban(reason=reason, delete_message_seconds=0)
    await interaction.response.send_message(f"Banned **{member}**.", ephemeral=True)
    await send_log(
        interaction.guild,
        moderation_embed("Ban", member, interaction.user, reason),
    )



SERVER_TEMPLATES = {
    "gaming": {
        "roles": ["Owner", "Administrator", "Moderator", "Member", "Bot"],
        "categories": {
            "START HERE": [
                ("welcome", "text"),
                ("rules", "text"),
                ("announcements", "text"),
                ("roles", "text"),
            ],
            "COMMUNITY": [
                ("general", "text"),
                ("media", "text"),
                ("memes", "text"),
                ("suggestions", "text"),
                ("General Voice", "voice"),
                ("Gaming Voice", "voice"),
            ],
            "GAMING": [
                ("looking-for-group", "text"),
                ("game-chat", "text"),
                ("clips-and-highlights", "text"),
                ("Squad 1", "voice"),
                ("Squad 2", "voice"),
            ],
            "SUPPORT": [
                ("open-a-ticket", "text"),
                ("server-help", "text"),
            ],
            "STAFF": [
                ("staff-chat", "text"),
                ("mod-logs", "text"),
            ],
        },
    },
    "community": {
        "roles": ["Owner", "Administrator", "Moderator", "Verified", "Member", "Bot"],
        "categories": {
            "START HERE": [
                ("welcome", "text"),
                ("rules", "text"),
                ("announcements", "text"),
                ("introductions", "text"),
            ],
            "COMMUNITY": [
                ("general", "text"),
                ("off-topic", "text"),
                ("photos-and-media", "text"),
                ("polls", "text"),
                ("suggestions", "text"),
                ("Community Voice", "voice"),
            ],
            "SUPPORT": [
                ("open-a-ticket", "text"),
                ("questions", "text"),
            ],
            "STAFF": [
                ("staff-chat", "text"),
                ("mod-logs", "text"),
            ],
        },
    },
    "store": {
        "roles": ["Owner", "Administrator", "Manager", "Support", "Customer", "Member", "Bot"],
        "categories": {
            "About Us": [
                ("All Members: 0", "voice"),
                ("Vouches: 0", "voice"),
                ("ducks-services.com", "voice"),
            ],
            "┌──── Information ────┐": [
                ("📜│rules", "text"),
                ("📢│announcements", "text"),
                ("🆕│updates", "text"),
                ("📦│restocks", "text"),
            ],
            "┌──── Support ────┐": [
                ("📖│support-ticket", "text"),
                ("❓│faq", "text"),
                ("🎫│open-a-ticket", "text"),
            ],
            "┌──── Chat ────┐": [
                ("🌎│general", "text"),
                ("🛟│general-support", "text"),
                ("🤖│bot-commands", "text"),
                ("🎥│clips", "text"),
                ("💻│dma-chat", "text"),
                ("⭐│reviews", "text"),
                ("⚙️│configs", "text"),
                ("🔨│ban-reports", "text"),
                ("💡│recommendations", "text"),
            ],
            "┌──── Staff ────┐": [
                ("🛡️│staff-chat", "text"),
                ("📋│mod-logs", "text"),
            ],
        },
    },
    "business": {
        "roles": ["Owner", "Administrator", "Manager", "Staff", "Client", "Bot"],
        "categories": {
            "INFORMATION": [
                ("welcome", "text"),
                ("rules", "text"),
                ("announcements", "text"),
                ("services", "text"),
            ],
            "CLIENT AREA": [
                ("general", "text"),
                ("questions", "text"),
                ("feedback", "text"),
                ("Client Meeting", "voice"),
            ],
            "SUPPORT": [
                ("open-a-ticket", "text"),
                ("support-information", "text"),
            ],
            "STAFF": [
                ("staff-chat", "text"),
                ("staff-tasks", "text"),
                ("mod-logs", "text"),
                ("Staff Meeting", "voice"),
            ],
        },
    },
}


def server_summary(guild: discord.Guild) -> str:
    categories = []
    for category in guild.categories:
        channels = ", ".join(channel.name for channel in category.channels) or "empty"
        categories.append(f"{category.name}: {channels}")
    uncategorized = [
        channel.name
        for channel in guild.channels
        if not isinstance(channel, discord.CategoryChannel)
        and getattr(channel, "category", None) is None
    ]
    role_names = [role.name for role in guild.roles if role.name != "@everyone"]
    return (
        f"Server: {guild.name}\n"
        f"Members: {guild.member_count}\n"
        f"Roles: {', '.join(role_names) or 'none'}\n"
        f"Categories:\n- " + "\n- ".join(categories or ["none"]) + "\n"
        f"Uncategorized channels: {', '.join(uncategorized) or 'none'}"
    )


async def get_or_create_role(guild: discord.Guild, name: str) -> tuple[discord.Role, bool]:
    existing = discord.utils.get(guild.roles, name=name)
    if existing:
        return existing, False

    permissions = discord.Permissions.none()
    if name == "Administrator":
        permissions = discord.Permissions(administrator=True)
    elif name in {"Moderator", "Manager"}:
        permissions = discord.Permissions(
            manage_messages=True,
            moderate_members=True,
            kick_members=True,
            view_audit_log=True,
        )

    role = await guild.create_role(
        name=name,
        permissions=permissions,
        reason="Created by the smart server builder",
    )
    return role, True


@bot.tree.command(description="Build an organized server layout from a template.")
@app_commands.describe(
    template="Choose gaming, community, or business",
    keep_existing="Keep all existing channels and add only missing items",
)
@app_commands.choices(
    template=[
        app_commands.Choice(name="Gaming server", value="gaming"),
        app_commands.Choice(name="Community server", value="community"),
        app_commands.Choice(name="Business server", value="business"),
        app_commands.Choice(name="Store / services server", value="store"),
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
    created_channels = 0

    try:
        for role_name in reversed(layout["roles"]):
            _, created = await get_or_create_role(guild, role_name)
            created_roles += int(created)

        for category_name, channels in layout["categories"].items():
            category = discord.utils.get(guild.categories, name=category_name)
            if category is None:
                overwrites = None
                if category_name == "STAFF":
                    staff_role = (
                        discord.utils.get(guild.roles, name="Moderator")
                        or discord.utils.get(guild.roles, name="Staff")
                        or discord.utils.get(guild.roles, name="Manager")
                    )
                    if staff_role and guild.me:
                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(view_channel=False),
                            staff_role: discord.PermissionOverwrite(
                                view_channel=True,
                                send_messages=True,
                                read_message_history=True,
                            ),
                            guild.me: discord.PermissionOverwrite(
                                view_channel=True,
                                send_messages=True,
                                manage_channels=True,
                            ),
                        }

                category = await guild.create_category(
                    category_name,
                    overwrites=overwrites,
                    reason="Created by the smart server builder",
                )
                created_categories += 1

            for channel_name, channel_type in channels:
                existing = discord.utils.get(category.channels, name=channel_name)
                if existing:
                    continue

                channel_overwrites = None

                if template.value == "store" and category_name == "About Us":
                    channel_overwrites = {
                        guild.default_role: discord.PermissionOverwrite(
                            view_channel=True,
                            connect=False,
                        )
                    }

                if template.value == "store" and (
                    "Staff" in category_name or channel_name == "⚙️│configs"
                ):
                    staff_role = (
                        discord.utils.get(guild.roles, name="Administrator")
                        or discord.utils.get(guild.roles, name="Manager")
                        or discord.utils.get(guild.roles, name="Support")
                    )
                    if staff_role and guild.me:
                        channel_overwrites = {
                            guild.default_role: discord.PermissionOverwrite(view_channel=False),
                            staff_role: discord.PermissionOverwrite(
                                view_channel=True,
                                send_messages=True,
                                read_message_history=True,
                            ),
                            guild.me: discord.PermissionOverwrite(
                                view_channel=True,
                                send_messages=True,
                                manage_channels=True,
                            ),
                        }

                if channel_type == "voice":
                    await guild.create_voice_channel(
                        channel_name,
                        category=category,
                        overwrites=channel_overwrites,
                        reason="Created by the smart server builder",
                    )
                else:
                    await guild.create_text_channel(
                        channel_name,
                        category=category,
                        overwrites=channel_overwrites,
                        reason="Created by the smart server builder",
                    )
                created_channels += 1

        # Automatically connect existing bot systems to common channels.
        welcome = discord.utils.get(guild.text_channels, name="welcome")
        logs = discord.utils.get(guild.text_channels, name="mod-logs")
        support_category = discord.utils.get(guild.categories, name="SUPPORT")
        support_role = (
            discord.utils.get(guild.roles, name="Moderator")
            or discord.utils.get(guild.roles, name="Staff")
            or discord.utils.get(guild.roles, name="Manager")
        )
        if welcome:
            upsert_setting(guild.id, "welcome_channel_id", welcome.id)
        if logs:
            upsert_setting(guild.id, "log_channel_id", logs.id)
        if support_category:
            upsert_setting(guild.id, "ticket_category_id", support_category.id)
        if support_role:
            upsert_setting(guild.id, "support_role_id", support_role.id)

        rules_channel = discord.utils.get(guild.text_channels, name="rules")
        if rules_channel and not any(
            message.author == guild.me
            async for message in rules_channel.history(limit=10)
        ):
            rules_embed = discord.Embed(
                title=f"{guild.name} Rules",
                description=(
                    "1. Treat everyone with respect.\n"
                    "2. No harassment, hate speech, threats, or excessive toxicity.\n"
                    "3. No spam, scams, malicious links, or unwanted advertising.\n"
                    "4. Keep content in the correct channels.\n"
                    "5. Do not share private information.\n"
                    "6. Follow Discord's Terms of Service and staff instructions."
                ),
                color=discord.Color.blurple(),
            )
            await rules_channel.send(embed=rules_embed)

        if template.value == "store":
            await update_store_stats(guild)

        await interaction.followup.send(
            f"✅ **{template.name} created.**\n"
            f"New roles: **{created_roles}**\n"
            f"New categories: **{created_categories}**\n"
            f"New channels: **{created_channels}**\n\n"
            "Existing matching channels were left unchanged.",
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "I could not finish because my role needs **Manage Roles** and **Manage Channels**. "
            "Move the bot role above the roles it manages.",
            ephemeral=True,
        )


@bot.tree.command(description="Inspect your server and recommend organization improvements.")
@app_commands.checks.has_permissions(manage_guild=True)
async def server_audit(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        return

    findings = []
    text_names = {channel.name.lower() for channel in guild.text_channels}

    essentials = {
        "rules": "Add a read-only rules channel.",
        "welcome": "Add a welcome channel for new members.",
        "announcements": "Add an announcements channel for important updates.",
        "mod-logs": "Add a private moderation log channel.",
        "open-a-ticket": "Add a ticket panel channel for support.",
    }
    for channel_name, recommendation in essentials.items():
        if channel_name not in text_names:
            findings.append(f"• **Missing #{channel_name}:** {recommendation}")

    uncategorized = [
        channel for channel in guild.channels
        if not isinstance(channel, discord.CategoryChannel)
        and getattr(channel, "category", None) is None
    ]
    if len(uncategorized) > 3:
        findings.append(
            f"• **{len(uncategorized)} uncategorized channels:** Move them into clear categories."
        )

    empty_categories = [category.name for category in guild.categories if not category.channels]
    if empty_categories:
        findings.append(
            f"• **Empty categories:** {', '.join(empty_categories[:8])}. Remove or use them."
        )

    duplicate_names = {}
    for channel in guild.channels:
        duplicate_names[channel.name] = duplicate_names.get(channel.name, 0) + 1
    duplicates = [name for name, count in duplicate_names.items() if count > 1]
    if duplicates:
        findings.append(
            f"• **Duplicate channel names:** {', '.join(duplicates[:8])}."
        )

    admin_roles = [
        role.name for role in guild.roles
        if role.permissions.administrator and role.name != "@everyone"
    ]
    if len(admin_roles) > 3:
        findings.append(
            f"• **Many administrator roles ({len(admin_roles)}):** Review them and use least privilege."
        )

    if not findings:
        findings.append("✅ The basic server structure looks organized.")

    embed = discord.Embed(
        title=f"Organization Audit — {guild.name}",
        description="\n".join(findings[:15]),
        color=discord.Color.green() if findings[0].startswith("✅") else discord.Color.orange(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(
        name="Current size",
        value=(
            f"{len(guild.categories)} categories • "
            f"{len(guild.text_channels)} text channels • "
            f"{len(guild.voice_channels)} voice channels • "
            f"{len(guild.roles) - 1} roles"
        ),
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(description="Create or replace a clean rules message.")
@app_commands.checks.has_permissions(manage_guild=True)
async def create_rules(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
) -> None:
    guild = interaction.guild
    if guild is None:
        return

    embed = discord.Embed(
        title=f"{guild.name} Rules",
        description=(
            "**1. Respect everyone**\n"
            "No harassment, discrimination, threats, or targeted abuse.\n\n"
            "**2. Keep the server safe**\n"
            "No scams, malware, doxxing, or malicious links.\n\n"
            "**3. Avoid spam**\n"
            "Do not flood chats, mass mention users, or advertise without permission.\n\n"
            "**4. Use the correct channels**\n"
            "Keep discussions and media in their intended areas.\n\n"
            "**5. Follow staff directions**\n"
            "Moderators may act to protect the server even when a situation is not listed exactly.\n\n"
            "**6. Follow Discord's Terms of Service**"
        ),
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
    )
    await channel.send(embed=embed)
    await interaction.response.send_message(
        f"Rules posted in {channel.mention}.", ephemeral=True
    )


@bot.tree.command(description="Ask the optional AI organizer how to improve your server.")
@app_commands.describe(question="What do you want help organizing or creating?")
@app_commands.checks.has_permissions(manage_guild=True)
async def ask_organizer(interaction: discord.Interaction, question: str) -> None:
    guild = interaction.guild
    if guild is None:
        return
    if ai_client is None:
        await interaction.response.send_message(
            "AI mode is not configured. Add `OPENAI_API_KEY` to your `.env` file, "
            "install the updated requirements, and restart the bot.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        response = await ai_client.responses.create(
            model=AI_MODEL,
            instructions=(
                "You are a Discord server organization assistant. Give practical, safe, "
                "concise recommendations. Do not claim you changed the server. Base your "
                "answer on the supplied server structure. Limit the response to 1,500 characters."
            ),
            input=(
                f"{server_summary(guild)}\n\n"
                f"Administrator's question: {question}"
            ),
            max_output_tokens=500,
        )
        answer = response.output_text.strip()
        await interaction.followup.send(answer[:1900], ephemeral=True)
    except Exception as exc:
        print(f"AI organizer error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(
            "The AI request failed. Check the API key, model name, package installation, and bot console.",
            ephemeral=True,
        )


async def update_store_stats(guild: discord.Guild) -> None:
    about = discord.utils.get(guild.categories, name="About Us")
    if about is None:
        return

    member_channel = next(
        (c for c in about.voice_channels if c.name.startswith("All Members:")),
        None,
    )
    vouch_channel = next(
        (c for c in about.voice_channels if c.name.startswith("Vouches:")),
        None,
    )

    if member_channel:
        desired = f"All Members: {guild.member_count or 0}"
        if member_channel.name != desired:
            try:
                await member_channel.edit(name=desired, reason="Updating member counter")
            except discord.Forbidden:
                pass

    if vouch_channel:
        reviews = discord.utils.find(
            lambda c: isinstance(c, discord.TextChannel)
            and c.name in {"⭐│reviews", "reviews"},
            guild.channels,
        )
        count = 0
        if isinstance(reviews, discord.TextChannel):
            try:
                async for _ in reviews.history(limit=None):
                    count += 1
            except discord.Forbidden:
                pass

        desired = f"Vouches: {count}"
        if vouch_channel.name != desired:
            try:
                await vouch_channel.edit(name=desired, reason="Updating vouch counter")
            except discord.Forbidden:
                pass


@bot.tree.command(description="Refresh the member and vouch counter channels.")
@app_commands.checks.has_permissions(manage_guild=True)
async def update_stats(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        return
    await interaction.response.defer(ephemeral=True)
    await update_store_stats(interaction.guild)
    await interaction.followup.send("Server statistics updated.", ephemeral=True)


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        message = "You do not have permission to use that command."
    elif isinstance(error, app_commands.BotMissingPermissions):
        message = "I am missing a required server permission."
    else:
        original = getattr(error, "original", error)
        print(f"Command error: {type(original).__name__}: {original}")
        message = "The command failed. Check the bot console for details."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


if __name__ == "__main__":
    bot.run(TOKEN, log_handler=None)
