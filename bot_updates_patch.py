from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")


def rep(old: str, new: str) -> None:
    global s
    if old in s:
        s = s.replace(old, new)

# Exact Railway variable for the Discord bot update log channel.
# UPDATE_LOG_CHANNEL_ID is the preferred name. BOT_UPDATE_CHANNEL_ID still works as an alias.
if "UPDATE_LOG_CHANNEL_ID" not in s:
    rep(
        'TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")\n',
        'TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")\n'
        'UPDATE_LOG_CHANNEL_ID = os.getenv("UPDATE_LOG_CHANNEL_ID") or os.getenv("BOT_UPDATE_CHANNEL_ID")\n',
    )
elif "BOT_UPDATE_CHANNEL_ID" in s and "UPDATE_LOG_CHANNEL_ID =" not in s:
    rep(
        'BOT_UPDATE_CHANNEL_ID = os.getenv("BOT_UPDATE_CHANNEL_ID")\n',
        'UPDATE_LOG_CHANNEL_ID = os.getenv("UPDATE_LOG_CHANNEL_ID") or os.getenv("BOT_UPDATE_CHANNEL_ID")\n',
    )

update_code = r'''


def split_update_items(text: str) -> list[str]:
    text = str(text or "").strip()
    if not text:
        return []
    raw_items = []
    for line in text.replace("\r", "\n").split("\n"):
        raw_items.extend(line.split(";"))
    items = []
    for item in raw_items:
        cleaned = item.strip(" -•\t")
        if cleaned:
            items.append(cleaned[:220])
    return items


def format_update_items(text: str, empty_text: str = "No items listed.") -> str:
    items = split_update_items(text)
    if not items:
        return empty_text
    return "\n".join(f"• {item}" for item in items)[:1024]


async def find_default_bot_update_channel(guild: discord.Guild | None):
    if guild is None:
        return None

    if not UPDATE_LOG_CHANNEL_ID:
        return None

    try:
        channel_id = int(UPDATE_LOG_CHANNEL_ID)
    except ValueError:
        return None

    try:
        channel = guild.get_channel(channel_id) or bot.get_channel(channel_id)
        if channel is None:
            channel = await bot.fetch_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel
    except Exception:
        return None

    return None


def can_post_bot_update(interaction: discord.Interaction) -> bool:
    member = interaction.user
    if isinstance(member, discord.Member) and member.guild_permissions.administrator:
        return True
    return any(getattr(role, "name", "") in STAFF_ROLE_NAMES for role in getattr(member, "roles", []))


def build_bot_update_embed(version: str, added: str, changed: str, author_name: str) -> discord.Embed:
    version = str(version or "MADBOT Update").strip()[:80]
    embed = discord.Embed(
        title=f"🤖 MADBOT Update — {version}",
        color=discord.Color.blurple(),
        timestamp=datetime.now(ZoneInfo(TIMEZONE)),
    )
    embed.add_field(name="✅ Added", value=format_update_items(added), inline=False)
    if str(changed or "").strip():
        embed.add_field(name="🔧 Changed / Fixed", value=format_update_items(changed), inline=False)
    embed.set_footer(text=f"Posted by {author_name}")
    return embed


@bot.tree.command(name="bot-update", description="Post a clean MADBOT update log to the configured update-log channel.")
@app_commands.describe(
    version="Update version or title, example: v1.4 Rank Sales Update",
    added="New features. Separate items with semicolons or new lines.",
    changed="Fixes/changes. Separate items with semicolons or new lines.",
    channel="Optional channel override for this post.",
    ping_role="Optional role to ping with the update.",
)
async def bot_update(
    interaction: discord.Interaction,
    version: str,
    added: str,
    changed: str = "",
    channel: discord.TextChannel | None = None,
    ping_role: discord.Role | None = None
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    if not can_post_bot_update(interaction):
        await interaction.response.send_message("You do not have permission to post bot updates.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    target_channel = channel or await find_default_bot_update_channel(interaction.guild)
    if target_channel is None:
        await interaction.followup.send(
            "I could not find the update-log channel. Add UPDATE_LOG_CHANNEL_ID in Railway Variables, or use the channel option in /bot-update.",
            ephemeral=True,
        )
        return

    embed = build_bot_update_embed(version, added, changed, getattr(interaction.user, "display_name", str(interaction.user)))
    content = ping_role.mention if ping_role else None

    try:
        message = await target_channel.send(
            content=content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=True, users=False, everyone=False),
        )
    except discord.Forbidden:
        await interaction.followup.send("I cannot send messages in that update channel. Give me Send Messages and Embed Links.", ephemeral=True)
        return

    await interaction.followup.send(f"Bot update posted in {target_channel.mention}: {message.jump_url}", ephemeral=True)


@bot.tree.command(name="bot-update-channel", description="Show the channel ID to use for bot update logs.")
@app_commands.describe(channel="The Discord channel you want MADBOT update logs posted in")
async def bot_update_channel(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    if not can_post_bot_update(interaction):
        await interaction.response.send_message("You do not have permission to configure bot updates.", ephemeral=True)
        return

    await interaction.response.send_message(
        f"Use this Railway variable for update-log posting:\n```env\nUPDATE_LOG_CHANNEL_ID={channel.id}\n```\n"
        f"Then use `/bot-update` to post an update to {channel.mention}.",
        ephemeral=True,
    )
'''

if "name=\"bot-update\"" not in s:
    s = s.replace("\n\nbot.run(TOKEN)", update_code + "\n\nbot.run(TOKEN)")
else:
    s = s.replace('BOT_UPDATE_CHANNEL_ID', 'UPDATE_LOG_CHANNEL_ID')
    s = s.replace('Either use the channel option or add UPDATE_LOG_CHANNEL_ID in Railway Variables.', 'Add UPDATE_LOG_CHANNEL_ID in Railway Variables, or use the channel option in /bot-update.')
    s = s.replace('Either use the channel option or add UPDATE_LOG_CHANNEL_ID in Railway Variables.', 'Add UPDATE_LOG_CHANNEL_ID in Railway Variables, or use the channel option in /bot-update.')

p.write_text(s, encoding="utf-8")
print("Bot updates patch applied.")
